import io
import json
from unittest.mock import patch

from app import app
from src.expression_evaluator import ExpressionEvaluator
from src.project_manager import ProjectManager


def _make_pm():
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()
    return pm


def test_import_step_route_surfaces_warning_when_file_produces_zero_solids():
    """Regression: an empty / non-STEP file should not be reported as a clean success."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        pm = _make_pm()
        with patch('app.get_project_manager_for_session', return_value=pm):
            data = {
                'stepFile': (io.BytesIO(b'definitely not a STEP file'), 'broken.step'),
                'options': json.dumps({
                    'groupingName': 'ST5_empty_warn',
                    'placementMode': 'assembly',
                    'parentLVName': 'World',
                    'offset': {'x': '0', 'y': '0', 'z': '0'},
                    'smartImport': False,
                }),
            }
            resp = client.post('/import_step_with_options', data=data, content_type='multipart/form-data')

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload['success'] is True
        assert 'did not produce any solids' in payload['message']
        assert 'step_import_report' in payload


def test_import_step_route_surfaces_warning_for_zero_byte_file():
    """Regression: an empty file should produce the same warning as a malformed one."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        pm = _make_pm()
        with patch('app.get_project_manager_for_session', return_value=pm):
            data = {
                'stepFile': (io.BytesIO(b''), 'empty.step'),
                'options': json.dumps({
                    'groupingName': 'ST5_zero',
                    'placementMode': 'assembly',
                    'parentLVName': 'World',
                    'offset': {'x': '0', 'y': '0', 'z': '0'},
                    'smartImport': False,
                }),
            }
            resp = client.post('/import_step_with_options', data=data, content_type='multipart/form-data')

        payload = resp.get_json()
        assert resp.status_code == 200
        assert payload['success'] is True
        assert 'did not produce any solids' in payload['message']

def test_import_step_route_returns_smart_import_report_payload():
    app.config['TESTING'] = True
    with app.test_client() as client:
        pm = _make_pm()

        fake_report = {
            'enabled': True,
            'candidates': [
                {
                    'source_id': 'fixture_1',
                    'classification': 'box',
                    'confidence': 0.95,
                    'params': {'x': 1, 'y': 2, 'z': 3},
                    'fallback_reason': None,
                    'selected_mode': 'primitive',
                },
                {
                    'source_id': 'fixture_2',
                    'classification': 'tessellated',
                    'confidence': 0.0,
                    'params': {},
                    'fallback_reason': 'no_primitive_match_v1',
                    'selected_mode': 'tessellated',
                },
            ],
            'summary': {
                'total': 2,
                'primitive_count': 1,
                'tessellated_count': 1,
                'primitive_ratio': 0.5,
                'selected_mode_counts': {'primitive': 1, 'tessellated': 1},
                'selected_primitive_ratio': 0.5,
                'counts_by_classification': {
                    'box': 1,
                    'cylinder': 0,
                    'sphere': 0,
                    'cone': 0,
                    'torus': 0,
                    'tessellated': 1,
                },
            },
        }

        with patch('app.get_project_manager_for_session', return_value=pm), \
             patch.object(pm, 'import_step_with_options', return_value=(True, None, fake_report)):
            data = {
                'stepFile': (io.BytesIO(b'STEP-DATA'), 'fixture.step'),
                'options': json.dumps({
                    'groupingName': 'fixture_import',
                    'placementMode': 'assembly',
                    'parentLVName': 'World',
                    'offset': {'x': '0', 'y': '0', 'z': '0'},
                    'smartImport': True,
                }),
            }
            resp = client.post('/import_step_with_options', data=data, content_type='multipart/form-data')

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload['success'] is True
        assert 'step_import_report' in payload
        assert payload['step_import_report']['summary']['selected_mode_counts']['primitive'] == 1
        assert payload['step_import_report']['candidates'][1]['fallback_reason'] == 'no_primitive_match_v1'


def test_zero_solid_fresh_import_rolls_back_state_and_leaves_no_orphan_cad_import():
    """Regression for F-015: a fresh STEP import that produces zero solids must
    not leave an orphan cad_import card behind. The pre-merge state should be
    restored so solids/groups/assemblies/cad_imports counts return to baseline."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        pm = _make_pm()
        baseline = pm.current_geometry_state
        baseline_solids = len(baseline.solids)
        baseline_assemblies = len(baseline.assemblies)
        baseline_groups_total = sum(len(v) for v in baseline.ui_groups.values())
        baseline_dfgs = len(baseline.detector_feature_generators)

        with patch('app.get_project_manager_for_session', return_value=pm):
            data = {
                'stepFile': (io.BytesIO(b'not-a-step-file'), 'broken.step'),
                'options': json.dumps({
                    'groupingName': 'ST5_orphan_rollback',
                    'placementMode': 'assembly',
                    'parentLVName': 'World',
                    'offset': {'x': '0', 'y': '0', 'z': '0'},
                    'smartImport': False,
                }),
            }
            resp = client.post('/import_step_with_options', data=data, content_type='multipart/form-data')

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload['success'] is True
        assert 'did not produce any solids' in payload['message']

        state = pm.current_geometry_state
        assert len(state.cad_imports) == 0, (
            f"Expected zero cad_imports after rollback, got {len(state.cad_imports)}: "
            f"{[c.source.filename for c in state.cad_imports]}"
        )
        assert len(state.solids) == baseline_solids, (
            f"Solids drift after rollback: baseline={baseline_solids}, now={len(state.solids)}"
        )
        assert len(state.assemblies) == baseline_assemblies
        groups_total = sum(len(v) for v in state.ui_groups.values())
        assert groups_total == baseline_groups_total
        assert len(state.detector_feature_generators) == baseline_dfgs
