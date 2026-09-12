import pytest


def test_register_success(client):
    """Test successful user registration."""
    response = client.post('/api/register', json={
        'name': 'Alice Developer',
        'email': 'alice@example.com',
        'password': 'securepassword123',
        'confirm_password': 'securepassword123'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert 'token' in data
    assert data['user']['email'] == 'alice@example.com'
    assert data['user']['name'] == 'Alice Developer'


def test_register_duplicate_email(client):
    """Test registering with an existing email returns 400."""
    payload = {
        'name': 'Bob Smith',
        'email': 'bob@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }
    res1 = client.post('/api/register', json=payload)
    assert res1.status_code == 201

    res2 = client.post('/api/register', json=payload)
    assert res2.status_code == 400
    data = res2.get_json()
    assert data['success'] is False
    assert 'already exists' in data['error'].lower()


def test_register_validation_errors(client):
    """Test missing fields, invalid email, and password mismatch."""
    # Missing name
    res = client.post('/api/register', json={'email': 'test@example.com', 'password': 'pass'})
    assert res.status_code == 400
    assert 'name is required' in res.get_json()['error'].lower()

    # Invalid email format
    res = client.post('/api/register', json={
        'name': 'Test',
        'email': 'not-an-email',
        'password': 'password123'
    })
    assert res.status_code == 400
    assert 'valid email' in res.get_json()['error'].lower()

    # Short password
    res = client.post('/api/register', json={
        'name': 'Test',
        'email': 'test@example.com',
        'password': '123'
    })
    assert res.status_code == 400
    assert 'at least 6' in res.get_json()['error'].lower()

    # Password mismatch
    res = client.post('/api/register', json={
        'name': 'Test',
        'email': 'test@example.com',
        'password': 'password123',
        'confirm_password': 'differentpassword'
    })
    assert res.status_code == 400
    assert 'do not match' in res.get_json()['error'].lower()


def test_login_success(client):
    """Test login with valid credentials returns 200 and token."""
    client.post('/api/register', json={
        'name': 'Carol Danvers',
        'email': 'carol@example.com',
        'password': 'mypassword123'
    })

    res = client.post('/api/login', json={
        'email': 'carol@example.com',
        'password': 'mypassword123'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'token' in data
    assert data['user']['email'] == 'carol@example.com'


def test_login_invalid_password(client):
    """Test login with incorrect password returns 401."""
    client.post('/api/register', json={
        'name': 'Dave',
        'email': 'dave@example.com',
        'password': 'correctpassword'
    })

    res = client.post('/api/login', json={
        'email': 'dave@example.com',
        'password': 'wrongpassword'
    })
    assert res.status_code == 401
    assert 'invalid email or password' in res.get_json()['error'].lower()


def test_get_current_user_profile(client, auth_headers):
    """Test accessing protected /api/me endpoint."""
    # Authorized
    res = client.get('/api/me', headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['user']['email'] == 'engineer@example.com'

    # Unauthorized
    unauth_res = client.get('/api/me')
    assert unauth_res.status_code == 401
