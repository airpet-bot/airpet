import io
from unittest.mock import patch

import pytest
from app import app as flask_app
from src.geometry_types import GeometryState, LogicalVolume, PhysicalVolumePlacement, Material
from src.expression_evaluator import ExpressionEvaluator
from src.gdml_parser import GDMLParser
from src.gdml_writer import GDMLWriter
from src.project_manager import ProjectManager


def _attrs_to_xml(attrs):
    return " ".join(f'{key}="{value}"' for key, value in attrs.items())

def test_sensitive_detector_auxinfo_round_trip():
    state = GeometryState()

    lv_world = LogicalVolume("World", "solid_world", "G4_Galactic")
    lv_box = LogicalVolume("Box_LV", "solid_box", "G4_Si", is_sensitive=True)

    state.add_logical_volume(lv_world)
    state.add_logical_volume(lv_box)
    state.world_volume_ref = "World"

    # Place Box inside World
    pv = PhysicalVolumePlacement("box_PV", "Box_LV")
    lv_world.add_child(pv)

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    # Verify exactly one auxiliary tag is emitted for the sensitive LV
    assert gdml_str.count('<auxiliary auxtype="SensDet"') == 1
    assert '<auxiliary auxtype="SensDet" auxvalue="Box_LV"/>' in gdml_str
    # Verify the non-sensitive LV has no auxiliary tag
    world_vol_start = gdml_str.find('<volume name="World">')
    world_vol_end = gdml_str.find('</volume>', world_vol_start) + len('</volume>')
    world_vol_chunk = gdml_str[world_vol_start:world_vol_end]
    assert '<auxiliary' not in world_vol_chunk

    # Parse the GDML back and verify is_sensitive survives the round-trip
    parser = GDMLParser()
    roundtrip_state = parser.parse_gdml_string(gdml_str)

    assert roundtrip_state.logical_volumes["Box_LV"].is_sensitive is True
    assert roundtrip_state.logical_volumes["World"].is_sensitive is False


def test_topological_sort():
    state = GeometryState()
    
    # Create a hierarchy: World -> Box1 -> Box2
    lv_world = LogicalVolume("World", "solid_world", "mat_air")
    lv_box1 = LogicalVolume("Box1", "solid_box1", "mat_lead")
    lv_box2 = LogicalVolume("Box2", "solid_box2", "mat_lead")
    
    state.add_logical_volume(lv_world)
    state.add_logical_volume(lv_box1)
    state.add_logical_volume(lv_box2)
    state.world_volume_ref = "World"
    
    # Place Box2 inside Box1
    pv2 = PhysicalVolumePlacement("PV2", "Box2")
    lv_box1.add_child(pv2)
    
    # Place Box1 inside World
    pv1 = PhysicalVolumePlacement("PV1", "Box1")
    lv_world.add_child(pv1)
    
    writer = GDMLWriter(state)
    sorted_structures = writer._topological_sort_structures()
    
    # Expected order: Box2, then Box1, then World
    names = [s.name for s in sorted_structures]
    assert names.index("Box2") < names.index("Box1")
    assert names.index("Box1") < names.index("World")

def test_tessellated_solid_deduplication():
    from src.geometry_types import Solid
    state = GeometryState()
    
    # Solid with two identical facets (absolute vertices)
    v1 = {'x': 0, 'y': 0, 'z': 0}
    v2 = {'x': 1, 'y': 0, 'z': 0}
    v3 = {'x': 0, 'y': 1, 'z': 0}
    
    facets = [
        {'type': 'triangular', 'vertices': [v1, v2, v3]},
        {'type': 'triangular', 'vertices': [v1, v2, v3]}
    ]
    solid = Solid("Tess", "tessellated", {"facets": facets})
    state.add_solid(solid)
    
    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()
    
    # Verify that only 3 unique positions are defined in the output
    # Each position tag looks like: <position name="Tess_v0" unit="mm" x="0" y="0" z="0"/>
    assert gdml_str.count("<position") == 3


def test_material_density_is_written_with_explicit_gdml_unit():
    state = GeometryState()

    mat = Material(
        "G4_Si",
        Z_expr="14",
        A_expr="28.085",
        density_expr="2.33*g/cm3",
        state="solid",
    )
    mat._evaluated_density = 0.00233  # internal g/mm^3
    state.add_material(mat)

    writer = GDMLWriter(state)
    writer._add_materials()
    gdml_str = writer.get_gdml_string()

    assert '<D value="2.33" unit="g/cm3"/>' in gdml_str


def test_plain_numeric_density_is_preserved_as_gdml_g_per_cm3():
    state = GeometryState()

    mat = Material(
        "G4_Galactic",
        Z_expr="1",
        A_expr="1.01",
        density_expr="1.0e-25",
        state="gas",
    )
    mat._evaluated_density = 1.0e-25
    state.add_material(mat)

    writer = GDMLWriter(state)
    writer._add_materials()
    gdml_str = writer.get_gdml_string()

    assert '<D value="1e-25" unit="g/cm3"/>' in gdml_str or '<D value="1.0e-25" unit="g/cm3"/>' in gdml_str


