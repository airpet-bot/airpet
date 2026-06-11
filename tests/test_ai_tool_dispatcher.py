from src.ai_tool_dispatcher import AIToolDispatcher, AIToolDispatchHooks


def _build_dispatcher(execute_result, calls):
    return AIToolDispatcher(
        AIToolDispatchHooks(
            normalize_args=lambda name, args: (
                {**args, "normalized": True},
                None,
            ),
            receipt_spec=lambda name, args: {"args": args},
            capture_receipt_state=lambda pm, spec: {"before": spec},
            classify_risk=lambda pm, name, args: {"risk": "spatial"},
            execute=lambda pm, name, args: (
                calls.append((pm, name, args)) or dict(execute_result)
            ),
            build_receipt=lambda pm, name, spec, before: {
                "tool": name,
                "before": before,
            },
            build_risk_verification=lambda pm, risk: {
                "risk": risk["risk"],
            },
        )
    )


def test_dispatcher_applies_receipt_and_risk_verification_to_success():
    calls = []
    dispatcher = _build_dispatcher({"success": True}, calls)

    result = dispatcher.dispatch("pm", "move", {"x": 1})

    assert calls == [("pm", "move", {"x": 1})]
    assert result["edit_receipt"]["tool"] == "move"
    assert result["risk_aware_verification"] == {"risk": "spatial"}


def test_dispatcher_does_not_decorate_failed_execution():
    dispatcher = _build_dispatcher(
        {"success": False, "error": "invalid"},
        [],
    )

    result = dispatcher.dispatch("pm", "move", {"x": 1})

    assert result == {"success": False, "error": "invalid"}


def test_dispatcher_can_disable_risk_verification_without_losing_receipts():
    dispatcher = _build_dispatcher({"success": True}, [])

    result = dispatcher.dispatch(
        "pm",
        "set_material",
        {"material": "G4_Si"},
        apply_risk_verification=False,
    )

    assert "edit_receipt" in result
    assert "risk_aware_verification" not in result
