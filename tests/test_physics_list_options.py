import sys
import os

# Ensure the project root is on the path so `app` can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app import get_geant4_env


NEW_PHYSICS_LISTS = [
    "QBBC",
    "QGSP_BERT_HP",
    "QGSP_BIC",
    "FTFP_BERT_ATL",
    "QGSP_FTFP_BERT",
]


def test_get_geant4_env_accepts_each_new_physics_list():
    """Verify that every newly exposed physics list is forwarded to G4PHYSICSLIST."""
    for pl_name in NEW_PHYSICS_LISTS:
        env = get_geant4_env(sim_params={"physics_list": pl_name})
        assert env.get("G4PHYSICSLIST") == pl_name, (
            f"Expected G4PHYSICSLIST={pl_name} but got {env.get('G4PHYSICSLIST')}"
        )


def test_get_geant4_env_preserves_existing_lists():
    """Ensure previously supported lists still work."""
    for pl_name in ["FTFP_BERT", "QGSP_BERT", "FTFP_BERT_HP", "QGSP_BIC_HP", "Shielding"]:
        env = get_geant4_env(sim_params={"physics_list": pl_name})
        assert env.get("G4PHYSICSLIST") == pl_name


def test_get_geant4_env_omits_physics_list_when_not_provided():
    """When sim_params lacks physics_list, G4PHYSICSLIST should not be injected."""
    baseline = get_geant4_env(sim_params={})
    assert "G4PHYSICSLIST" not in baseline

    with_list = get_geant4_env(sim_params={"physics_list": "QBBC"})
    assert with_list.get("G4PHYSICSLIST") == "QBBC"
