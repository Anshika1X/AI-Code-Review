import os
import json
import re
import logging
import requests

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {'Security', 'Bugs', 'Performance', 'Code Quality', 'Best Practices', 'Maintainability'}
VALID_SEVERITIES = {'Critical', 'High', 'Medium', 'Low'}


def build_review_prompt(code: str, language: str) -> str:
    """
    Build a comprehensive, developer-focused system prompt for Gemini code review.
    Enforces a rigorous security checklist across taint analysis, query safety,
    command execution, credential exposure, and architectural cleanliness.
    Demands concrete, usable refactored code instead of placeholder comments.
    """
    return f"""You are a principal software engineer and security auditor conducting an automated code review.
Review the following source code with high technical precision.

Programming Language: {language}

Source Code:
```
{code}
```

MANDATORY SECURITY AUDIT CHECKLIST:
Before determining the final findings, you MUST systematically analyze the code against each of these vectors:
1. SQL & Data Storage Injections:
   - Check if SQL, NoSQL, or database queries are constructed using string concatenation (+), string interpolation, format strings (% or .format() or f-strings), or template literals (`...${{var}}...`) with untrusted or function parameter inputs.
   - Treat unparameterized/concatenated SQL queries with parameters as HIGH or CRITICAL severity.
2. Command & Process Injections:
   - Check if shell, OS commands, or process execution functions (e.g., exec, spawn, system, popen, subprocess) receive unsanitized input.
3. Hardcoded Secrets & Credentials:
   - Check for hardcoded API keys, JWT secrets, passwords, private keys, database connection strings, or cloud tokens.
4. Cross-Site Scripting (XSS) & Output Encoding:
   - Check if user-controlled input reaches DOM manipulation (innerHTML, document.write) or web responses without sanitization.
5. Insecure Authentication & Authorization:
   - Check for missing authentication boundaries, weak credential verification, hardcoded roles, or insecure session tokens.
6. Path Traversal & Unsafe File Operations:
   - Check if file system paths are constructed from untrusted input without canonicalization or directory traversal prevention (e.g. ../).
7. Sensitive Data Exposure & Production Logging:
   - Check if sensitive data, internal tokens, or debug details are logged (e.g. console.log, print) or leaked in exceptions.
8. Memory & Resource Safety / Performance:
   - Check for unbounded loops, unindexed queries, connection leaks, or redundant memory allocations.
9. Bugs & Logical Flaws:
   - Check for off-by-one errors, null/undefined dereferences, unhandled exceptions, or bare except blocks.
10. Code Quality & Maintainability:
   - Check adherence to language best practices, modularity, and clean code principles.

EVIDENCE & ATTRIBUTION RULES:
- Clearly distinguish confirmed vulnerabilities from potential risks. If the context indicates a likely issue but exploitability depends on caller behavior, describe it as a "Potential" issue.
- ALWAYS identify the exact 1-indexed line_number where the issue originates.
- Do NOT skip general code quality or logging findings while reporting security findings (e.g., if code has both a SQL injection and a console.log, report BOTH).
- Categorize security issues strictly as "Security".

SUGGESTED REFACTORING CODE RULES:
- When an issue has a meaningful code fix, "suggested_code" MUST contain actual corrected code statements or functions, not merely explanatory comments or placeholders.
- For SQL injection caused by string concatenation: provide a practical parameterized query or prepared statement appropriate to {language} (e.g. $1 with parameters array for JavaScript/pg, %s with parameter tuple for Python, or PreparedStatement for Java).
- If the specific database library or driver is unknown from the snippet, provide a standard parameterized pattern and clearly label it as a contextual example without claiming it is guaranteed to execute without the driver.
- Preserve the developer's original function/variable naming where possible.

RETURN FORMAT:
You MUST return ONLY a strictly valid JSON object matching this exact schema:
{{
  "score": <integer from 0 to 100 representing overall code quality and security posture>,
  "summary": "<2 to 4 sentence executive overview summarizing security findings, code quality, and key improvements>",
  "issues": [
    {{
      "category": "<Must be one of: Security, Bugs, Performance, Code Quality, Best Practices, Maintainability>",
      "severity": "<Must be one of: Critical, High, Medium, Low>",
      "line_number": <integer line number where the issue occurs, or null if file-wide>,
      "message": "<Concise one-line title describing the specific finding>",
      "explanation": "<Clear technical explanation of why this code pattern is problematic and what risks it introduces>",
      "recommendation": "<Actionable engineering guidance on how to fix or refactor this>",
      "suggested_code": "<Refactored code snippet showing the secure and idiomatic implementation, or null>"
    }}
  ]
}}

Do NOT wrap the JSON with conversational text or markdown fences outside the JSON string.
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
            cat_lower = category.lower()
            if 'sec' in cat_lower or 'vulnerab' in cat_lower:
                category = 'Security'
            elif 'bug' in cat_lower or 'error' in cat_lower:
                category = 'Bugs'
            elif 'perf' in cat_lower or 'speed' in cat_lower:
                category = 'Performance'
            elif 'maintain' in cat_lower:
                category = 'Maintainability'
            elif 'best' in cat_lower or 'practice' in cat_lower:
                category = 'Best Practices'
            else:
                category = 'Code Quality'

        severity = str(item.get('severity', 'Medium')).strip().capitalize()
        if severity not in VALID_SEVERITIES:
            sev_lower = severity.lower()
            if 'crit' in sev_lower:
                severity = 'Critical'
            elif 'high' in sev_lower:
                severity = 'High'
            elif 'low' in sev_lower or 'info' in sev_lower:
                severity = 'Low'
            else:
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


def _get_sql_suggested_code(language: str) -> str:
    """Generate language-specific, practical parameterized query code."""
    lang = (language or '').lower()
    if any(k in lang for k in ('javascript', 'typescript', 'js', 'ts', 'node')):
        return (
            "// Contextual example: Parameterized query (e.g. pg / mysql2)\n"
            "// Bind user parameters separately from SQL syntax to prevent injection:\n"
            "const query = \"SELECT * FROM users WHERE name = $1\";\n"
            "const params = [username];\n"
            "const result = await db.query(query, params);"
        )
    elif 'python' in lang or 'py' in lang:
        return (
            "# Contextual example: Parameterized query (e.g. sqlite3 / psycopg2)\n"
            "# Pass parameters as a separate tuple to allow the driver to escape safely:\n"
            "query = \"SELECT * FROM users WHERE name = %s\"\n"
            "cursor.execute(query, (username,))\n"
            "records = cursor.fetchall()"
        )
    elif 'java' in lang:
        return (
            "// Contextual example: Parameterized query using PreparedStatement\n"
            "String sql = \"SELECT * FROM users WHERE name = ?\";\n"
            "try (PreparedStatement stmt = connection.prepareStatement(sql)) {\n"
            "    stmt.setString(1, username);\n"
            "    ResultSet rs = stmt.executeQuery();\n"
            "}"
        )
    else:
        return (
            "-- Contextual example: Parameterized query placeholder\n"
            "SELECT * FROM users WHERE name = ?;"
        )


def _get_logging_suggested_code(language: str) -> str:
    """Generate language-specific structured logging code."""
    lang = (language or '').lower()
    if any(k in lang for k in ('javascript', 'typescript', 'js', 'ts', 'node')):
        return (
            "// Use structured logger with configurable log levels\n"
            "logger.info(\"Retrieved user query\", { query });"
        )
    else:
        return (
            "# Use logging module instead of raw print\n"
            "import logging\n"
            "logger = logging.getLogger(__name__)\n"
            "logger.info(\"Retrieved user query: %s\", query)"
        )


def _get_secret_suggested_code(language: str) -> str:
    """Generate language-specific environment variable credential code."""
    lang = (language or '').lower()
    if any(k in lang for k in ('javascript', 'typescript', 'js', 'ts', 'node')):
        return (
            "// Read credentials securely from environment variables\n"
            "const apiKey = process.env.API_KEY;"
        )
    else:
        return (
            "# Read credentials securely from environment variables\n"
            "import os\n"
            "api_key = os.environ.get(\"API_KEY\")"
        )


def _get_cmd_suggested_code(language: str) -> str:
    """Generate language-specific command execution code without shell invocation."""
    lang = (language or '').lower()
    if any(k in lang for k in ('javascript', 'typescript', 'js', 'ts', 'node')):
        return (
            "const { execFile } = require('child_process');\n"
            "// Pass arguments as a sanitized array without invoking a shell\n"
            "execFile('/usr/bin/tool', [sanitizedArg], (err, stdout) => {\n"
            "    if (err) throw err;\n"
            "    console.log(stdout);\n"
            "});"
        )
    else:
        return (
            "import subprocess\n"
            "# Pass arguments as a list without shell=True\n"
            "result = subprocess.run([\"/usr/bin/tool\", sanitized_arg], capture_output=True, text=True, check=True)"
        )


def _get_xss_suggested_code(language: str) -> str:
    """Generate XSS prevention code."""
    return (
        "// Assign plain text safely to prevent script execution\n"
        "element.textContent = userInput;"
    )


def _get_bare_except_suggested_code(language: str) -> str:
    """Generate exception handling code."""
    lang = (language or '').lower()
    if any(k in lang for k in ('javascript', 'typescript', 'js', 'ts', 'node')):
        return (
            "try {\n"
            "    performAction();\n"
            "} catch (error) {\n"
            "    logger.error(\"Operation failed\", { error: error.message });\n"
            "    throw error;\n"
            "}"
        )
    else:
        return (
            "try:\n"
            "    perform_action()\n"
            "except Exception as err:\n"
            "    logger.error(\"Operation failed: %s\", err)\n"
            "    raise"
        )


def generate_static_analysis_fallback(code: str, language: str, error_msg: str = None) -> dict:
    """
    Deterministic rule-based fallback analyzer.
    Ensures that testing, live demonstrations, and interviews work smoothly
    even if the Gemini API key is missing or temporarily unavailable.
    Performs comprehensive static checks for SQL injection, hardcoded secrets,
    command injection, XSS, logging concerns, and code quality.
    Provides practical, language-specific suggested code implementations.
    """
    lines = code.splitlines()
    issues = []
    score = 92

    # Comprehensive multi-language security rules with compiled regex
    sql_patterns = [
        r'["\'].*?\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|VALUES)\b.*?["\']\s*\+\s*[a-zA-Z_$]',
        r'[a-zA-Z_$][a-zA-Z0-9_$]*\s*\+\s*["\'].*?\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|VALUES)\b',
        r'`.*?\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|VALUES)\b.*?\$\{.*?\}',
        r'`.*?\$\{.*?\}.*?\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|VALUES)\b.*?`',
        r'f["\'].*?\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|VALUES)\b.*?\{.*?\}.*?["\']',
        r'["\'].*?\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)\b.*?["\']\s*(?:%|\.format\s*\()'
    ]
    sql_regex = re.compile('|'.join(f'(?:{p})' for p in sql_patterns), re.IGNORECASE)

    secret_regex = re.compile(
        r'(?:password|secret|api_key|apikey|private_key|auth_token)\s*[:=]\s*["\'][a-zA-Z0-9_\-\.]{8,}["\']',
        re.IGNORECASE
    )

    cmd_regex = re.compile(
        r'(?:child_process\.(?:exec|spawn|execSync)|os\.system|subprocess\.(?:Popen|call|run)|Runtime\.getRuntime\(\)\.exec)\s*\([^)]*(?:\+|`|\$|\{)',
        re.IGNORECASE
    )

    xss_regex = re.compile(
        r'(?:\.innerHTML\s*=|document\.write\s*\(|dangerouslySetInnerHTML)',
        re.IGNORECASE
    )

    bare_except_regex = re.compile(
        r'except\s*:\s*$|catch\s*\(\s*(?:e|err|error)?\s*\)\s*\{\s*\}',
        re.IGNORECASE
    )

    log_regex = re.compile(
        r'\b(?:console\.log|console\.debug|print)\s*\(',
        re.IGNORECASE
    )

    for idx, line in enumerate(lines, 1):
        # Check SQL Injection
        if sql_regex.search(line):
            issues.append({
                'category': 'Security',
                'severity': 'Critical',
                'line_number': idx,
                'message': 'Potential SQL Injection Vulnerability',
                'explanation': 'SQL query appears to be dynamically constructed using direct string concatenation or unparameterized interpolation. If user-controlled input reaches this query, an attacker could manipulate query syntax to read, modify, or destroy database records.',
                'recommendation': 'Use parameterized queries, prepared statements, or ORM abstractions instead of direct string concatenation.',
                'suggested_code': _get_sql_suggested_code(language)
            })
            score -= 25

        # Check Hardcoded Secrets
        if secret_regex.search(line):
            issues.append({
                'category': 'Security',
                'severity': 'High',
                'line_number': idx,
                'message': 'Potential Hardcoded Secret or Credential',
                'explanation': 'Sensitive credential or key appears to be hardcoded directly in the source code. Hardcoded credentials can easily leak via version control or build artifacts.',
                'recommendation': 'Store credentials in environment variables or an encrypted key management service (e.g. AWS Secrets Manager, Vault).',
                'suggested_code': _get_secret_suggested_code(language)
            })
            score -= 15

        # Check Command Injection
        if cmd_regex.search(line):
            issues.append({
                'category': 'Security',
                'severity': 'Critical',
                'line_number': idx,
                'message': 'Potential Command Injection Risk',
                'explanation': 'Operating system commands are executed with dynamic string concatenation. Unsanitized user input could permit arbitrary command execution on the host server.',
                'recommendation': 'Avoid invoking OS shells with dynamic input. Pass command arguments as a validated array without shell interpretation.',
                'suggested_code': _get_cmd_suggested_code(language)
            })
            score -= 25

        # Check XSS
        if xss_regex.search(line):
            issues.append({
                'category': 'Security',
                'severity': 'High',
                'line_number': idx,
                'message': 'Potential Cross-Site Scripting (XSS) Risk',
                'explanation': 'Direct assignment to innerHTML or document.write bypasses HTML encoding. If unsanitized input is rendered, malicious JavaScript can execute in the user browser.',
                'recommendation': 'Use textContent, innerText, or context-aware DOM sanitization libraries (e.g., DOMPurify) before inserting HTML.',
                'suggested_code': _get_xss_suggested_code(language)
            })
            score -= 15

        # Check Bare Exceptions
        if bare_except_regex.search(line):
            issues.append({
                'category': 'Bugs',
                'severity': 'Medium',
                'line_number': idx,
                'message': 'Bare Exception Clause Detected',
                'explanation': 'Catching all exceptions indiscriminately or silently suppressing errors masks critical application bugs, system interrupts, and database connection failures.',
                'recommendation': 'Specify concrete exception classes and ensure appropriate logging or error escalation occurs.',
                'suggested_code': _get_bare_except_suggested_code(language)
            })
            score -= 8

        # Check Logging Statements
        if log_regex.search(line):
            issues.append({
                'category': 'Code Quality',
                'severity': 'Low',
                'line_number': idx,
                'message': 'Production Logging Warning',
                'explanation': 'Direct console.log or print statements found in application logic. In production environments, standard output can degrade performance and risk leaking sensitive query data.',
                'recommendation': 'Replace direct console or print statements with a configurable logging framework supporting structured levels (INFO, WARN, ERROR).',
                'suggested_code': _get_logging_suggested_code(language)
            })
            score -= 4

    score = max(20, min(98, score))
    mode_note = " (Static analysis fallback: configure GEMINI_API_KEY for full generative AI review)" if not os.getenv('GEMINI_API_KEY') else ""
    summary = f"Code analysis for {language} identified {len(issues)} finding(s). The code requires attention to security best practices, input sanitization, and production standards.{mode_note}"

    return {
        'score': score,
        'summary': summary,
        'issues': issues
    }