@pytest.mark.parametrize(
    "value,unit,expected_density_expr,expected_internal_density,expected_export_value",
    [
        ("2.33", "g/cm3", "2.33*g/cm3", 0.00233, "2.33"),
        ("2.33", "mg/cm3", "2.33*mg/cm3", 2.33e-06, "0.00233"),
        ("2330", "kg/m3", "2330*kg/m3", 0.00233, "2.33"),
    ],
)
def test_gdml_material_density_units_round_trip(value, unit, expected_density_expr, expected_internal_density, expected_export_value):
    gdml = f"""<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <materials>
    <material name="Silicon" state="solid" Z="14">
      <D value="{value}" unit="{unit}"/>
      <atom value="28.085"/>
    </material>
  </materials>
</gdml>
"""

    parser = GDMLParser()
    state = parser.parse_gdml_string(gdml)
    material = state.materials["Silicon"]

    assert material.density_expr == expected_density_expr

    evaluator = ExpressionEvaluator()
    success, evaluated_density = evaluator.evaluate(material.density_expr, verbose=False)
    assert success
    assert evaluated_density == pytest.approx(expected_internal_density)

    material._evaluated_density = evaluated_density

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    assert f'<D value="{expected_export_value}" unit="g/cm3"/>' in gdml_str


def test_gdml_entity_declarations_raise_clear_error(capsys):
    gdml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE gdml [
  <!ENTITY shared SYSTEM "shared.gdml">
]>
<gdml>
  <materials />
</gdml>
"""

    parser = GDMLParser()

    with pytest.raises(ValueError) as excinfo:
        parser.parse_gdml_string(gdml)

    captured = capsys.readouterr()
    expected_message = (
        "GDML entity declarations (`<!ENTITY ...>`) are not supported by this importer. "
        "Inline the entity definitions or export a single self-contained GDML file."
    )

    assert expected_message in str(excinfo.value)
    assert expected_message in captured.out
    assert parser.import_warnings == [expected_message]


def test_gdml_file_in_physvol_emits_clear_warning(capsys):
    gdml = """<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="100" y="100" z="100" lunit="mm"/>
  </solids>
  <structure>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <physvol name="include_module">
        <file name="module_piece.gdml"/>
      </physvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    parser = GDMLParser()
    state = parser.parse_gdml_string(gdml)
    captured = capsys.readouterr()
    expected_message = (
        "GDML <file> include 'module_piece.gdml' inside physvol 'include_module' under logical "
        "volume 'world_lv' is not supported yet. That placement will be ignored; inline the "
        "referenced GDML or merge the files before importing."
    )

    assert expected_message in captured.out
    assert parser.import_warnings == [expected_message]
    assert state.logical_volumes["world_lv"].content == []


@pytest.mark.parametrize(
    ("route_path", "file_field"),
    [
        ("/process_gdml", "gdmlFile"),
        ("/import_gdml_part", "partFile"),
    ],
)
def test_gdml_import_routes_surface_file_include_warnings(route_path, file_field):
    gdml = """<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="100" y="100" z="100" lunit="mm"/>
  </solids>
  <structure>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <physvol name="include_module">
        <file name="module_piece.gdml"/>
      </physvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    expected_message = (
        "GDML <file> include 'module_piece.gdml' inside physvol 'include_module' under logical "
        "volume 'world_lv' is not supported yet. That placement will be ignored; inline the "
        "referenced GDML or merge the files before importing."
    )

    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client, patch("app.get_project_manager_for_session", return_value=pm):
        response = client.post(
            route_path,
            data={file_field: (io.BytesIO(gdml.encode("utf-8")), "module_piece.gdml")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["import_warnings"] == [expected_message]


def test_parameterised_trd_dimensions_are_mapped_on_import(capsys):
    gdml = """<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="100" y="100" z="100" lunit="mm"/>
    <trd name="trd_solid" x1="1" x2="2" y1="3" y2="4" z="5" lunit="mm"/>
  </solids>
  <structure>
    <volume name="child_lv">
      <materialref ref="G4_Si"/>
      <solidref ref="trd_solid"/>
    </volume>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <paramvol name="trd_param" ncopies="1">
        <volumeref ref="child_lv"/>
        <parameterised_position_size>
          <parameters number="0">
            <trd_dimensions x1="1.1" x2="2.2" y1="3.3" y2="4.4" z="5.5" lunit="mm"/>
          </parameters>
        </parameterised_position_size>
      </paramvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    parser = GDMLParser()
    state = parser.parse_gdml_string(gdml)
    captured = capsys.readouterr()

    assert "No parameter mapping found for 'trd_dimensions'" not in captured.out
    assert "No parameter mapping found for 'trd_dimensions'" not in captured.err

    param_vol = state.logical_volumes["world_lv"].content
    assert param_vol.type == "parameterised"
    assert param_vol.volume_ref == "child_lv"
    assert len(param_vol.parameters) == 1

    param_set = param_vol.parameters[0]
    assert param_set.dimensions_type == "trd_dimensions"
    assert param_set.dimensions == {
        "x1": "1.1",
        "x2": "2.2",
        "y1": "3.3",
        "y2": "4.4",
        "z": "5.5",
    }


