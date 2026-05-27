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
    assert defaults["event_modulo_n"] == 0
    assert defaults["event_modulo_seed_once"] == 0

    state.scoring.run_manifest_defaults["event_modulo_n"] = 10
    state.scoring.run_manifest_defaults["event_modulo_seed_once"] = 1
    payload = state.to_dict()
    assert payload["scoring"]["run_manifest_defaults"]["event_modulo_n"] == 10
    assert payload["scoring"]["run_manifest_defaults"]["event_modulo_seed_once"] == 1

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.scoring.run_manifest_defaults["event_modulo_n"] == 10
    assert round_tripped.scoring.run_manifest_defaults["event_modulo_seed_once"] == 1


def test_run_manifest_validation_rejects_negative():
    ok, err = ScoringState.validate({
        "run_manifest_defaults": {"event_modulo_n": -1}
    })
    assert ok is False
    assert "event_modulo_n" in err

    ok, err = ScoringState.validate({
        "run_manifest_defaults": {"event_modulo_seed_once": -1}
    })
    assert ok is False
    assert "event_modulo_seed_once" in err


def test_project_json_save_load_persists_values():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.scoring.run_manifest_defaults["event_modulo_n"] = 20
    pm.current_geometry_state.scoring.run_manifest_defaults["event_modulo_seed_once"] = 2

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["scoring"]["run_manifest_defaults"]["event_modulo_n"] == 20
    assert data["scoring"]["run_manifest_defaults"]["event_modulo_seed_once"] == 2

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.scoring.run_manifest_defaults["event_modulo_n"] == 20
    assert pm2.current_geometry_state.scoring.run_manifest_defaults["event_modulo_seed_once"] == 2


def test_generate_macro_emits_event_modulo_when_n_positive(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.scoring.run_manifest_defaults["event_modulo_n"] = 10

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "modulo-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/beamOn 1" in macro_text
    assert "/run/eventModulo 10 0" in macro_text


def test_generate_macro_emits_event_modulo_when_seed_once_positive(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.scoring.run_manifest_defaults["event_modulo_seed_once"] = 1

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "seed-once-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/beamOn 1" in macro_text
    assert "/run/eventModulo 0 1" in macro_text


def test_generate_macro_emits_combined_event_modulo(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.scoring.run_manifest_defaults["event_modulo_n"] = 25
    state.scoring.run_manifest_defaults["event_modulo_seed_once"] = 2

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "combined-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/run/eventModulo 25 2" in macro_text
    # Ensure it appears before /run/beamOn
    modulo_pos = macro_text.index("/run/eventModulo 25 2")
    beam_on_pos = macro_text.index("/run/beamOn")
    assert modulo_pos < beam_on_pos


def test_generate_macro_omits_event_modulo_at_defaults(tmp_path):
    pm = ProjectManager(ExpressionEvaluator())
    state = GeometryState()
    state.scoring.run_manifest_defaults["event_modulo_n"] = 0
    state.scoring.run_manifest_defaults["event_modulo_seed_once"] = 0

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

    assert "/run/eventModulo" not in macro_text
    assert "/run/beamOn 1" in macro_text
