import pytest
from services.ai_service import (
    clean_json_response,
    validate_and_normalize_review,
    build_review_prompt,
    generate_static_analysis_fallback
)


def test_clean_json_response():
    """Ensure markdown code fence markers are safely removed."""
    raw = "```json\n{\"score\": 85, \"summary\": \"Good code\"}\n```"
    cleaned = clean_json_response(raw)
    assert cleaned.startswith('{')
    assert cleaned.endswith('}')


def test_validate_and_normalize_review_valid():
    """Verify normalizer accepts compliant review payload."""
    raw_payload = {
        'score': 92,
        'summary': 'Well-written module.',
        'issues': [
            {
                'category': 'Security',
                'severity': 'High',
                'line_number': 14,
                'message': 'Potential secret leak',
                'explanation': 'Token present.',
                'recommendation': 'Use env vars.',
                'suggested_code': 'token = os.getenv("TOKEN")'
            }
        ]
    }
    result = validate_and_normalize_review(raw_payload, "line 1\nline 2\n")
    assert result['score'] == 92
    assert result['summary'] == 'Well-written module.'
    assert len(result['issues']) == 1
    assert result['issues'][0]['category'] == 'Security'
    assert result['issues'][0]['severity'] == 'High'
    assert result['issues'][0]['line_number'] == 14


def test_validate_and_normalize_review_resilience():
    """Verify normalizer handles missing, out-of-bounds, or invalid types gracefully."""
    malformed_payload = {
        'score': 'invalid-number',
        'summary': '',
        'issues': [
            {
                'category': 'UnknownCategory',
                'severity': 'UnknownSeverity',
                'line_number': 'not-an-int'
            },
            "invalid-string-issue"
        ]
    }
    result = validate_and_normalize_review(malformed_payload, "def test(): pass")
    assert isinstance(result['score'], int)
    assert 0 <= result['score'] <= 100
    assert len(result['summary']) > 0
    assert len(result['issues']) == 1
    # Category fallback
    assert result['issues'][0]['category'] == 'Code Quality'
    # Severity fallback
    assert result['issues'][0]['severity'] == 'Medium'
    # Line number None when invalid
    assert result['issues'][0]['line_number'] is None


def test_static_analysis_detects_flaws():
    """Ensure rule-based fallback detects hardcoded secrets and bare excepts."""
    vulnerable_code = """
import os
db_password = "supersecretpassword123"

def query(val):
    sql = "SELECT * FROM items WHERE id = " + val
    try:
        pass
    except:
        pass
"""
    result = generate_static_analysis_fallback(vulnerable_code, 'Python')
    assert result['score'] < 80
    assert len(result['issues']) >= 2

    categories = [i['category'] for i in result['issues']]
    assert 'Security' in categories
    assert 'Bugs' in categories


def test_javascript_sql_injection_and_console_log():
    """
    Verify the user's exact JavaScript snippet:
    Detects both the potential SQL injection risk on line 2 (Security / High or Critical)
    and the production console.log statement on line 3 (Code Quality).
    """
    js_snippet = """function getUser(username) {
    const query = "SELECT * FROM users WHERE name = '" + username + "'";
    console.log(query);
    return query;
}

getUser("admin");"""

    result = generate_static_analysis_fallback(js_snippet, 'JavaScript')
    issues = result['issues']

    # Must detect findings
    assert len(issues) >= 2, f"Expected at least 2 findings, got {len(issues)}"

    # 1. Check SQL injection
    sql_issues = [i for i in issues if 'sql injection' in i['message'].lower()]
    assert len(sql_issues) >= 1, "SQL injection was not detected in JavaScript snippet!"
    sql_finding = sql_issues[0]
    assert sql_finding['category'] == 'Security'
    assert sql_finding['severity'] in ['High', 'Critical']
    assert sql_finding['line_number'] == 2
    assert 'parameterized' in sql_finding['recommendation'].lower()

    # 2. Check console.log
    log_issues = [i for i in issues if 'logging' in i['message'].lower()]
    assert len(log_issues) >= 1, "Console.log was not detected in JavaScript snippet!"
    log_finding = log_issues[0]
    assert log_finding['category'] == 'Code Quality'
    assert log_finding['line_number'] == 3

    # Overall score must reflect security penalty
    assert result['score'] < 80


def test_build_review_prompt_security_checklist():
    """Verify prompt constructor includes systematic security checklist."""
    prompt = build_review_prompt("const x = 42;", "JavaScript")
    assert "Programming Language: JavaScript" in prompt
    assert "MANDATORY SECURITY AUDIT CHECKLIST" in prompt
    assert "SQL & Data Storage Injections" in prompt
    assert "Command & Process Injections" in prompt
    assert "Hardcoded Secrets" in prompt
    assert "line_number" in prompt
    assert "SUGGESTED REFACTORING CODE RULES" in prompt


def test_suggested_refactoring_practical_code():
    """Verify suggested_code provides actual parameterized statements and contextual labeling."""
    # Test JavaScript snippet
    js_code = 'const q = "SELECT * FROM users WHERE name = \'" + user + "\'";'
    js_result = generate_static_analysis_fallback(js_code, 'JavaScript')
    js_sql_issue = next(i for i in js_result['issues'] if 'sql injection' in i['message'].lower())
    assert js_sql_issue['suggested_code'] is not None
    assert "$1" in js_sql_issue['suggested_code']
    assert "params" in js_sql_issue['suggested_code']
    assert "Contextual example" in js_sql_issue['suggested_code']

    # Test Python snippet
    py_code = 'query = f"SELECT * FROM accounts WHERE id = {acc_id}"'
    py_result = generate_static_analysis_fallback(py_code, 'Python')
    py_sql_issue = next(i for i in py_result['issues'] if 'sql injection' in i['message'].lower())
    assert py_sql_issue['suggested_code'] is not None
    assert "%s" in py_sql_issue['suggested_code']
    assert "cursor.execute" in py_sql_issue['suggested_code']
    assert "Contextual example" in py_sql_issue['suggested_code']


def test_sql_injection_severity_calibration():
    """
    Verify severity calibration:
    - HIGH by default when query is constructed without visible database execution call.
    - CRITICAL when direct database execution is visible.
    - Wording uses 'Potential SQL Injection Vulnerability' for unconfirmed execution.
    """
    # 1. Unconfirmed database execution: High severity + Potential wording
    unconfirmed_snippet = """
    function getUser(username) {
        const query = "SELECT * FROM users WHERE name = '" + username + "'";
        return query;
    }
    """
    res_unconfirmed = generate_static_analysis_fallback(unconfirmed_snippet, 'JavaScript')
    issue_unconfirmed = next(i for i in res_unconfirmed['issues'] if 'sql injection' in i['message'].lower())
    assert issue_unconfirmed['severity'] == 'High'
    assert 'potential' in issue_unconfirmed['message'].lower()

    # 2. Confirmed database execution: Critical severity
    confirmed_snippet = """
    function getUser(username) {
        const query = "SELECT * FROM users WHERE name = '" + username + "'";
        return db.query(query);
    }
    """
    res_confirmed = generate_static_analysis_fallback(confirmed_snippet, 'JavaScript')
    issue_confirmed = next(i for i in res_confirmed['issues'] if 'sql injection' in i['message'].lower())
    assert issue_confirmed['severity'] == 'Critical'
    assert 'sql injection vulnerability' in issue_confirmed['message'].lower()


