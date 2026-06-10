"""Regression tests for AIRPET input validation and containment safeguards.

These tests protect route and project-manager behavior for materials, particle
sources, solids, placements, and geometry preflight checks.
"""
import pytest
from unittest.mock import patch
from src.project_manager import ProjectManager
from src.expression_evaluator import ExpressionEvaluator
from app import app as flask_app


@pytest.fixture
def pm():
    """Fresh ProjectManager with an empty project."""
    manager = ProjectManager(ExpressionEvaluator())
    manager.create_empty_project()
    return manager


@pytest.fixture
def client(pm):
    """Flask test client wired to the project manager."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c, \
         patch("app.get_project_manager_for_session", return_value=pm):
        yield c


# --- F-031: Material validation ---

class TestMaterialValidation:
    """F-031: Materials must reject invalid density, Z, A, and name."""

    def test_empty_name_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': '',
            'params': {'density_expr': '1', 'Z_expr': '1', 'A_expr': '1'}
        })
        assert resp.status_code == 400
        # Route returns 400 for missing name
        assert 'missing' in resp.get_json()['error'].lower() or 'empty' in resp.get_json()['error'].lower()

    def test_whitespace_name_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': '   ',
            'params': {'density_expr': '1', 'Z_expr': '1', 'A_expr': '1'}
        })
        assert resp.status_code == 400

    def test_negative_density_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': 'bad_mat',
            'params': {'density_expr': '-1', 'Z_expr': '1', 'A_expr': '1'}
        })
        assert resp.status_code == 400
        assert 'density' in resp.get_json()['error'].lower()

    def test_zero_density_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': 'bad_mat',
            'params': {'density_expr': '0', 'Z_expr': '1', 'A_expr': '1'}
        })
        assert resp.status_code == 400

    def test_string_density_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': 'bad_mat',
            'params': {'density_expr': 'abc', 'Z_expr': '1', 'A_expr': '1'}
        })
        assert resp.status_code == 400

    def test_negative_z_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': 'bad_mat',
            'params': {'density_expr': '1', 'Z_expr': '-1', 'A_expr': '1'}
        })
        assert resp.status_code == 400
        assert 'z' in resp.get_json()['error'].lower()

    def test_zero_z_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': 'bad_mat',
            'params': {'density_expr': '1', 'Z_expr': '0', 'A_expr': '1'}
        })
        assert resp.status_code == 400

    def test_negative_a_rejected(self, client):
        resp = client.post('/add_material', json={
            'name': 'bad_mat',
            'params': {'density_expr': '1', 'Z_expr': '1', 'A_expr': '-5'}
        })
        assert resp.status_code == 400

    def test_valid_material_accepted(self, client):
        resp = client.post('/add_material', json={
            'name': 'good_mat',
            'params': {'density_expr': '1 g/cm3', 'Z_expr': '13', 'A_expr': '27'}
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_nist_material_without_density_accepted(self, client):
        resp = client.post('/add_material', json={
            'name': 'G4_Si',
            'params': {
                'mat_type': 'nist',
                'components': [],
                'Z_expr': None,
                'A_expr': None,
                'density_expr': None,
            },
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True


# --- F-032: Source validation ---

class TestSourceValidation:
    """F-032: Sources must reject invalid energy, ion Z, and activity."""

    def test_negative_energy_rejected(self, client):
        resp = client.post('/api/add_source', json={
            'name': 'bad_src',
            'gps_commands': {'energy': '-1 MeV', 'particle/type': 'e-'},
            'position': {'x': '0', 'y': '0', 'z': '0'}
        })
        assert resp.status_code == 400
        assert 'energy' in resp.get_json()['error'].lower()

    def test_zero_energy_rejected(self, client):
        resp = client.post('/api/add_source', json={
            'name': 'bad_src',
            'gps_commands': {'energy': '0', 'particle/type': 'e-'},
            'position': {'x': '0', 'y': '0', 'z': '0'}
        })
        assert resp.status_code == 400

    def test_invalid_energy_expression_rejected(self, client):
        resp = client.post('/api/add_source', json={
            'name': 'bad_src',
            'gps_commands': {'energy': 'abc', 'particle/type': 'e-'},
            'position': {'x': '0', 'y': '0', 'z': '0'}
        })
        assert resp.status_code == 400

    def test_negative_ion_z_rejected(self, client):
        resp = client.post('/api/add_source', json={
            'name': 'bad_src',
            'gps_commands': {'energy': '1 MeV', 'particle/type': 'ion'},
            'ion_params': {'Z': '-1', 'A': '12'},
            'position': {'x': '0', 'y': '0', 'z': '0'}
        })
        assert resp.status_code == 400
        assert 'ionz' in resp.get_json()['error'].lower()

    def test_negative_activity_rejected(self, client):
        resp = client.post('/api/add_source', json={
            'name': 'bad_src',
            'gps_commands': {'energy': '1 MeV', 'particle/type': 'e-'},
            'activity': '-5',
            'position': {'x': '0', 'y': '0', 'z': '0'}
        })
        assert resp.status_code == 400
        assert 'activity' in resp.get_json()['error'].lower()

    def test_empty_source_name_rejected(self, client):
        resp = client.post('/api/add_source', json={
            'name': '',
            'gps_commands': {'energy': '1 MeV', 'particle/type': 'e-'},
            'position': {'x': '0', 'y': '0', 'z': '0'}
        })
        assert resp.status_code == 400
        assert 'name' in resp.get_json()['error'].lower()

    def test_valid_source_accepted(self, client):
        resp = client.post('/api/add_source', json={
            'name': 'good_src',
            'gps_commands': {'energy': '1 MeV', 'particle/type': 'e-'},
            'position': {'x': '0', 'y': '0', 'z': '0'}
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_negative_ion_z_rejected_on_create(self, client):
        """F-003: Ion Z must be >= 1 on source creation."""
        resp = client.post('/api/add_source', json={
            'name': 'bad_ion_src',
            'gps_commands': {'particle/type': 'ion'},
            'position': {'x': '0', 'y': '0', 'z': '0'},
            'rotation': {'x': '0', 'y': '0', 'z': '0'},
            'source_type': 'ion',
            'ion_params': {'Z': -1, 'A': 12, 'Q': 0}
        })
        assert resp.status_code == 400
        assert 'ion' in resp.get_json()['error'].lower() or 'z' in resp.get_json()['error'].lower()

    def test_zero_ion_z_rejected_on_create(self, client):
        """F-003: Ion Z must be >= 1 on source creation."""
        resp = client.post('/api/add_source', json={
            'name': 'zero_ion_src',
            'gps_commands': {'particle/type': 'ion'},
            'position': {'x': '0', 'y': '0', 'z': '0'},
            'rotation': {'x': '0', 'y': '0', 'z': '0'},
            'source_type': 'ion',
            'ion_params': {'Z': 0, 'A': 12, 'Q': 0}
        })
        assert resp.status_code == 400
        assert 'ion' in resp.get_json()['error'].lower() or 'z' in resp.get_json()['error'].lower()

    def test_negative_ion_a_rejected_on_create(self, client):
        """F-003: Ion A must be >= 1 on source creation."""
        resp = client.post('/api/add_source', json={
            'name': 'bad_a_ion_src',
            'gps_commands': {'particle/type': 'ion'},
            'position': {'x': '0', 'y': '0', 'z': '0'},
            'rotation': {'x': '0', 'y': '0', 'z': '0'},
            'source_type': 'ion',
            'ion_params': {'Z': 6, 'A': -1, 'Q': 0}
        })
        assert resp.status_code == 400
        assert 'ion' in resp.get_json()['error'].lower() or 'a' in resp.get_json()['error'].lower()

    def test_valid_ion_source_accepted(self, client):
        """F-003: Valid ion source should be accepted."""
        resp = client.post('/api/add_source', json={
            'name': 'good_ion_src',
            'gps_commands': {'particle/type': 'ion'},
            'position': {'x': '0', 'y': '0', 'z': '0'},
            'rotation': {'x': '0', 'y': '0', 'z': '0'},
            'source_type': 'ion',
            'ion_params': {'Z': 6, 'A': 12, 'Q': 0}
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_negative_ion_z_rejected_on_update(self, client, pm):
        """F-003: Ion Z must be >= 1 on source update."""
        pm.add_source('update_ion_src', {'particle/type': 'ion'}, {'x': '0', 'y': '0', 'z': '0'}, {'x': '0', 'y': '0', 'z': '0'}, source_type='ion', ion_params={'Z': 6, 'A': 12, 'Q': 0})
        source_id = list(pm.current_geometry_state.sources.values())[0].id
        resp = client.post('/api/update_source', json={
            'id': source_id,
            'ion_params': {'Z': -1, 'A': 12, 'Q': 0}
        })
        assert resp.status_code == 400
        assert 'ion' in resp.get_json()['error'].lower() or 'z' in resp.get_json()['error'].lower()

    def test_zero_ion_z_rejected_on_update(self, client, pm):
        """F-003: Ion Z must be >= 1 on source update."""
        pm.add_source('update_ion_src2', {'particle/type': 'ion'}, {'x': '0', 'y': '0', 'z': '0'}, {'x': '0', 'y': '0', 'z': '0'}, source_type='ion', ion_params={'Z': 6, 'A': 12, 'Q': 0})
        source_id = list(pm.current_geometry_state.sources.values())[0].id
        resp = client.post('/api/update_source', json={
            'id': source_id,
            'ion_params': {'Z': 0, 'A': 12, 'Q': 0}
        })
        assert resp.status_code == 400
        assert 'ion' in resp.get_json()['error'].lower() or 'z' in resp.get_json()['error'].lower()

    def test_negative_ion_a_rejected_on_update(self, client, pm):
        """F-003: Ion A must be >= 1 on source update."""
        pm.add_source('update_ion_src3', {'particle/type': 'ion'}, {'x': '0', 'y': '0', 'z': '0'}, {'x': '0', 'y': '0', 'z': '0'}, source_type='ion', ion_params={'Z': 6, 'A': 12, 'Q': 0})
        source_id = list(pm.current_geometry_state.sources.values())[0].id
        resp = client.post('/api/update_source', json={
            'id': source_id,
            'ion_params': {'Z': 6, 'A': -1, 'Q': 0}
        })
        assert resp.status_code == 400
        assert 'ion' in resp.get_json()['error'].lower() or 'a' in resp.get_json()['error'].lower()

    def test_valid_ion_update_accepted(self, client, pm):
        """F-003: Valid ion update should be accepted."""
        pm.add_source('update_ion_src4', {'particle/type': 'ion'}, {'x': '0', 'y': '0', 'z': '0'}, {'x': '0', 'y': '0', 'z': '0'}, source_type='ion', ion_params={'Z': 6, 'A': 12, 'Q': 0})
        source_id = list(pm.current_geometry_state.sources.values())[0].id
        resp = client.post('/api/update_source', json={
            'id': source_id,
            'ion_params': {'Z': 7, 'A': 14, 'Q': 1}
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_invalid_ion_update_does_not_apply_rename(self, client, pm):
        source, error_msg = pm.add_source(
            'atomic_update_source',
            {'particle/type': 'ion'},
            {'x': '0', 'y': '0', 'z': '0'},
            {'x': '0', 'y': '0', 'z': '0'},
            source_type='ion',
            ion_params={'Z': 6, 'A': 12, 'Q': 0},
        )
        assert error_msg is None

        resp = client.post('/api/update_source', json={
            'id': source['id'],
            'name': 'should_not_be_applied',
            'ion_params': {'Z': -1, 'A': 12, 'Q': 0},
        })

        assert resp.status_code == 400
        assert 'atomic_update_source' in pm.current_geometry_state.sources
        assert 'should_not_be_applied' not in pm.current_geometry_state.sources


# --- F-033: Solid validation ---

class TestSolidValidation:
    """F-033: Solids must reject invalid dimensions and types."""

    def test_invalid_type_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_box',
            'type': 'pyramid',
            'params': {'x': '1', 'y': '1', 'z': '1'}
        })
        assert resp.status_code == 400
        assert 'type' in resp.get_json()['error'].lower()

    def test_negative_box_dimension_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_box',
            'type': 'box',
            'params': {'x': '-1', 'y': '1', 'z': '1'}
        })
        assert resp.status_code == 400
        assert 'x' in resp.get_json()['error'].lower()

    def test_zero_box_dimension_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_box',
            'type': 'box',
            'params': {'x': '0', 'y': '1', 'z': '1'}
        })
        assert resp.status_code == 400

    def test_negative_tube_rmin_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_tube',
            'type': 'tube',
            'params': {'rmin': '-1', 'rmax': '5', 'dz': '10', 'startphi': '0', 'deltaphi': '360'}
        })
        assert resp.status_code == 400
        assert 'rmin' in resp.get_json()['error'].lower()

    def test_rmin_gt_rmax_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_tube',
            'type': 'tube',
            'params': {'rmin': '10', 'rmax': '5', 'dz': '10', 'startphi': '0', 'deltaphi': '360'}
        })
        assert resp.status_code == 400
        assert 'rmin' in resp.get_json()['error'].lower() and 'rmax' in resp.get_json()['error'].lower()

    def test_zero_tube_rmax_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_tube',
            'type': 'tube',
            'params': {'rmin': '0', 'rmax': '0', 'dz': '10', 'startphi': '0', 'deltaphi': '360'}
        })
        assert resp.status_code == 400

    def test_zero_deltaphi_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_tube',
            'type': 'tube',
            'params': {'rmin': '0', 'rmax': '5', 'dz': '10', 'startphi': '0', 'deltaphi': '0'}
        })
        assert resp.status_code == 400

    def test_negative_sphere_rmin_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_sphere',
            'type': 'sphere',
            'params': {'rmin': '-1', 'rmax': '5', 'startphi': '0', 'deltaphi': '360', 'starttheta': '0', 'deltatheta': '180'}
        })
        assert resp.status_code == 400

    def test_rmin_gt_rmax_sphere_rejected(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'bad_sphere',
            'type': 'sphere',
            'params': {'rmin': '10', 'rmax': '5', 'startphi': '0', 'deltaphi': '360', 'starttheta': '0', 'deltatheta': '180'}
        })
        assert resp.status_code == 400

    def test_valid_box_accepted(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'good_box',
            'type': 'box',
            'params': {'x': '10', 'y': '10', 'z': '10'}
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_valid_tube_accepted(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'good_tube',
            'type': 'tube',
            'params': {'rmin': '0', 'rmax': '5', 'dz': '10', 'startphi': '0', 'deltaphi': '360'}
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_ui_tube_z_parameter_accepted(self, client):
        resp = client.post('/add_primitive_solid', json={
            'name': 'ui_tube',
            'type': 'tube',
            'params': {
                'rmin': '0',
                'rmax': '5',
                'z': '10',
                'startphi': '0',
                'deltaphi': '2*pi',
            },
        })
        assert resp.status_code == 200

    def test_ui_trd_half_length_parameters_are_normalized(self, client, pm):
        resp = client.post('/add_primitive_solid', json={
            'name': 'ui_trd',
            'type': 'trd',
            'params': {
                'dx1': '5',
                'dx2': '6',
                'dy1': '7',
                'dy2': '8',
                'dz': '9',
            },
        })
        assert resp.status_code == 200
        solid = pm.current_geometry_state.solids['ui_trd']
        assert solid.raw_parameters == {
            'x1': '2*(5)',
            'x2': '2*(6)',
            'y1': '2*(7)',
            'y2': '2*(8)',
            'z': '2*(9)',
        }


# --- F-034: Placement validation ---

class TestPlacementValidation:
    """F-034: Placements must reject invalid scale and use user-provided position/scale."""

    def _setup_placement(self, pm):
        """Create world solid, LV, and material for placement tests."""
        pm.add_material('test_mat', {'density_expr': '1 g/cm3', 'Z_expr': '13', 'A_expr': '27'})
        pm.add_solid('world_s', 'box', {'x': '100', 'y': '100', 'z': '100'})
        pm.add_logical_volume('world_lv', 'world_s', 'test_mat')
        pm.add_solid('child_s', 'box', {'x': '10', 'y': '10', 'z': '10'})
        pm.add_logical_volume('child_lv', 'child_s', 'test_mat')

    def test_negative_scale_rejected(self, client, pm):
        self._setup_placement(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'placed_s', 'type': 'box', 'params': {'x': '5', 'y': '5', 'z': '5'}},
            'lv_params': {'name': 'placed_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'placed_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '0', 'y': '0', 'z': '0'},
                'scale': {'x': '-1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 400
        assert 'scale' in resp.get_json()['error'].lower()

    def test_zero_scale_rejected(self, client, pm):
        self._setup_placement(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'placed_s', 'type': 'box', 'params': {'x': '5', 'y': '5', 'z': '5'}},
            'lv_params': {'name': 'placed_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'placed_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '0', 'y': '0', 'z': '0'},
                'scale': {'x': '0', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 400

    def test_position_is_used(self, client, pm):
        """F-034: User-provided position must be used, not hardcoded (0,0,0)."""
        self._setup_placement(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'placed_s', 'type': 'box', 'params': {'x': '5', 'y': '5', 'z': '5'}},
            'lv_params': {'name': 'placed_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'placed_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '50', 'y': '30', 'z': '-20'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        # Verify the placement was created at the specified position
        state = pm.current_geometry_state
        world_lv = state.logical_volumes.get('world_lv')
        assert world_lv is not None
        # Find the placed PV
        placed_pv = None
        for pv in world_lv.content:
            if pv.name.startswith('placed_pv'):
                placed_pv = pv
                break
        assert placed_pv is not None
        pos = placed_pv._evaluated_position
        assert abs(pos.get('x', 0) - 50.0) < 0.01
        assert abs(pos.get('y', 0) - 30.0) < 0.01
        assert abs(pos.get('z', 0) - (-20.0)) < 0.01

    def test_scale_is_used(self, client, pm):
        """F-034: User-provided scale must be used, not hardcoded (1,1,1)."""
        self._setup_placement(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'placed_s', 'type': 'box', 'params': {'x': '5', 'y': '5', 'z': '5'}},
            'lv_params': {'name': 'placed_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'placed_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '0', 'y': '0', 'z': '0'},
                'scale': {'x': '2', 'y': '3', 'z': '0.5'}
            }
        })
        assert resp.status_code == 200
        state = pm.current_geometry_state
        world_lv = state.logical_volumes.get('world_lv')
        placed_pv = None
        for pv in world_lv.content:
            if pv.name.startswith('placed_pv'):
                placed_pv = pv
                break
        assert placed_pv is not None
        scale = placed_pv._evaluated_scale
        assert abs(scale.get('x', 1) - 2.0) < 0.01
        assert abs(scale.get('y', 1) - 3.0) < 0.01
        assert abs(scale.get('z', 1) - 0.5) < 0.01

    def test_valid_placement_accepted(self, client, pm):
        self._setup_placement(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'placed_s', 'type': 'box', 'params': {'x': '5', 'y': '5', 'z': '5'}},
            'lv_params': {'name': 'placed_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'placed_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '0', 'y': '0', 'z': '0'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True


# --- F-007: Mother-daughter containment checks ---

class TestMotherDaughterContainment:
    """F-007: Preflight must detect daughter volumes outside mother solid."""

    def _setup_world(self, pm):
        """Create a small world for containment tests."""
        pm.add_material('test_mat', {'density_expr': '1 g/cm3', 'Z_expr': '13', 'A_expr': '27'})
        pm.add_solid('world_s', 'box', {'x': '10', 'y': '10', 'z': '10'})
        pm.add_logical_volume('world_lv', 'world_s', 'test_mat')
        pm.current_geometry_state.world_volume_ref = 'world_lv'

    def test_daughter_entirely_outside_blocks_simulation(self, client, pm):
        """Daughter PV far outside mother solid → preflight error, can_run=False."""
        self._setup_world(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'child_s', 'type': 'box', 'params': {'x': '1', 'y': '1', 'z': '1'}},
            'lv_params': {'name': 'child_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'child_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '999999', 'y': '0', 'z': '0'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        report = pm.run_preflight_checks()
        assert report['summary']['can_run'] is False
        codes = [issue['code'] for issue in report['issues']]
        assert 'daughter_entirely_outside_mother' in codes

    def test_daughter_inside_mother_passes(self, client, pm):
        """Daughter PV fully inside mother solid → no containment issue."""
        self._setup_world(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'child_s', 'type': 'box', 'params': {'x': '2', 'y': '2', 'z': '2'}},
            'lv_params': {'name': 'child_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'child_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '0', 'y': '0', 'z': '0'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        report = pm.run_preflight_checks()
        codes = [issue['code'] for issue in report['issues']]
        assert 'daughter_entirely_outside_mother' not in codes
        assert 'daughter_extends_outside_mother' not in codes

    def test_daughter_partially_outside_warns(self, client, pm):
        """Daughter PV extends beyond mother solid → preflight warning."""
        self._setup_world(pm)
        # 8mm box at (6, 0, 0) → extends from 2 to 10 in +X, but -X goes to -2 (outside -5..+5)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'child_s', 'type': 'box', 'params': {'x': '8', 'y': '2', 'z': '2'}},
            'lv_params': {'name': 'child_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'child_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '6', 'y': '0', 'z': '0'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        report = pm.run_preflight_checks()
        codes = [issue['code'] for issue in report['issues']]
        assert 'daughter_extends_outside_mother' in codes
        # Warning should not block simulation
        assert report['summary']['can_run'] is True

    def test_daughter_outside_prevents_simulation_run(self, client, pm):
        """Simulation route rejects when daughter is outside mother."""
        self._setup_world(pm)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'child_s', 'type': 'box', 'params': {'x': '1', 'y': '1', 'z': '1'}},
            'lv_params': {'name': 'child_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'child_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '999999', 'y': '0', 'z': '0'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        resp = client.post('/api/simulation/run', json={
            'numberOfEvents': 10,
            'physicsList': 'FTFP_BERT'
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'preflight' in data['error'].lower()

    def test_nested_placement_outside_grandparent(self, client, pm):
        """Deeply nested PV outside ultimate mother is caught at its immediate parent level."""
        self._setup_world(pm)
        # Intermediate LV: 4mm box, placed at origin
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'inter_s', 'type': 'box', 'params': {'x': '4', 'y': '4', 'z': '4'}},
            'lv_params': {'name': 'inter_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'inter_pv',
                'parent_lv_name': 'world_lv',
                'position': {'x': '0', 'y': '0', 'z': '0'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        # Child placed far outside the intermediate LV (4mm box)
        resp = client.post('/add_solid_and_place', json={
            'solid_params': {'name': 'deep_s', 'type': 'box', 'params': {'x': '1', 'y': '1', 'z': '1'}},
            'lv_params': {'name': 'deep_lv', 'material_ref': 'test_mat'},
            'pv_params': {
                'name': 'deep_pv',
                'parent_lv_name': 'inter_lv',
                'position': {'x': '999', 'y': '0', 'z': '0'},
                'scale': {'x': '1', 'y': '1', 'z': '1'}
            }
        })
        assert resp.status_code == 200
        report = pm.run_preflight_checks()
        codes = [issue['code'] for issue in report['issues']]
        assert 'daughter_entirely_outside_mother' in codes
