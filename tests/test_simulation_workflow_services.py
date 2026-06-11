from src.simulation_workflow_services import (
    Geant4MacroGenerationService,
    GeometryInspectionService,
    GeometryPreflightService,
)


class _FakeProjectManager:
    def _inspect_geometry_focus_impl(
        self,
        component_type,
        reference,
        *,
        nearby_limit,
        preflight_report,
    ):
        return {
            "component_type": component_type,
            "reference": reference,
            "nearby_limit": nearby_limit,
            "preflight_report": preflight_report,
        }

    def _run_preflight_checks_impl(self):
        return {"summary": {"errors": 0}}

    def _generate_macro_file_impl(
        self,
        job_id,
        sim_params,
        build_dir,
        run_dir,
        version_dir,
    ):
        return (
            job_id,
            sim_params,
            build_dir,
            run_dir,
            version_dir,
        )


def test_geometry_inspection_service_delegates_explicit_focus_contract():
    service = GeometryInspectionService(_FakeProjectManager())
    preflight = {"summary": {"warnings": 1}}

    result = service.inspect_focus(
        "physical_volume",
        "pv-1",
        nearby_limit=4,
        preflight_report=preflight,
    )

    assert result == {
        "component_type": "physical_volume",
        "reference": "pv-1",
        "nearby_limit": 4,
        "preflight_report": preflight,
    }


def test_geometry_preflight_service_delegates_report_generation():
    service = GeometryPreflightService(_FakeProjectManager())

    assert service.run() == {"summary": {"errors": 0}}


def test_geant4_macro_service_delegates_generation_inputs():
    service = Geant4MacroGenerationService(_FakeProjectManager())

    result = service.generate(
        "job-1",
        {"events": 10},
        "/build",
        "/run",
        "/version",
    )

    assert result == (
        "job-1",
        {"events": 10},
        "/build",
        "/run",
        "/version",
    )
