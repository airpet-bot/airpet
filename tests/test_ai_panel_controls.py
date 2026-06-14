from app import app


def test_ai_panel_keeps_model_visible_and_exposes_run_controls():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    primary_controls = html.split('<div class="ai-primary-controls">', 1)[1].split(
        '<div id="ai_attachment_tray"',
        1,
    )[0]
    advanced_controls = primary_controls.split(
        '<details id="ai_advanced_settings"',
        1,
    )[1]

    assert 'id="ai_model_select"' in primary_controls
    assert 'id="ai_model_select"' not in advanced_controls
    assert '<option value="interactive" selected>Interactive</option>' in primary_controls
    assert '<option value="build_validate">Build &amp; Validate</option>' in primary_controls
    assert 'value="design_only"' not in primary_controls
    assert 'value="full_study"' not in primary_controls
    assert 'id="ai_turn_policy"' in advanced_controls
    assert '<option value="automatic" selected>Until complete</option>' in advanced_controls
    assert 'id="ai_turn_limit" value="100" min="1" max="500"' in advanced_controls
    assert 'id="ai_runtime_config_btn"' in advanced_controls
    assert 'id="ai_stop_button"' in html
