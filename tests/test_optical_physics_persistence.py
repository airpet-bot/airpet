import json

from app import get_geant4_env
from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import EnvironmentState, GeometryState
from src.project_manager import ProjectManager


def test_environment_state_optical_physics_round_trip():
    state = GeometryState()
    assert state.environment.optical_physics is False

    state.environment.optical_physics = True
    payload = state.to_dict()
    assert payload["environment"]["optical_physics"] is True

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.optical_physics is True


def test_environment_state_optical_physics_false_explicitly():
    state = GeometryState()
    state.environment.optical_physics = False
    payload = state.to_dict()
    assert payload["environment"]["optical_physics"] is False

    round_tripped = GeometryState.from_dict(payload)
    assert round_tripped.environment.optical_physics is False


def test_environment_state_validation_rejects_non_bool():
    ok, err = EnvironmentState.validate({"optical_physics": "yes"})
    assert ok is False
    assert "optical_physics must be a boolean" in err


def test_project_json_save_load_persists_optical_physics():
    pm = ProjectManager(ExpressionEvaluator())
    pm.current_geometry_state.environment.optical_physics = True

    json_string = pm.save_project_to_json_string()
    data = json.loads(json_string)
    assert data["environment"]["optical_physics"] is True

    pm2 = ProjectManager(ExpressionEvaluator())
    pm2.load_project_from_json_string(json_string)
    assert pm2.current_geometry_state.environment.optical_physics is True


def test_get_geant4_env_sets_g4opticalphysics_true():
    env = get_geant4_env(sim_params={"optical_physics": True})
    assert env.get("G4OPTICALPHYSICS") == "true"


def test_get_geant4_env_sets_g4opticalphysics_false():
    env = get_geant4_env(sim_params={"optical_physics": False})
    assert env.get("G4OPTICALPHYSICS") == "false"


def test_get_geant4_env_omits_g4opticalphysics_when_not_provided():
    env = get_geant4_env(sim_params={"physics_list": "FTFP_BERT"})
    assert "G4OPTICALPHYSICS" not in env
