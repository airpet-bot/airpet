from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass(frozen=True)
class AIToolDispatchHooks:
    normalize_args: Callable[
        [str, Dict[str, Any]],
        Tuple[Dict[str, Any], Optional[str]],
    ]
    receipt_spec: Callable[[str, Dict[str, Any]], Any]
    capture_receipt_state: Callable[[Any, Any], Any]
    classify_risk: Callable[[Any, str, Dict[str, Any]], Any]
    execute: Callable[[Any, str, Dict[str, Any]], Dict[str, Any]]
    build_receipt: Callable[[Any, str, Any, Any], Dict[str, Any]]
    build_risk_verification: Callable[[Any, Any], Dict[str, Any]]


class AIToolDispatcher:
    """Provider-neutral lifecycle around AIRPET tool execution."""

    def __init__(self, hooks: AIToolDispatchHooks):
        self.hooks = hooks

    def dispatch(
        self,
        project_manager: Any,
        tool_name: str,
        args: Dict[str, Any],
        *,
        apply_risk_verification: bool = True,
    ) -> Dict[str, Any]:
        normalized_args, normalize_error = self.hooks.normalize_args(
            tool_name,
            args,
        )
        effective_args = (
            normalized_args
            if normalize_error is None and isinstance(normalized_args, dict)
            else args
        )
        receipt_spec = self.hooks.receipt_spec(tool_name, effective_args or {})
        before = self.hooks.capture_receipt_state(
            project_manager,
            receipt_spec,
        )
        risk_spec = (
            self.hooks.classify_risk(
                project_manager,
                tool_name,
                effective_args or {},
            )
            if apply_risk_verification and normalize_error is None
            else None
        )

        result = self.hooks.execute(project_manager, tool_name, args)
        if (
            isinstance(result, dict)
            and result.get("success") is True
            and receipt_spec is not None
        ):
            result["edit_receipt"] = self.hooks.build_receipt(
                project_manager,
                tool_name,
                receipt_spec,
                before,
            )
        if (
            isinstance(result, dict)
            and result.get("success") is True
            and risk_spec is not None
        ):
            result["risk_aware_verification"] = (
                self.hooks.build_risk_verification(
                    project_manager,
                    risk_spec,
                )
            )
        return result
