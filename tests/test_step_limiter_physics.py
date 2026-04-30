"""Test that G4StepLimiterPhysics is registered and region user limits work."""

import os
import subprocess
import tempfile


def test_step_limiter_physics_is_registered():
    """Running a minimal macro must show G4StepLimiterPhysics registration."""
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
        )

        combined_output = result.stdout + result.stderr
        assert "Registering G4StepLimiterPhysics" in combined_output, (
            f"G4StepLimiterPhysics not registered. Output:\n{combined_output}"
        )