def test_unmapped_parameterised_dimensions_emit_clear_warning(capsys):
    gdml = """<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="100" y="100" z="100" lunit="mm"/>
    <box name="child_solid" x="10" y="10" z="10" lunit="mm"/>
  </solids>
  <structure>
    <volume name="child_lv">
      <materialref ref="G4_Si"/>
      <solidref ref="child_solid"/>
    </volume>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <paramvol name="mystery_param" ncopies="1">
        <volumeref ref="child_lv"/>
        <parameterised_position_size>
          <parameters number="0">
            <mystery_dimensions foo="1.1" bar="2.2" lunit="mm"/>
          </parameters>
        </parameterised_position_size>
      </paramvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    parser = GDMLParser()
    state = parser.parse_gdml_string(gdml)
    captured = capsys.readouterr()
    expected_message = (
        "No parameter mapping found for <mystery_dimensions> in <paramvol> 'mystery_param' "
        "referencing volume 'child_lv'. Keeping the raw GDML attribute names; this parameterised "
        "solid will import without AIRPET normalization yet."
    )

    assert expected_message in captured.out
    assert parser.import_warnings == [expected_message]

    param_vol = state.logical_volumes["world_lv"].content
    assert param_vol.type == "parameterised"
    assert len(param_vol.parameters) == 1
    assert param_vol.parameters[0].dimensions_type == "mystery_dimensions"
    assert param_vol.parameters[0].dimensions == {"foo": "1.1", "bar": "2.2"}


def test_parameterised_trap_dimensions_are_mapped_on_import(capsys):
    gdml = """<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="100" y="100" z="100" lunit="mm"/>
    <trap name="trap_solid" z="50" theta="10" phi="20" y1="30" x1="40" x2="50" alpha1="60" y2="70" x3="80" x4="90" alpha2="100" aunit="deg" lunit="mm"/>
  </solids>
  <structure>
    <volume name="child_lv">
      <materialref ref="G4_Si"/>
      <solidref ref="trap_solid"/>
    </volume>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <paramvol name="trap_param" ncopies="1">
        <volumeref ref="child_lv"/>
        <parameterised_position_size>
          <parameters number="0">
            <trap_dimensions z="5.5" theta="6.6" phi="7.7" y1="8.8" x1="9.9" x2="10.1" alpha1="11.2" y2="12.3" x3="13.4" x4="14.5" alpha2="15.6" lunit="mm" aunit="deg"/>
          </parameters>
        </parameterised_position_size>
      </paramvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    parser = GDMLParser()
    state = parser.parse_gdml_string(gdml)
    captured = capsys.readouterr()

    assert "No parameter mapping found for 'trap_dimensions'" not in captured.out
    assert "No parameter mapping found for 'trap_dimensions'" not in captured.err

    param_vol = state.logical_volumes["world_lv"].content
    assert param_vol.type == "parameterised"
    assert param_vol.volume_ref == "child_lv"
    assert len(param_vol.parameters) == 1

    param_set = param_vol.parameters[0]
    assert param_set.dimensions_type == "trap_dimensions"
    assert param_set.dimensions == {
        "z": "5.5",
        "theta": "6.6",
        "phi": "7.7",
        "y1": "8.8",
        "x1": "9.9",
        "x2": "10.1",
        "alpha1": "11.2",
        "y2": "12.3",
        "x3": "13.4",
        "x4": "14.5",
        "alpha2": "15.6",
    }


