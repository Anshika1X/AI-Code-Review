import sys
from pathlib import Path
import pytest

# Ensure backend directory is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app import create_app
from config import TestConfig
from models import db, User


@pytest.fixture
def app():
    """Create and configure a fresh Flask app instance for testing."""
    app_instance = create_app(TestConfig)

    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Helper fixture to register a test user and obtain auth headers."""
    register_payload = {
        'name': 'Test Engineer',
        'email': 'engineer@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }
    res = client.post('/api/register', json=register_payload)
    data = res.get_json()
    token = data['token']
    return {'Authorization': f'Bearer {token}'}
