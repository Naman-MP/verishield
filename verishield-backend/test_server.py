from fastapi.testclient import TestClient

import server


client = TestClient(server.app)


def test_extract_text_ignores_page_chrome_and_injected_ui():
    html = """<article><nav>Navigation links must disappear</nav>
    <div class='veribar-root'>Injected score must disappear</div>
    <h1>A useful article about an actual event</h1>
    <p>This paragraph contains the information a reader came here to find.</p>
    <script>secret tracking code</script></article>"""
    text = server.extract_text_from_elements(html)
    assert "useful article" in text
    assert "reader came" in text
    assert "Navigation" not in text
    assert "Injected score" not in text
    assert "tracking" not in text


def test_short_text_is_not_scored():
    response = client.post("/verify", json={"html": "<p>Only a few words.</p>"})
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_text"
    assert response.json()["ai_probability"] is None


def test_score_uses_fake_class_probability(monkeypatch):
    monkeypatch.setattr(server, "_predict", lambda _text: (0.84, 0.84))
    html = "<p>" + "This is a complete sample sentence for a test. " * 6 + "</p>"
    response = client.post("/verify", json={"html": html})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "analyzed"
    assert data["ai_probability"] == 84.0
    assert data["method"] == "model"
    assert data["word_count"] >= 30


def test_model_failure_is_reported(monkeypatch):
    def fail(_text):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(server, "_predict", fail)
    html = "<p>" + "This is a complete sample sentence for a test. " * 6 + "</p>"
    response = client.post("/verify", json={"html": html})
    assert response.status_code == 503
    assert response.json()["detail"] == "Text model unavailable"