@pytest.mark.parametrize(
    "dimensions_tag,solid_attrs,parameter_attrs,expected_dimensions",
    [
        (
            "sphere_dimensions",
            {"rmin": "1", "rmax": "2", "startphi": "3", "deltaphi": "4", "starttheta": "5", "deltatheta": "6", "lunit": "mm", "aunit": "deg"},
            {"rmin": "1.1", "rmax": "2.2", "startphi": "3.3", "deltaphi": "4.4", "starttheta": "5.5", "deltatheta": "6.6", "lunit": "mm", "aunit": "deg"},
            {
                "rmin": "1.1",
                "rmax": "2.2",
                "startphi": "3.3",
                "deltaphi": "4.4",
                "starttheta": "5.5",
                "deltatheta": "6.6",
            },
        ),
        (
            "orb_dimensions",
            {"r": "5", "lunit": "mm"},
            {"r": "7.5", "lunit": "mm"},
            {"r": "7.5"},
        ),
        (
            "torus_dimensions",
            {"rmin": "1", "rmax": "2", "rtor": "3", "startphi": "4", "deltaphi": "5", "lunit": "mm", "aunit": "deg"},
            {"rmin": "1.25", "rmax": "2.5", "rtor": "3.75", "startphi": "4.5", "deltaphi": "5.5", "lunit": "mm", "aunit": "deg"},
            {"rmin": "1.25", "rmax": "2.5", "rtor": "3.75", "startphi": "4.5", "deltaphi": "5.5"},
        ),
        (
            "ellipsoid_dimensions",
            {"ax": "1", "by": "2", "cz": "3", "zcut1": "4", "zcut2": "5", "lunit": "mm"},
            {"ax": "1.5", "by": "2.5", "cz": "3.5", "zcut1": "4.5", "zcut2": "5.5", "lunit": "mm"},
            {"ax": "1.5", "by": "2.5", "cz": "3.5", "zcut1": "4.5", "zcut2": "5.5"},
        ),
        (
            "para_dimensions",
            {"x": "1", "y": "2", "z": "3", "alpha": "4", "theta": "5", "phi": "6", "lunit": "mm", "aunit": "deg"},
            {"x": "1.1", "y": "2.2", "z": "3.3", "alpha": "4.4", "theta": "5.5", "phi": "6.6", "lunit": "mm", "aunit": "deg"},
            {"x": "1.1", "y": "2.2", "z": "3.3", "alpha": "4.4", "theta": "5.5", "phi": "6.6"},
        ),
        (
            "hype_dimensions",
            {"rmin": "1", "rmax": "2", "inst": "3", "outst": "4", "z": "5", "lunit": "mm", "aunit": "deg"},
            {"rmin": "1.25", "rmax": "2.5", "inst": "3.75", "outst": "4.5", "z": "5.25", "lunit": "mm", "aunit": "deg"},
            {"rmin": "1.25", "rmax": "2.5", "inst": "3.75", "outst": "4.5", "z": "5.25"},
        ),
        (
            "eltube_dimensions",
            {"dx": "1", "dy": "2", "dz": "3", "lunit": "mm"},
            {"dx": "1.5", "dy": "2.5", "dz": "3.5", "lunit": "mm"},
            {"dx": "1.5", "dy": "2.5", "dz": "3.5"},
        ),
        (
            "elcone_dimensions",
            {"dx": "4", "dy": "5", "zmax": "6", "zcut": "7", "lunit": "mm"},
            {"dx": "4.5", "dy": "5.5", "zmax": "6.5", "zcut": "7.5", "lunit": "mm"},
            {"dx": "4.5", "dy": "5.5", "zmax": "6.5", "zcut": "7.5"},
        ),
        (
            "paraboloid_dimensions",
            {"rlo": "8", "rhi": "9", "dz": "10", "lunit": "mm"},
            {"rlo": "8.5", "rhi": "9.5", "dz": "10.5", "lunit": "mm"},
            {"rlo": "8.5", "rhi": "9.5", "dz": "10.5"},
        ),
    ],
)
def test_parameterised_additional_dimensions_are_mapped_on_import(
    dimensions_tag,
    solid_attrs,
    parameter_attrs,
    expected_dimensions,
    capsys,
):
    solid_tag = dimensions_tag.replace("_dimensions", "")

    gdml = f"""<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="100" y="100" z="100" lunit="mm"/>
    <{solid_tag} name="{solid_tag}_solid" {_attrs_to_xml(solid_attrs)}/>
  </solids>
  <structure>
    <volume name="child_lv">
      <materialref ref="G4_Si"/>
      <solidref ref="{solid_tag}_solid"/>
    </volume>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <paramvol name="{solid_tag}_param" ncopies="1">
        <volumeref ref="child_lv"/>
        <parameterised_position_size>
          <parameters number="0">
            <{dimensions_tag} {_attrs_to_xml(parameter_attrs)}/>
          </parameters>
        </parameterised_position_size>
      </paramvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    parser = GDMLParser()
    state = parser.parse_gdml_string(gdml)
    captured = capsys.readouterr()

    assert f"No parameter mapping found for '{dimensions_tag}'" not in captured.out
    assert f"No parameter mapping found for '{dimensions_tag}'" not in captured.err

    param_vol = state.logical_volumes["world_lv"].content
    assert param_vol.type == "parameterised"
    assert param_vol.volume_ref == "child_lv"
    assert len(param_vol.parameters) == 1

    param_set = param_vol.parameters[0]
    assert param_set.dimensions_type == dimensions_tag
    assert param_set.dimensions == expected_dimensions


@pytest.mark.parametrize(
    "dimensions_tag,solid_attrs,parameter_attrs,expected_dimensions",
    [
        (
            "twistedbox_dimensions",
            {"PhiTwist": "10", "x": "20", "y": "30", "z": "40", "lunit": "mm", "aunit": "deg"},
            {"PhiTwist": "10.5", "x": "20.5", "y": "30.5", "z": "40.5", "lunit": "mm", "aunit": "deg"},
            {"PhiTwist": "10.5", "x": "20.5", "y": "30.5", "z": "40.5"},
        ),
        (
            "twistedtrd_dimensions",
            {"PhiTwist": "5", "x1": "6", "x2": "7", "y1": "8", "y2": "9", "z": "10", "lunit": "mm", "aunit": "deg"},
            {"PhiTwist": "5.5", "x1": "6.5", "x2": "7.5", "y1": "8.5", "y2": "9.5", "z": "10.5", "lunit": "mm", "aunit": "deg"},
            {"PhiTwist": "5.5", "x1": "6.5", "x2": "7.5", "y1": "8.5", "y2": "9.5", "z": "10.5"},
        ),
        (
            "twistedtrap_dimensions",
            {
                "PhiTwist": "1",
                "z": "2",
                "Theta": "3",
                "Phi": "4",
                "y1": "5",
                "x1": "6",
                "x2": "7",
                "y2": "8",
                "x3": "9",
                "x4": "10",
                "Alph": "11",
                "lunit": "mm",
                "aunit": "deg",
            },
            {
                "PhiTwist": "1.5",
                "z": "2.5",
                "Theta": "3.5",
                "Phi": "4.5",
                "y1": "5.5",
                "x1": "6.5",
                "x2": "7.5",
                "y2": "8.5",
                "x3": "9.5",
                "x4": "10.5",
                "Alph": "11.5",
                "lunit": "mm",
                "aunit": "deg",
            },
            {
                "PhiTwist": "1.5",
                "z": "2.5",
                "Theta": "3.5",
                "Phi": "4.5",
                "y1": "5.5",
                "x1": "6.5",
                "x2": "7.5",
                "y2": "8.5",
                "x3": "9.5",
                "x4": "10.5",
                "Alph": "11.5",
            },
        ),
        (
            "twistedtubs_dimensions",
            {"twistedangle": "12", "endinnerrad": "13", "endouterrad": "14", "zlen": "15", "phi": "16", "lunit": "mm", "aunit": "deg"},
            {"twistedangle": "12.5", "endinnerrad": "13.5", "endouterrad": "14.5", "zlen": "15.5", "phi": "16.5", "lunit": "mm", "aunit": "deg"},
            {"twistedangle": "12.5", "endinnerrad": "13.5", "endouterrad": "14.5", "zlen": "15.5", "phi": "16.5"},
        ),
    ],
)
def test_parameterised_twisted_dimensions_are_mapped_on_import(
    dimensions_tag,
    solid_attrs,
    parameter_attrs,
    expected_dimensions,
    capsys,
):
    solid_tag = dimensions_tag.replace("_dimensions", "")

    gdml = f"""<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="100" y="100" z="100" lunit="mm"/>
    <{solid_tag} name="{solid_tag}_solid" {_attrs_to_xml(solid_attrs)}/>
  </solids>
  <structure>
    <volume name="child_lv">
      <materialref ref="G4_Si"/>
      <solidref ref="{solid_tag}_solid"/>
    </volume>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <paramvol name="{solid_tag}_param" ncopies="1">
        <volumeref ref="child_lv"/>
        <parameterised_position_size>
          <parameters number="0">
            <{dimensions_tag} {_attrs_to_xml(parameter_attrs)}/>
          </parameters>
        </parameterised_position_size>
      </paramvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    parser = GDMLParser()
    state = parser.parse_gdml_string(gdml)
    captured = capsys.readouterr()

    assert f"No parameter mapping found for '{dimensions_tag}'" not in captured.out
    assert f"No parameter mapping found for '{dimensions_tag}'" not in captured.err

    param_vol = state.logical_volumes["world_lv"].content
    assert param_vol.type == "parameterised"
    assert param_vol.volume_ref == "child_lv"
    assert len(param_vol.parameters) == 1

    param_set = param_vol.parameters[0]
    assert param_set.dimensions_type == dimensions_tag
    assert param_set.dimensions == expected_dimensions


