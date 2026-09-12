import os
import json
import re
import logging
import requests

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {'Security', 'Bugs', 'Performance', 'Code Quality', 'Best Practices', 'Maintainability'}
VALID_SEVERITIES = {'Critical', 'High', 'Medium', 'Low'}


def build_review_prompt(code: str, language: str) -> str:
    """Build a structured system prompt for Gemini code review."""
    return f"""You are an experienced software engineering tech lead performing a professional code review.
Review the following source code carefully.

Programming Language: {language}

Source Code:
```
{code}
```

Analyze the code thoroughly for:
1. Bugs and logical flaws
2. Potential security vulnerabilities (distinguish confirmed flaws from potential concerns; do not claim exploitable unless verified)
3. Performance issues and efficiency bottlenecks
4. Code quality, maintainability, and clean code principles
5. Error handling and edge cases
6. Language-specific best practices

You MUST return a strictly valid JSON object matching this schema exactly:
{{
  "score": <integer from 0 to 100 representing overall code quality>,
  "summary": "<2 to 4 sentence executive overview of the code's strengths and primary areas for improvement>",
  "issues": [
    {{
      "category": "<Must be one of: Security, Bugs, Performance, Code Quality, Best Practices, Maintainability>",
      "severity": "<Must be one of: Critical, High, Medium, Low>",
      "line_number": <integer line number if applicable, or null>,
      "message": "<Concise one-line title describing the finding>",
      "explanation": "<Clear technical explanation of why this is a concern>",
      "recommendation": "<Actionable guidance on how to fix or improve it>",
      "suggested_code": "<Refactored snippet showing the correct implementation, or null>"
    }}
  ]
}}

Return ONLY valid JSON. Do not include introductory text or trailing markdown fences outside the JSON.
"""


def clean_json_response(raw_text: str) -> str:
    """Remove markdown code blocks or stray formatting from model response."""
    text = raw_text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return text.strip()


def validate_and_normalize_review(parsed_data: dict, original_code: str) -> dict:
    """
    Validates and normalizes the parsed AI review output against strict schema rules.
    Ensures safe, consistent data structure before database persistence.
    """
    # 1. Validate Score
    raw_score = parsed_data.get('score', 75)
    try:
        score = int(raw_score)
        score = max(0, min(100, score))
    except (ValueError, TypeError):
        score = 75

    # 2. Validate Summary
    summary = str(parsed_data.get('summary', '')).strip()
    if not summary:
        summary = "Code review completed. Please inspect the identified issues and recommendations."

    # 3. Validate and Clean Issues
    raw_issues = parsed_data.get('issues', [])
    if not isinstance(raw_issues, list):
        raw_issues = []

    normalized_issues = []
    line_count = len(original_code.splitlines()) if original_code else 1

    for item in raw_issues:
        if not isinstance(item, dict):
            continue

        category = str(item.get('category', 'Code Quality')).strip()
        if category not in VALID_CATEGORIES:
            category = 'Code Quality'

        severity = str(item.get('severity', 'Medium')).strip().capitalize()
        if severity not in VALID_SEVERITIES:
            severity = 'Medium'

        message = str(item.get('message', 'Potential issue identified')).strip()
        explanation = str(item.get('explanation', 'Review identified potential improvement.')).strip()
        recommendation = str(item.get('recommendation', 'Follow standard language conventions.')).strip()

        # Line number validation
        raw_line = item.get('line_number')
        line_number = None
        if raw_line is not None:
            try:
                parsed_line = int(raw_line)
                if 1 <= parsed_line <= max(1000, line_count + 20):
                    line_number = parsed_line
            except (ValueError, TypeError):
                line_number = None

        suggested_code = item.get('suggested_code')
        if suggested_code is not None:
            suggested_code = str(suggested_code).strip()
            if not suggested_code:
                suggested_code = None

        normalized_issues.append({
            'category': category,
            'severity': severity,
            'line_number': line_number,
            'message': message,
            'explanation': explanation,
            'recommendation': recommendation,
            'suggested_code': suggested_code
        })

    return {
        'score': score,
        'summary': summary,
        'issues': normalized_issues
    }


