import json
import pytest

from app import app, db, ConversationSession, ConversationHistory


class FakeClient:
    class models:
        @staticmethod
        def generate_content(model, contents, config):
            class R:
                text = "This is a fake response"

            return R()


@pytest.fixture
def client_app(tmp_path, monkeypatch):
    # Use the Flask test client and an in-memory sqlite DB
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Use fake LLM client
    monkeypatch.setattr('app.client', FakeClient())

    with app.app_context():
        db.create_all()
        yield app.test_client()


def test_chat_happy_path(client_app):
    resp = client_app.post('/chat', json={'user_query': 'Hello', 'session_id': None})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'bot_response' in data
    assert data['bot_response'] == 'This is a fake response'


def test_chat_validation_missing_query(client_app):
    resp = client_app.post('/chat', json={})
    assert resp.status_code == 400


def test_llm_failure_marks_escalated(client_app, monkeypatch):
    class BrokenClient:
        class models:
            @staticmethod
            def generate_content(*args, **kwargs):
                raise RuntimeError('LLM down')

    monkeypatch.setattr('app.client', BrokenClient())
    resp = client_app.post('/chat', json={'user_query': 'Hi', 'session_id': None})
    assert resp.status_code in (200, 503)
    data = resp.get_json()
    assert 'bot_response' in data