@pytest.mark.parametrize(
    (
        "solid_tag",
        "solid_attrs",
        "dimensions_tag",
        "parameter_attrs",
        "parameter_zplanes",
        "expected_dimensions",
        "expected_evaluated_dimensions",
    ),
    [
        (
            "polycone",
            {
                "startphi": "0",
                "deltaphi": "180",
                "lunit": "mm",
                "aunit": "deg",
            },
            "polycone_dimensions",
            {
                "numRZ": "2",
                "startPhi": "15",
                "openPhi": "90",
                "lunit": "mm",
                "aunit": "deg",
            },
            [
                {"z": "-12", "rmin": "0", "rmax": "20"},
                {"z": "12", "rmin": "5", "rmax": "25"},
            ],
            {
                "numRZ": "2",
                "startPhi": "15",
                "openPhi": "90",
                "zplanes": [
                    {"z": "-12", "rmin": "0", "rmax": "20"},
                    {"z": "12", "rmin": "5", "rmax": "25"},
                ],
            },
            {
                "numRZ": 2.0,
                "startPhi": 15.0,
                "openPhi": 90.0,
                "zplanes": [
                    {"z": -12.0, "rmin": 0.0, "rmax": 20.0},
                    {"z": 12.0, "rmin": 5.0, "rmax": 25.0},
                ],
            },
        ),
        (
            "polyhedra",
            {
                "numsides": "8",
                "startphi": "30",
                "deltaphi": "270",
                "lunit": "mm",
                "aunit": "deg",
            },
            "polyhedra_dimensions",
            {
                "numRZ": "2",
                "numSide": "8",
                "startPhi": "30",
                "openPhi": "120",
                "lunit": "mm",
                "aunit": "deg",
            },
            [
                {"z": "-8", "rmin": "1", "rmax": "9"},
                {"z": "8", "rmin": "2", "rmax": "10"},
            ],
            {
                "numRZ": "2",
                "numSide": "8",
                "startPhi": "30",
                "openPhi": "120",
                "zplanes": [
                    {"z": "-8", "rmin": "1", "rmax": "9"},
                    {"z": "8", "rmin": "2", "rmax": "10"},
                ],
            },
            {
                "numRZ": 2.0,
                "numSide": 8.0,
                "startPhi": 30.0,
                "openPhi": 120.0,
                "zplanes": [
                    {"z": -8.0, "rmin": 1.0, "rmax": 9.0},
                    {"z": 8.0, "rmin": 2.0, "rmax": 10.0},
                ],
            },
        ),
    ],
)
def test_parameterised_polycone_and_polyhedra_dimensions_round_trip(
    solid_tag,
    solid_attrs,
    dimensions_tag,
    parameter_attrs,
    parameter_zplanes,
    expected_dimensions,
    expected_evaluated_dimensions,
    capsys,
):
    solid_zplanes = "\n".join(
        f'      <zplane {_attrs_to_xml(zplane)}/>' for zplane in parameter_zplanes
    )
    parameter_zplanes_xml = "\n".join(
        f'            <zplane {_attrs_to_xml(zplane)}/>' for zplane in parameter_zplanes
    )

    gdml = f"""<?xml version="1.0" encoding="UTF-8"?>
<gdml>
  <solids>
    <box name="world_solid" x="200" y="200" z="200" lunit="mm"/>
    <box name="container_solid" x="80" y="80" z="80" lunit="mm"/>
    <{solid_tag} name="{solid_tag}_solid" {_attrs_to_xml(solid_attrs)}>
{solid_zplanes}
    </{solid_tag}>
  </solids>
  <structure>
    <volume name="child_lv">
      <materialref ref="G4_Si"/>
      <solidref ref="{solid_tag}_solid"/>
    </volume>
    <volume name="container_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="container_solid"/>
      <paramvol name="{dimensions_tag}_param" ncopies="1">
        <volumeref ref="child_lv"/>
        <parameterised_position_size>
          <parameters number="0">
            <{dimensions_tag} {_attrs_to_xml(parameter_attrs)}>
{parameter_zplanes_xml}
            </{dimensions_tag}>
          </parameters>
        </parameterised_position_size>
      </paramvol>
    </volume>
    <volume name="world_lv">
      <materialref ref="G4_Galactic"/>
      <solidref ref="world_solid"/>
      <physvol name="container_pv">
        <volumeref ref="container_lv"/>
        <position x="0" y="0" z="0" unit="mm"/>
      </physvol>
    </volume>
  </structure>
  <setup>
    <world ref="world_lv"/>
  </setup>
</gdml>
"""

    pm = ProjectManager(ExpressionEvaluator())
    state = pm.load_gdml_from_string(gdml)
    capsys.readouterr()

    assert pm.gdml_parser.import_warnings == []

    param_vol = state.logical_volumes["container_lv"].content
    assert param_vol.type == "parameterised"
    assert param_vol.volume_ref == "child_lv"
    assert len(param_vol.parameters) == 1

    param_set = param_vol.parameters[0]
    assert param_set.dimensions_type == dimensions_tag
    assert param_set.dimensions == expected_dimensions
    assert param_set._evaluated_dimensions == expected_evaluated_dimensions

    exported = pm.export_to_gdml_string()
    roundtrip_pm = ProjectManager(ExpressionEvaluator())
    roundtrip_state = roundtrip_pm.load_gdml_from_string(exported)
    capsys.readouterr()

    assert roundtrip_pm.gdml_parser.import_warnings == []

    roundtrip_param_vol = roundtrip_state.logical_volumes["container_lv"].content
    roundtrip_param_set = roundtrip_param_vol.parameters[0]
    assert roundtrip_param_set.dimensions_type == dimensions_tag
    assert roundtrip_param_set.dimensions == expected_dimensions
    assert roundtrip_param_set._evaluated_dimensions == expected_evaluated_dimensions