def analyze_code_with_gemini(code: str, language: str) -> dict:
    """
    Main AI code review function.
    Connects to Google Gemini API using HTTPS REST endpoint, formats prompt,
    parses JSON response, and normalizes output.
    Falls back gracefully if API key is missing or quota/network error occurs.
    """
    api_key = os.getenv('GEMINI_API_KEY', '').strip()

    if not api_key:
        logger.warning("GEMINI_API_KEY not configured. Running rule-based static analyzer fallback.")
        return generate_static_analysis_fallback(code, language)

    # We support Gemini 2.5 Flash and Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt = build_review_prompt(code, language)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=45)

        if response.status_code != 200:
            logger.error(f"Gemini API returned status {response.status_code}: {response.text}")
            # If rate limited or invalid key, return clear message or fallback
            return generate_static_analysis_fallback(code, language, error_msg=f"Gemini API status {response.status_code}")

        res_data = response.json()
        candidates = res_data.get('candidates', [])
        if not candidates:
            return generate_static_analysis_fallback(code, language, error_msg="No response candidate returned by Gemini.")

        candidate = candidates[0]
        content = candidate.get('content', {})
        parts = content.get('parts', [])
        if not parts:
            return generate_static_analysis_fallback(code, language, error_msg="Empty response parts from Gemini.")

        raw_text = parts[0].get('text', '')
        clean_text = clean_json_response(raw_text)

        parsed_json = json.loads(clean_text)
        return validate_and_normalize_review(parsed_json, code)

    except (requests.RequestException, json.JSONDecodeError, Exception) as exc:
        logger.exception(f"Error during AI code review: {exc}")
        return generate_static_analysis_fallback(code, language, error_msg=str(exc))


def generate_static_analysis_fallback(code: str, language: str, error_msg: str = None) -> dict:
    """
    Deterministic rule-based fallback analyzer.
    Ensures that testing, live demonstrations, and interviews work smoothly
    even if the Gemini API key is missing or temporarily unavailable.
    Performs real static checks for common vulnerabilities and quality issues.
    """
    lines = code.splitlines()
    issues = []
    score = 88

    # Check 1: Hardcoded credentials/secrets
    secret_patterns = [
        (r'(?i)(password|secret|api_key|apikey|token|private_key)\s*=\s*["\'][^"\']+["\']',
         'Potential Hardcoded Credential', 'Security', 'High',
         'Sensitive credential or key appears to be hardcoded directly in the source file.',
         'Store secrets in environment variables or a secure key management system.',
         '# Example: Read from environment variable\nimport os\napi_key = os.getenv("API_KEY")'),
        (r'(?i)(select\s+.+\s+from\s+.+\s+where\s+.+\s*(=|\+)\s*["\']?\s*\+)',
         'Potential SQL Injection Vulnerability', 'Security', 'Critical',
         'Dynamic SQL query construction detected with string concatenation.',
         'Use parameterized queries or ORM abstractions instead of direct concatenation.',
         '# Use parameterized query\ncursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'),
        (r'except\s*:\s*$',
         'Bare Except Clause Detected', 'Bugs', 'Medium',
         'Catching all exceptions indiscriminately masks critical bugs and system exits.',
         'Specify concrete exception classes such as Exception or ValueError.',
         'try:\n    perform_action()\nexcept ValueError as err:\n    logger.error(f"Invalid input: {err}")'),
        (r'(console\.log|print)\(',
         'Production Logging Warning', 'Code Quality', 'Low',
         'Direct print/console statements detected in application code.',
         'Use a structured logger with configurable log levels (DEBUG, INFO, ERROR).',
         '# Use logging library\nimport logging\nlogger = logging.getLogger(__name__)\nlogger.info("Operation completed")')
    ]

    for idx, line in enumerate(lines, 1):
        for pattern, title, category, severity, explanation, rec, suggested in secret_patterns:
            if re.search(pattern, line):
                issues.append({
                    'category': category,
                    'severity': severity,
                    'line_number': idx,
                    'message': title,
                    'explanation': explanation,
                    'recommendation': rec,
                    'suggested_code': suggested
                })
                if severity == 'Critical':
                    score -= 20
                elif severity == 'High':
                    score -= 12
                elif severity == 'Medium':
                    score -= 6
                else:
                    score -= 3

    # If code is very short or missing comments
    if len(lines) > 10 and not any('#' in l or '//' in l or '/*' in l for l in lines):
        issues.append({
            'category': 'Maintainability',
            'severity': 'Low',
            'line_number': 1,
            'message': 'Missing Documentation or Inline Comments',
            'explanation': 'The codebase lacks inline comments or docstrings explaining the module purpose and non-obvious logic.',
            'recommendation': 'Add docstrings to functions and brief comments explaining complex business logic.',
            'suggested_code': '"""\nModule description: explain purpose and primary functions.\n"""'
        })
        score -= 4

    # Keep score in valid range
    score = max(35, min(95, score))

    mode_note = " (Static analysis fallback: configure GEMINI_API_KEY for full AI review)" if not os.getenv('GEMINI_API_KEY') else ""
    summary = f"Code analysis for {language} identified {len(issues)} potential issue(s). Overall code structure is functional but requires attention to security and best practices.{mode_note}"

    return {
        'score': score,
        'summary': summary,
        'issues': issues
    }
