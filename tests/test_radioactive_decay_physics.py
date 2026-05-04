"""Test that G4RadioactiveDecayPhysics is registered when the env var is set."""

import os
import subprocess
import tempfile


def test_radioactive_decay_physics_is_registered_when_env_var_is_set():
    """Running a minimal macro with G4RADIOACTIVEDECAYPHYSICS=true must show registration."""
    executable = os.path.join(os.getcwd(), "geant4", "build", "airpet-sim")
    assert os.path.exists(executable), f"Executable not found: {executable}"

    macro_content = """
/g4pet/detector/readFile geometry.gdml
/run/initialize
/exit
"""
    # Minimal GDML
    gdml_content = """<?xml version="1.0"?>
<gdml>
  <materials>
    <material name="Air" state="gas">
      <D value="0.001225" unit="g/cm3"/>
      <atom value="28.085"/>
    </material>
  </materials>
  <solids>
    <box name="world_solid" lunit="mm" x="100" y="100" z="100"/>
  </solids>
  <structure>
    <volume name="world_lv">
      <materialref ref="Air"/>
      <solidref ref="world_solid"/>
    </volume>
  </structure>
  <setup name="Default" version="1.0">
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    env = os.environ.copy()
    env["G4RADIOACTIVEDECAYPHYSICS"] = "true"

    with tempfile.TemporaryDirectory() as tmpdir:
        gdml_path = os.path.join(tmpdir, "geometry.gdml")
        macro_path = os.path.join(tmpdir, "test.mac")
        with open(gdml_path, "w") as f:
            f.write(gdml_content)
        with open(macro_path, "w") as f:
            f.write(macro_content)

        result = subprocess.run(
            [executable, macro_path],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        combined_output = result.stdout + result.stderr
        assert "Registering G4RadioactiveDecayPhysics" in combined_output, (
            f"G4RadioactiveDecayPhysics not registered. Output:\n{combined_output}"
        )


def test_radioactive_decay_physics_is_not_registered_when_env_var_is_unset():
    """Running a minimal macro without the env var must not show registration."""
    executable = os.path.join(os.getcwd(), "geant4", "build", "airpet-sim")
    assert os.path.exists(executable), f"Executable not found: {executable}"

    macro_content = """
/g4pet/detector/readFile geometry.gdml
/run/initialize
/exit
"""
    gdml_content = """<?xml version="1.0"?>
<gdml>
  <materials>
    <material name="Air" state="gas">
      <D value="0.001225" unit="g/cm3"/>
      <atom value="28.085"/>
    </material>
  </materials>
  <solids>
    <box name="world_solid" lunit="mm" x="100" y="100" z="100"/>
  </solids>
  <structure>
    <volume name="world_lv">
      <materialref ref="Air"/>
      <solidref ref="world_solid"/>
    </volume>
  </structure>
  <setup name="Default" version="1.0">
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    env = os.environ.copy()
    env.pop("G4RADIOACTIVEDECAYPHYSICS", None)

    with tempfile.TemporaryDirectory() as tmpdir:
        gdml_path = os.path.join(tmpdir, "geometry.gdml")
        macro_path = os.path.join(tmpdir, "test.mac")
        with open(gdml_path, "w") as f:
            f.write(gdml_content)
        with open(macro_path, "w") as f:
            f.write(macro_content)

        result = subprocess.run(
            [executable, macro_path],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        combined_output = result.stdout + result.stderr
        assert "Registering G4RadioactiveDecayPhysics" not in combined_output, (
            f"G4RadioactiveDecayPhysics should not be registered when env var is absent. Output:\n{combined_output}"
        )


def test_get_geant4_env_sets_g4radioactivedecayphysics_true():
    from app import get_geant4_env
    env = get_geant4_env(sim_params={"radioactive_decay_physics": True})
    assert env.get("G4RADIOACTIVEDECAYPHYSICS") == "true"


def test_get_geant4_env_sets_g4radioactivedecayphysics_false():
    from app import get_geant4_env
    env = get_geant4_env(sim_params={"radioactive_decay_physics": False})
    assert env.get("G4RADIOACTIVEDECAYPHYSICS") == "false"


def test_get_geant4_env_omits_g4radioactivedecayphysics_when_not_provided():
    from app import get_geant4_env
    env = get_geant4_env(sim_params={"physics_list": "FTFP_BERT"})
    assert "G4RADIOACTIVEDECAYPHYSICS" not in env