def test_gdml_sensitive_detector_round_trip():
    """Sensitive-detector assignments must survive GDML export and re-import."""
    state = GeometryState()

    # Simple solids
    from src.geometry_types import Solid
    state.add_solid(Solid("world_solid", "box", {"x": "100", "y": "100", "z": "100"}))
    state.add_solid(Solid("det_solid", "box", {"x": "10", "y": "10", "z": "10"}))

    # Materials (NIST names only)
    state.add_material(Material("G4_Galactic", mat_type="nist"))
    state.add_material(Material("G4_Si", mat_type="nist"))

    # Logical volumes: one sensitive, one not
    lv_world = LogicalVolume("world_lv", "world_solid", "G4_Galactic", is_sensitive=False)
    lv_det = LogicalVolume("det_lv", "det_solid", "G4_Si", is_sensitive=True)
    state.add_logical_volume(lv_world)
    state.add_logical_volume(lv_det)
    state.world_volume_ref = "world_lv"

    # Place det inside world
    pv = PhysicalVolumePlacement("det_pv", "det_lv")
    lv_world.add_child(pv)

    # Export to GDML
    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    # Verify the auxiliary tag appears exactly once for the sensitive LV
    assert gdml_str.count('<auxiliary auxtype="SensDet"') == 1
    assert '<auxiliary auxtype="SensDet" auxvalue="det_lv"/>' in gdml_str
    # Verify it is inside the det_lv volume block (simple substring check)
    det_volume_start = gdml_str.find('<volume name="det_lv">')
    det_volume_end = gdml_str.find('</volume>', det_volume_start)
    det_volume_block = gdml_str[det_volume_start:det_volume_end + len('</volume>')]
    assert '<auxiliary auxtype="SensDet" auxvalue="det_lv"/>' in det_volume_block

    # Parse back
    parser = GDMLParser()
    imported_state = parser.parse_gdml_string(gdml_str)

    assert imported_state.logical_volumes["world_lv"].is_sensitive is False
    assert imported_state.logical_volumes["det_lv"].is_sensitive is True


