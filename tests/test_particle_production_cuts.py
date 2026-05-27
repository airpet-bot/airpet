import json
from pathlib import Path
import sys
import types

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import GeometryState, ScoringState


class _DummyOccObject:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return self


def _install_occ_stubs():
    if "OCC" in sys.modules:
        return

    occ_module = types.ModuleType("OCC")
    occ_module.__path__ = []
    core_module = types.ModuleType("OCC.Core")
    core_module.__path__ = []

    sys.modules["OCC"] = occ_module
    sys.modules["OCC.Core"] = core_module

    module_specs = {
        "OCC.Core.STEPControl": {"STEPControl_Reader": _DummyOccObject},
        "OCC.Core.TopAbs": {
            "TopAbs_SOLID": 0,
            "TopAbs_FACE": 1,
            "TopAbs_REVERSED": 2,
        },
        "OCC.Core.TopExp": {"TopExp_Explorer": _DummyOccObject},
        "OCC.Core.BRep": {
            "BRep_Tool": type(
                "_BRepTool",
                (),
                {"Triangulation": staticmethod(lambda *args, **kwargs: None)},
            )
        },
        "OCC.Core.BRepMesh": {"BRepMesh_IncrementalMesh": _DummyOccObject},
        "OCC.Core.TopLoc": {"TopLoc_Location": _DummyOccObject},
        "OCC.Core.gp": {"gp_Trsf": _DummyOccObject},
        "OCC.Core.TDF": {"TDF_Label": _DummyOccObject, "TDF_LabelSequence": _DummyOccObject},
        "OCC.Core.XCAFDoc": {
            "XCAFDoc_DocumentTool": type(
                "_XCAFDocDocumentTool",
                (),
                {"ShapeTool": staticmethod(lambda *args, **kwargs: _DummyOccObject())},
            )
        },
        "OCC.Core.STEPCAFControl": {"STEPCAFControl_Reader": _DummyOccObject},
        "OCC.Core.TDocStd": {"TDocStd_Document": _DummyOccObject},
    }

    for module_name, attrs in module_specs.items():
        module = types.ModuleType(module_name)
        for attr_name, value in attrs.items():
            setattr(module, attr_name, value)
        sys.modules[module_name] = module


_install_occ_stubs()

from src.project_manager import ProjectManager


def test_run_manifest_defaults_round_trip():
    state = GeometryState()
    defaults = state.scoring.to_dict()["run_manifest_defaults"]
    assert defaults["particle_production_cuts"] == []

    state.scoring.run_manifest_defaults["particle_production_cuts"] = [
        {"particle_name": "gamma", "cut": 1.0, "unit": "mm"},
        {"particle_name": "e-", "cut": 0.5, "unit": "um"},
    ]
    payload = state.to_dict()
    assert payload["scoring"]["run_manifest_defaults"]["particle_production_cuts"] == [
        {"particle_name": "gamma", "cut": 1.0, "unit": "mm"},
        {"particle_name": "e-", "cut": 0.5, "unit": "um"},
    ]

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.scoring.run_manifest_defaults["particle_production_cuts"] == [
        {"particle_name": "gamma", "cut": 1.0, "unit": "mm"},
        {"particle_name": "e-", "cut": 0.5, "unit": "um"},
    ]


def test_run_manifest_validation_rejects_invalid():
    ok, err = ScoringState.validate({
        "run_manifest_defaults": {"particle_production_cuts": "not-a-list"}
    })
    assert ok is False
    assert "particle_production_cuts" in err

    ok, err = ScoringState.validate({
        "run_manifest_defaults": {"particle_production_cuts": [{"particle_name": ""}]}
    })
    assert ok is False
    assert "particle_name" in err

    ok, err = ScoringState.validate({
        "run_manifest_defaults": {"particle_production_cuts": [{"particle_name": "gamma", "cut": -1}]}
    })
    assert ok is False
    assert "cut" in err


def test_project_json_save_load_persists_values():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.scoring.run_manifest_defaults["particle_production_cuts"] = [
        {"particle_name": "proton", "cut": 2.0, "unit": "mm"},
    ]

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["scoring"]["run_manifest_defaults"]["particle_production_cuts"] == [
        {"particle_name": "proton", "cut": 2.0, "unit": "mm"},
    ]

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.scoring.run_manifest_defaults["particle_production_cuts"] == [
        {"particle_name": "proton", "cut": 2.0, "unit": "mm"},
    ]


def test_generate_macro_emits_particle_production_cuts(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.scoring.run_manifest_defaults["particle_production_cuts"] = [
        {"particle_name": "gamma", "cut": 1.0, "unit": "mm"},
        {"particle_name": "e-", "cut": 0.5, "unit": "um"},
    ]

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "cuts-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/beamOn 1" in macro_text
    assert "/run/setCutForAGivenParticle gamma 1 mm" in macro_text
    assert "/run/setCutForAGivenParticle e- 0.5 um" in macro_text
    # Ensure commands appear before /run/beamOn
    cut_pos = macro_text.index("/run/setCutForAGivenParticle gamma 1 mm")
    beam_on_pos = macro_text.index("/run/beamOn")
    assert cut_pos < beam_on_pos


def test_generate_macro_omits_particle_production_cuts_at_default(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.scoring.run_manifest_defaults["particle_production_cuts"] = []

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "default-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/setCutForAGivenParticle" not in macro_text
    assert "/run/beamOn 1" in macro_text
