import sys
import types
import hashlib
import json
from unittest.mock import patch


class _DummyOccObject:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return self


def _install_occ_stubs():
    if 'OCC' in sys.modules:
        return

    occ_module = types.ModuleType('OCC')
    occ_module.__path__ = []
    core_module = types.ModuleType('OCC.Core')
    core_module.__path__ = []

    sys.modules['OCC'] = occ_module
    sys.modules['OCC.Core'] = core_module

    module_specs = {
        'OCC.Core.STEPControl': {'STEPControl_Reader': _DummyOccObject},
        'OCC.Core.TopAbs': {
            'TopAbs_SOLID': 0,
            'TopAbs_FACE': 1,
            'TopAbs_REVERSED': 2,
        },
        'OCC.Core.TopExp': {'TopExp_Explorer': _DummyOccObject},
        'OCC.Core.BRep': {'BRep_Tool': type('_BRepTool', (), {'Triangulation': staticmethod(lambda *args, **kwargs: None)})},
        'OCC.Core.BRepMesh': {'BRepMesh_IncrementalMesh': _DummyOccObject},
        'OCC.Core.TopLoc': {'TopLoc_Location': _DummyOccObject},
        'OCC.Core.gp': {'gp_Trsf': _DummyOccObject},
        'OCC.Core.TDF': {'TDF_Label': _DummyOccObject, 'TDF_LabelSequence': _DummyOccObject},
        'OCC.Core.XCAFDoc': {
            'XCAFDoc_DocumentTool': type(
                '_XCAFDocDocumentTool',
                (),
                {'ShapeTool': staticmethod(lambda *args, **kwargs: _DummyOccObject())},
            )
        },
        'OCC.Core.STEPCAFControl': {'STEPCAFControl_Reader': _DummyOccObject},
        'OCC.Core.TDocStd': {'TDocStd_Document': _DummyOccObject},
    }

    for module_name, attrs in module_specs.items():
        module = types.ModuleType(module_name)
        for attr_name, value in attrs.items():
            setattr(module, attr_name, value)
        sys.modules[module_name] = module


_install_occ_stubs()

from src.expression_evaluator import ExpressionEvaluator
from src.geometry_types import Assembly, GeometryState, LogicalVolume, PhysicalVolumePlacement, Solid
from src.project_manager import ProjectManager


def _make_pm():
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()
    return pm


class DummyStepUpload:
    def __init__(self, data, filename):
        self.data = data
        self.filename = filename

    def save(self, path):
        with open(path, 'wb') as handle:
            handle.write(self.data)


def _build_fake_imported_state():
    state = GeometryState()
    state.grouping_name = 'fixture_import'

    solid = Solid('fixture_solid', 'box', {'x': '1', 'y': '2', 'z': '3'})
    state.add_solid(solid)

    lv = LogicalVolume('fixture_lv', solid.name, 'G4_STAINLESS-STEEL')
    state.add_logical_volume(lv)

    assembly = Assembly('fixture_assembly')
    assembly_child = PhysicalVolumePlacement(
        name='fixture_lv_placement',
        volume_ref=lv.name,
        parent_lv_name=assembly.name,
    )
    assembly.add_placement(assembly_child)
    state.add_assembly(assembly)

    top_level_pv = PhysicalVolumePlacement(
        name='fixture_assembly_placement',
        volume_ref=assembly.name,
        parent_lv_name='World',
    )
    state.placements_to_add = [top_level_pv]

    return state, solid, lv, assembly, assembly_child, top_level_pv


def test_step_import_provenance_roundtrips_through_saved_project_state():
    payload_bytes = b'STEP-DATA'
    expected_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    imported_state, solid, lv, assembly, assembly_child, top_level_pv = _build_fake_imported_state()

    pm = _make_pm()
    upload = DummyStepUpload(payload_bytes, 'fixture.step')

    with patch('src.project_manager.parse_step_file', return_value=imported_state):
        success, error_msg, import_report = pm.import_step_with_options(
            upload,
            {
                'groupingName': 'fixture_import',
                'placementMode': 'assembly',
                'parentLVName': 'World',
                'offset': {'x': '0', 'y': '0', 'z': '0'},
                'smartImport': True,
            },
        )

    assert success is True
    assert error_msg is None
    assert import_report is None

    assert len(pm.current_geometry_state.cad_imports) == 1
    import_record = pm.current_geometry_state.cad_imports[0]
    assert import_record['import_id'].startswith('step_import_')
    assert import_record['source'] == {
        'format': 'step',
        'filename': 'fixture.step',
        'sha256': expected_sha256,
        'size_bytes': len(payload_bytes),
    }
    assert import_record['options'] == {
        'grouping_name': 'fixture_import',
        'placement_mode': 'assembly',
        'parent_lv_name': 'World',
        'offset': {'x': '0', 'y': '0', 'z': '0'},
        'smart_import_enabled': True,
    }
    assert import_record['created_object_ids']['solid_ids'] == [solid.id]
    assert import_record['created_object_ids']['logical_volume_ids'] == [lv.id]
    assert import_record['created_object_ids']['assembly_ids'] == [assembly.id]
    assert set(import_record['created_object_ids']['placement_ids']) == {assembly_child.id, top_level_pv.id}
    assert import_record['created_group_names'] == {
        'solid': 'fixture_import_solids',
        'logical_volume': 'fixture_import_lvs',
        'assembly': 'fixture_import_assemblies',
    }

    saved_payload = json.loads(pm.save_project_to_json_string())
    assert saved_payload['cad_imports'][0] == import_record

    pm_round_tripped = ProjectManager(ExpressionEvaluator())
    pm_round_tripped.load_project_from_json_string(json.dumps(saved_payload))
    assert pm_round_tripped.current_geometry_state.cad_imports[0] == import_record