def test_gdml_material_properties_round_trip():
    """Material optical properties must survive GDML export and re-import."""
    state = GeometryState()

    from src.geometry_types import Solid, Define
    state.add_solid(Solid("world_solid", "box", {"x": "100", "y": "100", "z": "100"}))

    # Add matrix defines so the property references are valid
    state.add_define(Define("AIRRINDEX", "matrix", {"coldim": "2", "values": ["1.0*eV", "1.0", "2.0*eV", "1.33"]}))
    state.add_define(Define("AIRABSLENGTH", "matrix", {"coldim": "1", "values": ["100.0"]}))

    mat = Material(
        "OpticalAir",
        Z_expr="14",
        A_expr="28.085",
        density_expr="0.001225*g/cm3",
        state="gas",
        properties={"RINDEX": "AIRRINDEX", "ABSLENGTH": "AIRABSLENGTH"},
    )
    state.add_material(mat)

    lv_world = LogicalVolume("world_lv", "world_solid", "OpticalAir")
    state.add_logical_volume(lv_world)
    state.world_volume_ref = "world_lv"

    # Export to GDML
    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    # Verify property tags are emitted inside the material
    mat_start = gdml_str.find('<material name="OpticalAir"')
    mat_end = gdml_str.find('</material>', mat_start) + len('</material>')
    mat_block = gdml_str[mat_start:mat_end]
    assert '<property name="RINDEX" ref="AIRRINDEX"/>' in mat_block
    assert '<property name="ABSLENGTH" ref="AIRABSLENGTH"/>' in mat_block
    # Verify matrices are in defines
    assert '<matrix name="AIRRINDEX"' in gdml_str
    assert '<matrix name="AIRABSLENGTH"' in gdml_str

    # Parse back
    parser = GDMLParser()
    imported_state = parser.parse_gdml_string(gdml_str)

    imported_mat = imported_state.materials["OpticalAir"]
    # coldim="2" matrix refs are resolved to evaluated vector data; coldim="1" remains a string ref
    assert imported_mat.properties["RINDEX"] == [[0.001, 1.0], [0.002, 1.33]]
    assert imported_mat.properties["ABSLENGTH"] == "AIRABSLENGTH"

    # Verify re-export from the resolved state creates a new matrix define for the vector
    writer_rt = GDMLWriter(imported_state)
    gdml_str_rt = writer_rt.get_gdml_string()
    assert '<property name="RINDEX" ref="OpticalAir_RINDEX_matprop_vec"/>' in gdml_str_rt
    assert '<matrix name="OpticalAir_RINDEX_matprop_vec"' in gdml_str_rt
    assert 'coldim="2"' in gdml_str_rt

    # Parse again and verify vector data survives the second round-trip
    parser2 = GDMLParser()
    imported_state2 = parser2.parse_gdml_string(gdml_str_rt)
    assert imported_state2.materials["OpticalAir"].properties["RINDEX"] == [[0.001, 1.0], [0.002, 1.33]]

    # Verify a material without properties round-trips as empty dict
    mat_no_props = Material("PlainSi", Z_expr="14", A_expr="28.085", density_expr="2.33*g/cm3")
    state2 = GeometryState()
    state2.add_solid(Solid("box_solid", "box", {"x": "10", "y": "10", "z": "10"}))
    state2.add_material(mat_no_props)
    lv2 = LogicalVolume("lv2", "box_solid", "PlainSi")
    state2.add_logical_volume(lv2)
    state2.world_volume_ref = "lv2"

    writer2 = GDMLWriter(state2)
    gdml_str2 = writer2.get_gdml_string()

    parser2 = GDMLParser()
    imported_state2 = parser2.parse_gdml_string(gdml_str2)
    assert imported_state2.materials["PlainSi"].properties == {}


