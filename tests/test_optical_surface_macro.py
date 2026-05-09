"""Test optical surface macro emission from generate_macro_file."""

import json
from pathlib import Path

from src.geometry_types import (
    GeometryState,
    Material,
    Solid,
    LogicalVolume,
    PhysicalVolumePlacement,
    OpticalSurface,
    SkinSurface,
    BorderSurface,
)
from src.project_manager import ProjectManager
from src.expression_evaluator import ExpressionEvaluator


def test_generate_macro_emits_optical_surface_commands(tmp_path):
    """Verify that generate_macro_file emits optical surface, skin surface,
    and border surface commands."""
    pm = ProjectManager(ExpressionEvaluator())

    state = GeometryState()
    state.add_material(Material("G4_Galactic", mat_type="nist"))
    state.add_material(Material("G4_Si", mat_type="nist"))
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

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "optical-surface-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "/g4pet/detector/addOpticalSurface MirrorSurf|glisur|polished|dielectric_dielectric|0.95" in macro_text
    assert "/g4pet/detector/addSkinSurface Skin1|box_lv|MirrorSurf" in macro_text
    assert "/g4pet/detector/addBorderSurface Border1|box_pv|box_pv|MirrorSurf" in macro_text


def test_generate_macro_skips_border_surface_with_unresolved_pv(tmp_path):
    """Border surfaces with unresolved PV refs should be skipped or commented."""
    pm = ProjectManager(ExpressionEvaluator())

    state = GeometryState()
    state.add_material(Material("G4_Galactic", mat_type="nist"))
    state.add_solid(Solid("world_solid", "box", {"x": "100", "y": "100", "z": "100"}))
    lv_world = LogicalVolume("world_lv", "world_solid", "G4_Galactic")
    state.add_logical_volume(lv_world)
    state.world_volume_ref = "world_lv"

    surf = OpticalSurface(name="Surf1", model="unified", finish="ground", surf_type="dielectric_metal", value="0.5")
    state.add_optical_surface(surf)

    border = BorderSurface(
        name="BadBorder",
        physvol1_ref="nonexistent-id",
        physvol2_ref="nonexistent-id",
        surfaceproperty_ref="Surf1",
    )
    state.add_border_surface(border)

    version_dir = tmp_path / "version"
    version_dir.mkdir()
    (version_dir / "version.json").write_text(json.dumps(state.to_dict()), encoding="utf-8")

    macro_path = Path(
        pm.generate_macro_file(
            "bad-border-job",
            {"events": 1},
            str(tmp_path),
            str(tmp_path),
            str(version_dir),
        )
    )
    macro_text = macro_path.read_text(encoding="utf-8")

    assert "BadBorder skipped" in macro_text or "# Border surface 'BadBorder'" in macro_text
