import pytest
import json
from unittest.mock import patch
from app import app, limiter
from nlp_engine import NLPEngine

@pytest.fixture
def client():
    # Setup testing configurations
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["RATELIMIT_ENABLED"] = False # Disable by default for tests
    with app.test_client() as client:
        yield client

# --- NLP Engine Tests ---
def test_nlp_engine_loading():
    nlp = NLPEngine("event_data.json")
    data_dict = nlp.get_raw_data_dict()
    assert "halls" in data_dict
    
    bad_nlp = NLPEngine("does_not_exist.json")
    bad_data = bad_nlp.get_raw_data_dict()
    assert bad_data["halls"] == {}

def test_nlp_intent_hall():
    nlp = NLPEngine("event_data.json")
    assert "Hall A" in nlp.handle_basic_intent("where is hall a?")
    assert "We have Halls" in nlp.handle_basic_intent("where is hall x?")

def test_nlp_intent_facilities():
    nlp = NLPEngine("event_data.json")
    assert "Help Desk:" in nlp.handle_basic_intent("where is help desk")

def test_nlp_intent_recommendation():
    nlp = NLPEngine("event_data.json")
    assert "I recommend:" in nlp.handle_basic_intent("recommend an ai session")
    # "sports" is not a predefined interest, so it prompts the user
    assert "What are you interested in" in nlp.handle_basic_intent("recommend a sports session")

def test_nlp_intent_unmatched():
    nlp = NLPEngine("event_data.json")
    assert nlp.handle_basic_intent("tell me a joke") is None

# --- API Endpoint Tests ---
def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200

def test_info_api(client):
    response = client.get("/api/info")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "csrf_token" in data

def test_chat_success(client):
    response = client.post("/chat", json={"message": "where is hall a?"})
    assert response.status_code == 200

def test_chat_missing_message(client):
    response = client.post("/chat", json={})
    assert response.status_code == 400

def test_chat_unmatched_fallback(client):
    response = client.post("/chat", json={"message": "how do I cook a turkey?"})
    assert response.status_code == 200

# --- Security & Architecture Tests ---
def test_security_headers(client):
    response = client.get("/")
    assert response.headers.get("X-Frame-Options") == "DENY"

def test_csrf_protection():
    app.config["WTF_CSRF_ENABLED"] = True
    with app.test_client() as client:
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 400

def test_rate_limiting(client):
    """Explicitly test Rate Limiting."""
    app.config["RATELIMIT_ENABLED"] = True
    for i in range(21):
        response = client.post("/chat", json={"message": "test"})
    assert response.status_code == 429
    app.config["RATELIMIT_ENABLED"] = False