def test_gdml_optical_surface_round_trip():
    """OpticalSurface must survive GDML export and re-import."""
    from src.geometry_types import Solid, OpticalSurface

    state = GeometryState()
    state.add_solid(Solid("world_solid", "box", {"x": "100", "y": "100", "z": "100"}))
    state.add_material(Material("G4_Galactic", mat_type="nist"))

    surf = OpticalSurface(
        name="MirrorSurf",
        model="glisur",
        finish="polished",
        surf_type="dielectric_metal",
        value="1.0",
    )
    surf.properties["REFLECTIVITY"] = "ref_mat"
    state.add_optical_surface(surf)

    from src.geometry_types import Define
    state.defines["ref_mat"] = Define("ref_mat", "matrix", {"coldim": "2", "values": ["1.0", "0.5"]})

    lv_world = LogicalVolume("world_lv", "world_solid", "G4_Galactic")
    state.add_logical_volume(lv_world)
    state.world_volume_ref = "world_lv"

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    # Verify opticalsurface tag with attributes and nested property
    assert '<opticalsurface name="MirrorSurf"' in gdml_str
    assert 'model="glisur"' in gdml_str
    assert 'finish="polished"' in gdml_str
    assert 'type="dielectric_metal"' in gdml_str
    assert 'value="1.0"' in gdml_str
    assert '<property name="REFLECTIVITY" ref="ref_mat"/>' in gdml_str

    parser = GDMLParser()
    imported_state = parser.parse_gdml_string(gdml_str)

    imported_surf = imported_state.optical_surfaces["MirrorSurf"]
    assert imported_surf.model == "glisur"
    assert imported_surf.finish == "polished"
    assert imported_surf.type == "dielectric_metal"
    assert imported_surf.value == "1.0"
    assert imported_surf.properties == {"REFLECTIVITY": "ref_mat"}


def test_gdml_skin_surface_round_trip():
    """SkinSurface must survive GDML export and re-import."""
    from src.geometry_types import Solid, OpticalSurface, SkinSurface

    state = GeometryState()
    state.add_solid(Solid("world_solid", "box", {"x": "100", "y": "100", "z": "100"}))
    state.add_material(Material("G4_Galactic", mat_type="nist"))

    surf = OpticalSurface(name="SkinOptSurf", model="glisur", finish="ground", surf_type="dielectric_dielectric", value="0.5")
    state.add_optical_surface(surf)

    lv_world = LogicalVolume("world_lv", "world_solid", "G4_Galactic")
    state.add_logical_volume(lv_world)
    state.world_volume_ref = "world_lv"

    skin = SkinSurface(name="Skin1", volume_ref="world_lv", surfaceproperty_ref="SkinOptSurf")
    state.add_skin_surface(skin)

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    assert '<skinsurface name="Skin1" surfaceproperty="SkinOptSurf">' in gdml_str
    assert '<volumeref ref="world_lv"/>' in gdml_str

    parser = GDMLParser()
    imported_state = parser.parse_gdml_string(gdml_str)

    imported_skin = imported_state.skin_surfaces["Skin1"]
    assert imported_skin.volume_ref == "world_lv"
    assert imported_skin.surfaceproperty_ref == "SkinOptSurf"


def test_gdml_border_surface_round_trip():
    """BorderSurface must survive GDML export and re-import."""
    from src.geometry_types import Solid, OpticalSurface, BorderSurface

    state = GeometryState()
    state.add_solid(Solid("world_solid", "box", {"x": "100", "y": "100", "z": "100"}))
    state.add_solid(Solid("box_solid", "box", {"x": "10", "y": "10", "z": "10"}))
    state.add_material(Material("G4_Galactic", mat_type="nist"))
    state.add_material(Material("G4_Si", mat_type="nist"))

    surf = OpticalSurface(name="BorderOptSurf", model="glisur", finish="polished", surf_type="dielectric_dielectric", value="0.8")
    state.add_optical_surface(surf)

    lv_world = LogicalVolume("world_lv", "world_solid", "G4_Galactic")
    lv_box = LogicalVolume("box_lv", "box_solid", "G4_Si")
    state.add_logical_volume(lv_world)
    state.add_logical_volume(lv_box)
    state.world_volume_ref = "world_lv"

    pv_box = PhysicalVolumePlacement("box_pv", "box_lv")
    lv_world.add_child(pv_box)

    border = BorderSurface(
        name="Border1",
        physvol1_ref=pv_box.id,
        physvol2_ref=pv_box.id,
        surfaceproperty_ref="BorderOptSurf",
    )
    state.add_border_surface(border)

    writer = GDMLWriter(state)
    gdml_str = writer.get_gdml_string()

    assert '<bordersurface name="Border1" surfaceproperty="BorderOptSurf">' in gdml_str
    assert gdml_str.count('<physvolref ref="box_pv"/>') == 2

    parser = GDMLParser()
    imported_state = parser.parse_gdml_string(gdml_str)

    imported_border = imported_state.border_surfaces["Border1"]
    assert imported_border.surfaceproperty_ref == "BorderOptSurf"
    # The writer emits PV names; the parser resolves them back to new PV IDs.
    # Verify the IDs point to PVs with the correct names.
    imported_pv1 = imported_state._find_pv_by_id(imported_border.physvol1_ref)
    imported_pv2 = imported_state._find_pv_by_id(imported_border.physvol2_ref)
    assert imported_pv1 is not None and imported_pv1.name == "box_pv"
    assert imported_pv2 is not None and imported_pv2.name == "box_pv"


