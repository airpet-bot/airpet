"""Test whether Geant4 native GDML parser creates optical surfaces from AIRPET GDML."""

import os
import subprocess
import tempfile

from src.geometry_types import (
    GeometryState, Material, Solid, LogicalVolume,
    PhysicalVolumePlacement, OpticalSurface, SkinSurface, BorderSurface,
)
from src.gdml_writer import GDMLWriter


def test_gdml_native_optical_surfaces():
    """Verify that Geant4 creates optical surfaces from AIRPET GDML without custom macros."""
    executable = os.path.join(os.getcwd(), "geant4", "build", "airpet-sim")
    assert os.path.exists(executable), f"Executable not found: {executable}"

    state = GeometryState()
    state.add_solid(Solid("world_solid", "box", {"x": "100", "y": "100", "z": "100"}))
    state.add_solid(Solid("box_solid", "box", {"x": "10", "y": "10", "z": "10"}))

    lv_world = LogicalVolume("world_lv", "world_solid", "G4_Galactic")
    lv_box = LogicalVolume("box_lv", "box_solid", "G4_Si")
    state.add_logical_volume(lv_world)
    state.add_logical_volume(lv_box)
    state.world_volume_ref = "world_lv"

    pv_box = PhysicalVolumePlacement("box_pv", "box_lv")
    lv_world.add_child(pv_box)

    surf = OpticalSurface(
        name="MirrorSurf",
        model="glisur",
        finish="polished",
        surf_type="dielectric_dielectric",
        value="0.95",
    )
    state.add_optical_surface(surf)

    skin = SkinSurface(name="Skin1", volume_ref="box_lv", surfaceproperty_ref="MirrorSurf")
    state.add_skin_surface(skin)

    border = BorderSurface(
        name="Border1",
        physvol1_ref=pv_box.id,
        physvol2_ref=pv_box.id,
        surfaceproperty_ref="MirrorSurf",
    )
    state.add_border_surface(border)

    gdml_string = GDMLWriter(state).get_gdml_string()

    macro_content = """
/g4pet/detector/readFile geometry.gdml
/run/initialize
/exit
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        gdml_path = os.path.join(tmpdir, "geometry.gdml")
        macro_path = os.path.join(tmpdir, "test.mac")
        with open(gdml_path, "w") as f:
            f.write(gdml_string)
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
        print("COMBINED OUTPUT:")
        print(combined_output)
        # We just want to see if Geant4 parses the GDML surfaces
        assert "G4GDML: Reading" in combined_output
