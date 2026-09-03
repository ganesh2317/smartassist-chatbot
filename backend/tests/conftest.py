import os
from pathlib import Path

TEST_DB = Path('/tmp/smartassist_test.db')
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ['APP_ENV'] = 'test'
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB}'
os.environ['SECRET_KEY'] = 'test-secret-key-that-is-long-enough-for-tests-only'
os.environ['AI_API_KEY'] = ''
os.environ['CORS_ORIGINS'] = 'http://localhost:5173'
os.environ['AUTH_RATE_LIMIT_PER_MINUTE'] = '1000'
os.environ['CHAT_RATE_LIMIT_PER_MINUTE'] = '1000'
os.environ['UPLOAD_RATE_LIMIT_PER_MINUTE'] = '1000'
os.environ['MAX_DOCUMENTS_PER_USER'] = '50'

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    response = client.post('/auth/register', json={'username': 'alice', 'password': 'password123'})
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}
