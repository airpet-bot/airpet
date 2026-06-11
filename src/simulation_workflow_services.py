from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GeometryInspectionService:
    project_manager: Any

    def inspect_focus(
        self,
        component_type: str,
        reference: str,
        *,
        nearby_limit: int = 6,
        preflight_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.project_manager._inspect_geometry_focus_impl(
            component_type,
            reference,
            nearby_limit=nearby_limit,
            preflight_report=preflight_report,
        )


@dataclass(frozen=True)
class GeometryPreflightService:
    project_manager: Any

    def run(self) -> Dict[str, Any]:
        return self.project_manager._run_preflight_checks_impl()


@dataclass(frozen=True)
class Geant4MacroGenerationService:
    project_manager: Any

    def generate(
        self,
        job_id: str,
        sim_params: Dict[str, Any],
        build_dir: str,
        run_dir: str,
        version_dir: str,
    ) -> str:
        return self.project_manager._generate_macro_file_impl(
            job_id,
            sim_params,
            build_dir,
            run_dir,
            version_dir,
        )
