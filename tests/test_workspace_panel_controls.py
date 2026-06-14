from app import app


def test_workspace_exposes_collapsible_resizable_left_panel():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="left_panel_container"' in html
    assert 'id="left_panel_rail"' in html
    assert 'id="leftPanelResizeHandle"' in html
    assert 'role="separator"' in html
    assert 'aria-orientation="vertical"' in html
    assert 'id="toggleLeftPanelBtn"' in html
    assert 'aria-controls="left_panel_container"' in html
    assert 'id="restoreLeftPanelBtn"' in html
    assert 'class="panel-collapse-button"' in html
    assert 'aria-controls="bottom_panel_content"' in html
