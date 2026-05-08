import io
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app import (
    app,
    _build_gemini_sdk_history,
    _build_local_adapter_message_history,
    _get_ai_artifact_store_for_session,
)
from src.expression_evaluator import ExpressionEvaluator
from src.project_manager import ProjectManager


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def _build_project_manager(tmp_path: Path) -> ProjectManager:
    pm = ProjectManager(ExpressionEvaluator())
    pm.create_empty_project()
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    pm.projects_dir = str(projects_dir)
    return pm


def test_ai_artifact_upload_and_metadata_listing_flow(client, tmp_path):
    pm = _build_project_manager(tmp_path)

    source_path = tmp_path / "incoming" / "detector_input.pdf"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"%PDF-1.7\n%detector\n")

    with patch('app.get_project_manager_for_session', return_value=pm):
        upload_response = client.post(
            '/api/ai/artifacts/upload',
            data={
                'artifact': (io.BytesIO(b'%PDF-1.7\n1 0 obj\n<<>>\nendobj\n'), 'detector_sketch.pdf'),
                'source_path': str(source_path),
                'source_label': 'user-dropbox',
            },
            content_type='multipart/form-data',
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.get_json()
        assert upload_data['success'] is True
        artifact = upload_data['artifact']
        artifact_id = artifact['artifact_id']

        assert artifact['mime_type'] == 'application/pdf'
        assert artifact['size_bytes'] > 0
        assert artifact['source_path_input'] == str(source_path)
        assert artifact['source_path_exists'] is True
        assert artifact['source_path_is_file'] is True
        assert artifact['created_at'].endswith('Z')

        blob_path = (
            Path(pm.projects_dir)
            / '.airpet_ai_artifacts'
            / 'blobs'
            / artifact['stored_filename']
        )
        assert blob_path.is_file()

        list_response = client.post('/api/ai/artifacts/list', json={'limit': 10})
        assert list_response.status_code == 200
        list_data = list_response.get_json()
        assert list_data['success'] is True
        assert list_data['count'] == 1
        assert list_data['artifacts'][0]['artifact_id'] == artifact_id

        metadata_response = client.get(f'/api/ai/artifacts/{artifact_id}')
        assert metadata_response.status_code == 200
        metadata_data = metadata_response.get_json()
        assert metadata_data['success'] is True
        assert metadata_data['artifact']['artifact_id'] == artifact_id


def test_ai_artifact_listing_is_deterministic_and_respects_limit(client, tmp_path):
    pm = _build_project_manager(tmp_path)

    with patch('app.get_project_manager_for_session', return_value=pm):
        first_upload = client.post(
            '/api/ai/artifacts/upload',
            data={
                'artifact': (io.BytesIO(b'\x89PNG\r\n\x1a\nfirst'), 'first.png'),
            },
            content_type='multipart/form-data',
        )
        assert first_upload.status_code == 200
        first_id = first_upload.get_json()['artifact']['artifact_id']

        time.sleep(0.002)

        second_upload = client.post(
            '/api/ai/artifacts/upload',
            data={
                'artifact': (io.BytesIO(b'\x89PNG\r\n\x1a\nsecond'), 'second.png'),
            },
            content_type='multipart/form-data',
        )
        assert second_upload.status_code == 200
        second_id = second_upload.get_json()['artifact']['artifact_id']

        list_response = client.post('/api/ai/artifacts/list', json={'limit': 1})
        assert list_response.status_code == 200
        list_data = list_response.get_json()
        assert list_data['success'] is True
        assert list_data['count'] == 1
        assert [item['artifact_id'] for item in list_data['artifacts']] == [second_id]

        full_list_response = client.post('/api/ai/artifacts/list', json={'limit': 10})
        assert full_list_response.status_code == 200
        full_ids = [item['artifact_id'] for item in full_list_response.get_json()['artifacts']]
        assert full_ids == [second_id, first_id]


def test_ai_artifact_upload_rejects_unsupported_file_types(client, tmp_path):
    pm = _build_project_manager(tmp_path)

    with patch('app.get_project_manager_for_session', return_value=pm):
        response = client.post(
            '/api/ai/artifacts/upload',
            data={
                'artifact': (io.BytesIO(b'not a supported file'), 'notes.txt'),
            },
            content_type='multipart/form-data',
        )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert 'Unsupported artifact type' in payload['error']


def test_ai_chat_rejects_attachment_when_selected_local_backend_lacks_vision(client, tmp_path):
    pm = _build_project_manager(tmp_path)

    with patch('app.get_project_manager_for_session', return_value=pm):
        upload_response = client.post(
            '/api/ai/artifacts/upload',
            data={
                'artifact': (io.BytesIO(b'\x89PNG\r\n\x1a\nimage'), 'detector.png'),
            },
            content_type='multipart/form-data',
        )
        assert upload_response.status_code == 200
        artifact_id = upload_response.get_json()['artifact']['artifact_id']

        response = client.post('/api/ai/chat', json={
            'message': 'Build this detector.',
            'model': 'llama_cpp::local-vision-disabled',
            'attachment_ids': [artifact_id],
        })

    assert response.status_code == 400
    payload = response.get_json()
    assert payload['success'] is False
    assert 'vision' in payload['error']


def test_chat_history_builders_attach_image_parts_from_artifact_metadata(tmp_path):
    pm = _build_project_manager(tmp_path)
    store = _get_ai_artifact_store_for_session(pm)

    class _Upload:
        filename = 'detector.png'
        mimetype = 'image/png'

        def read(self):
            return b'\x89PNG\r\n\x1a\nimage'

    artifact = store.ingest_upload(_Upload())
    chat_history = [
        {
            'role': 'user',
            'content': 'Build this detector.',
            'metadata': {
                'ai_attachments': [
                    {
                        'artifact_id': artifact['artifact_id'],
                        'mime_type': artifact['mime_type'],
                        'original_filename': artifact['original_filename'],
                        'sha256': artifact['sha256'],
                        'size_bytes': artifact['size_bytes'],
                    }
                ]
            },
        }
    ]

    local_messages = _build_local_adapter_message_history(chat_history, store)
    openai_message = local_messages[0].as_openai_message()
    assert openai_message['content'][0] == {'type': 'text', 'text': 'Build this detector.'}
    assert openai_message['content'][1]['type'] == 'image_url'
    assert openai_message['content'][1]['image_url']['url'].startswith('data:image/png;base64,')

    gemini_history = _build_gemini_sdk_history(chat_history, store)
    assert gemini_history[0]['role'] == 'user'
    assert len(gemini_history[0]['parts']) == 2
    assert gemini_history[0]['parts'][0] == {'text': 'Build this detector.'}
    assert getattr(gemini_history[0]['parts'][1], 'inline_data', None) is not None
