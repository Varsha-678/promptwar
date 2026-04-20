import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test that the index page loads correctly with semantic HTML structure."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Event Buddy AI" in response.data
    assert b"<main class=\"main-content\"" in response.data

def test_info_api(client):
    """Test that the /api/info endpoint returns correct JSON structure and headers."""
    response = client.get("/api/info")
    assert response.status_code == 200
    
    # Check Efficiency cache headers
    assert "Cache-Control" in response.headers
    assert "public, max-age=3600" in response.headers["Cache-Control"]

    data = json.loads(response.data)
    assert "sample_questions" in data
    assert "event_data" in data
    assert "halls" in data["event_data"]

def test_chat_hall_intent(client):
    """Test the local intent matching for finding a hall."""
    response = client.post("/chat", json={"message": "where is hall a?"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "Hall A" in data["reply"]
    assert "Main entrance" in data["reply"]

def test_chat_recommendation_intent(client):
    """Test the local intent matching for session recommendations."""
    response = client.post("/chat", json={"message": "recommend an ai session"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "The Future of AI" in data["reply"] or "Generative AI" in data["reply"]

def test_chat_missing_message(client):
    """Test error handling for bad input."""
    response = client.post("/chat", json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data

def test_chat_sanitization(client):
    """Test that inputs are handled safely (no crash on weird chars)."""
    response = client.post("/chat", json={"message": "<script>alert(1)</script>"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "reply" in data

def test_security_headers(client):
    """Test that security headers are applied to responses."""
    response = client.get("/")
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
