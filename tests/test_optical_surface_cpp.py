"""Test that optical surfaces, skin surfaces, and border surfaces are created at runtime."""

import os
import subprocess
import tempfile


def test_optical_surfaces_are_created_at_runtime():
    """Running a macro with optical-surface commands must create the surfaces."""
    executable = os.path.join(os.getcwd(), "geant4", "build", "airpet-sim")
    assert os.path.exists(executable), f"Executable not found: {executable}"

    gdml_content = """<?xml version="1.0"?>
<gdml>
  <solids>
    <box name="world_solid" lunit="mm" x="100" y="100" z="100"/>
    <box name="box_solid" lunit="mm" x="10" y="10" z="10"/>
  </solids>
  <structure>
    <volume name="box_lv">
      <materialref ref="G4_Si"/>
      <solidref ref="box_solid"/>
    </volume>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <physvol name="box_pv">
        <volumeref ref="box_lv"/>
        <position name="box_pos" x="0" y="0" z="0" unit="mm"/>
      </physvol>
    </volume>
  </structure>
  <setup name="Default" version="1.0">
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    macro_content = """
/g4pet/detector/readFile geometry.gdml
/g4pet/detector/addOpticalSurface MirrorSurf|glisur|polished|dielectric_dielectric|0.95
/g4pet/detector/addSkinSurface Skin1|box_lv|MirrorSurf
/g4pet/detector/addBorderSurface Border1|box_pv|box_pv|MirrorSurf
/run/initialize
/exit
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
        assert "Created optical surface 'MirrorSurf'" in combined_output, (
            f"Optical surface not created. Output:\n{combined_output}"
        )
        assert "Created skin surface 'Skin1'" in combined_output, (
            f"Skin surface not created. Output:\n{combined_output}"
        )
        assert "Created border surface 'Border1'" in combined_output, (
            f"Border surface not created. Output:\n{combined_output}"
        )
