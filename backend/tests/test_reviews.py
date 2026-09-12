import pytest


SAMPLE_PYTHON_CODE = """
def get_user_data(user_id):
    api_key = "AIzaSyD-fake-secret-key-12345"
    query = "SELECT * FROM users WHERE id = " + user_id
    try:
        cursor.execute(query)
    except:
        print("Error occurred")
    return None
"""

SAMPLE_JS_SQL_INJECTION = """function getUser(username) {
    const query = "SELECT * FROM users WHERE name = '" + username + "'";
    console.log(query);
    return query;
}

getUser("admin");"""


def test_create_review_unauthorized(client):
    """Submitting a review without authentication must return 401."""
    res = client.post('/api/reviews', json={
        'language': 'Python',
        'code': 'print("hello")'
    })
    assert res.status_code == 401


def test_create_review_empty_code(client, auth_headers):
    """Submitting empty code must return 400."""
    res = client.post('/api/reviews', json={
        'language': 'Python',
        'code': '   '
    }, headers=auth_headers)
    assert res.status_code == 400
    assert 'enter some code' in res.get_json()['error'].lower()


def test_create_review_success(client, auth_headers):
    """Submitting valid code must return 201 and structured review with issues."""
    res = client.post('/api/reviews', json={
        'language': 'Python',
        'code': SAMPLE_PYTHON_CODE
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    review = data['review']
    assert review['language'] == 'Python'
    assert 'score' in review
    assert isinstance(review['score'], int)
    assert 0 <= review['score'] <= 100
    assert 'summary' in review
    assert len(review['issues']) > 0


def test_create_review_javascript_sql_injection_end_to_end(client, auth_headers):
    """
    End-to-end API test:
    Verify submitting the user's JavaScript SQL injection code via POST /api/reviews
    stores and returns findings for SQL injection (Security) and console.log (Code Quality).
    """
    res = client.post('/api/reviews', json={
        'language': 'JavaScript',
        'code': SAMPLE_JS_SQL_INJECTION
    }, headers=auth_headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    review = data['review']
    assert review['language'] == 'JavaScript'
    assert review['score'] < 80

    issues = review['issues']
    # Check SQL Injection finding
    sql_findings = [i for i in issues if 'sql injection' in i['message'].lower()]
    assert len(sql_findings) >= 1, "SQL Injection issue was not detected in POST /api/reviews response"
    assert sql_findings[0]['category'] == 'Security'
    assert sql_findings[0]['severity'] in ['Critical', 'High']
    assert sql_findings[0]['line_number'] == 2

    # Check Console.log finding
    log_findings = [i for i in issues if 'logging' in i['message'].lower()]
    assert len(log_findings) >= 1, "Console.log issue was not detected in POST /api/reviews response"
    assert log_findings[0]['category'] == 'Code Quality'
    assert log_findings[0]['line_number'] == 3

    # Check persistence: retrieve via GET /api/reviews/:id
    get_res = client.get(f'/api/reviews/{review["id"]}', headers=auth_headers)
    assert get_res.status_code == 200
    fetched = get_res.get_json()['review']
    assert len(fetched['issues']) >= 2


def test_get_reviews_history(client, auth_headers):
    """Fetching reviews list must return authenticated user's history."""
    # Create two reviews
    client.post('/api/reviews', json={'language': 'Python', 'code': 'x = 1'}, headers=auth_headers)
    client.post('/api/reviews', json={'language': 'JavaScript', 'code': 'let x = 1;'}, headers=auth_headers)

    res = client.get('/api/reviews', headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['count'] >= 2
    assert len(data['reviews']) >= 2


def test_get_single_review_and_isolation(client, auth_headers):
    """Testing single review retrieval and cross-user isolation."""
    # Create review for User 1
    create_res = client.post('/api/reviews', json={
        'language': 'Python',
        'code': 'def add(a, b): return a + b'
    }, headers=auth_headers)
    review_id = create_res.get_json()['review']['id']

    # User 1 can fetch their review
    get_res = client.get(f'/api/reviews/{review_id}', headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.get_json()['review']['id'] == review_id

    # Create User 2
    client.post('/api/register', json={
        'name': 'User Two',
        'email': 'user2@example.com',
        'password': 'password123'
    })
    login_res = client.post('/api/login', json={
        'email': 'user2@example.com',
        'password': 'password123'
    })
    token_user2 = login_res.get_json()['token']
    headers_user2 = {'Authorization': f'Bearer {token_user2}'}

    # User 2 attempting to view User 1's review must receive 404 (isolation)
    forbidden_res = client.get(f'/api/reviews/{review_id}', headers=headers_user2)
    assert forbidden_res.status_code == 404


def test_delete_review(client, auth_headers):
    """Deleting a review removes it from the database."""
    create_res = client.post('/api/reviews', json={
        'language': 'Python',
        'code': 'val = 42'
    }, headers=auth_headers)
    review_id = create_res.get_json()['review']['id']

    # Delete
    del_res = client.delete(f'/api/reviews/{review_id}', headers=auth_headers)
    assert del_res.status_code == 200

    # Ensure it no longer exists
    get_res = client.get(f'/api/reviews/{review_id}', headers=auth_headers)
    assert get_res.status_code == 404


def test_dashboard_metrics(client, auth_headers):
    """Dashboard endpoint must return aggregate statistics."""
    client.post('/api/reviews', json={
        'language': 'Python',
        'code': SAMPLE_PYTHON_CODE
    }, headers=auth_headers)

    res = client.get('/api/dashboard', headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['stats']['total_reviews'] >= 1
    assert data['stats']['average_score'] > 0
    assert 'score_trend' in data
    assert 'category_distribution' in data
    assert len(data['recent_reviews']) >= 1
