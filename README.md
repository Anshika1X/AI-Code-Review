# AI Code Review

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-brightgreen.svg?style=for-the-badge&logo=render)](https://ai-code-review-v269.onrender.com)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20SQLAlchemy-blue.svg)](https://www.postgresql.org/)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%20API-orange.svg)](https://aistudio.google.com/)
[![Tests](https://img.shields.io/badge/Tests-24%20Passed%20(Pytest)-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> 🚀 **Live Production Application:** **[https://ai-code-review-v269.onrender.com](https://ai-code-review-v269.onrender.com)**  
> *(Note: Hosted on Render Free Tier. If the instance is sleeping due to inactivity, please allow ~30–50 seconds for initial spin-up.)*  
>  
> **Repository Description:** AI-powered code review application built with Python Flask, PostgreSQL, JavaScript, and Gemini API.  
> **Suggested GitHub Topics:** `python`, `flask`, `postgresql`, `sqlalchemy`, `javascript`, `html`, `css`, `bootstrap`, `gemini-api`, `ai`, `code-review`, `rest-api`, `postman`, `pytest`, `software-testing`

---

## 1. Project Overview

**AI Code Review** is a production-ready, full-stack web application that performs automated, in-depth code quality assessments using the **Google Gemini API**. It evaluates source code for potential security vulnerabilities, bugs, performance bottlenecks, and architectural code smells, returning structured JSON reports with actionable recommendations and refactored code snippets.

Built specifically for a **Graduate Engineer Trainee / Junior Software Engineer** portfolio, the application emphasizes:
- **Clean Architecture:** Separation of concerns between REST API routing, business services, and database persistence.
- **Explainable Engineering:** Simple, standard technologies without unnecessary frameworks or over-engineering.
- **Strict Visual Identity:** Elegant developer-focused interface adhering strictly to an **Olive (`#6B7A3A`), Light Olive (`#E8EDD8`), and White (`#FFFFFF`)** palette.
- **Thorough Verification:** 24 automated Pytest test cases and an exportable Postman test collection with status assertion scripts.

---

## 2. Features

- 🔐 **Secure JWT Authentication:** User registration, bcrypt-grade password hashing (Scrypt), and 24-hour stateless JWT authorization.
- 🤖 **AI-Powered Code Analysis:** Analyzes source code across **6 core dimensions**:
  1. Bugs and logical edge cases
  2. Security vulnerabilities (OWASP, SQL injection, hardcoded credentials)
  3. Performance bottlenecks and complexity issues
  4. Code quality & SOLID principles
  5. Error handling
  6. Language-specific best practices
- 📑 **Structured Review Report:**
  - Code quality score out of 100
  - Executive summary
  - Severity-tagged findings (**Critical**, **High**, **Medium**, **Low**)
  - Line number detection
  - Actionable recommendations with copyable refactored code
- 🔄 **Original vs. Suggested Code Comparison:** Side-by-side inspection allowing engineers to review refactoring recommendations before applying them.
- 🐙 **Public GitHub Import:** Direct analysis of any public GitHub repository file without requiring personal access tokens.
- 📊 **Real-Time Database Analytics:** Dynamic dashboard displaying review trends over time and issue category distribution using **Chart.js**.
- 📜 **Persistent Review History:** User-isolated history stored in **PostgreSQL** with live keyword search, score filters, and deletion with cascading cleanup.
- 🛡️ **Dual-Mode Database Engine:** Connects to **PostgreSQL** via `DATABASE_URL` in production, with automatic zero-configuration fallback to local **SQLite** for testing.
- ⚡ **Resilient AI Fallback:** Includes a built-in static analysis engine that ensures the app continues functioning seamlessly even if Gemini API keys are omitted during an interview demonstration.

---

## 3. Technology Stack

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend UI** | HTML5, CSS3, Vanilla JS (ES6), Bootstrap 5 | Zero build tools required; lightweight, responsive, and easy to explain. |
| **Styling** | Custom Olive Theme | Professional, modern SaaS palette: `#6B7A3A`, `#4F5D2A`, `#E8EDD8`, `#FFFFFF`. |
| **Charts** | Chart.js (via CDN) | Lightweight client-side visualization for review scores and issue breakdown. |
| **Backend API** | Python 3.11+, Flask 3.1.2 | Minimalist, explicit Python microframework ideal for REST APIs. |
| **ORM / Database** | SQLAlchemy 2.0, PostgreSQL | Standard relational database with robust schema definitions and cascade rules. |
| **Authentication** | PyJWT, Werkzeug Security | Secure salted hashing and standard Bearer token authorization. |
| **AI Integration** | Google Gemini API (1.5/2.5 Flash) | Fast, structured JSON generation with strict prompt schema adherence. |
| **Unit Testing** | Pytest | Fast, readable test assertions covering positive, negative, and edge cases. |
| **API Testing** | Postman | Automated collection validating status codes and schema structures. |
| **Deployment** | Render (Backend) + Vercel (Frontend) | Standard cloud platforms for decoupled full-stack deployment. |

---

## 4. Application Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend (HTML5 / Vanilla JS ES6 / Bootstrap 5)"]
        Landing["Landing Page (index.html)"]
        Auth["Login / Register (login.html, register.html)"]
        Dash["Dashboard & Charts (dashboard.html)"]
        Studio["Code Review Studio (review.html)"]
        Report["Review Report & Diff (result.html)"]
        History["Review History (history.html)"]
    end

    subgraph API ["Backend (Python Flask REST API)"]
        AuthBP["Auth Routes (/api/register, /api/login, /api/me)"]
        ReviewBP["Review Routes (/api/reviews, /api/reviews/:id)"]
        DashBP["Dashboard Routes (/api/dashboard)"]
        JWTMiddleware["@token_required Middleware"]
        AIService["AI Service (services/ai_service.py)"]
    end

    subgraph DB ["Database (PostgreSQL / SQLite fallback)"]
        UserModel["Users Table"]
        ReviewModel["Reviews Table"]
        IssueModel["Issues Table"]
    end

    subgraph External ["External AI"]
        GeminiAPI["Google Gemini 1.5/2.5 Flash API"]
    end

    Client -- "HTTP REST (JSON + Bearer JWT)" --> API
    AuthBP --> JWTMiddleware
    ReviewBP --> JWTMiddleware
    DashBP --> JWTMiddleware
    ReviewBP --> AIService
    AIService -- "HTTPS Prompt (JSON Mode)" --> GeminiAPI
    API --> DB
    UserModel --> ReviewModel --> IssueModel
```

---

## 5. Database Design

```
+-------------------------------------------------------------+
|                          users                              |
+-------------------------------------------------------------+
| id            : INTEGER (PK, Auto-increment)                |
| name          : VARCHAR(100), NOT NULL                      |
| email         : VARCHAR(120), UNIQUE, NOT NULL, INDEXED     |
| password_hash : VARCHAR(255), NOT NULL                      |
| created_at    : TIMESTAMP (UTC), NOT NULL                   |
+-------------------------------------------------------------+
                               |
                               | 1:N (Cascade Delete)
                               v
+-------------------------------------------------------------+
|                         reviews                             |
+-------------------------------------------------------------+
| id            : INTEGER (PK, Auto-increment)                |
| user_id       : INTEGER (FK -> users.id, ON DELETE CASCADE) |
| language      : VARCHAR(50), NOT NULL                       |
| code          : TEXT, NOT NULL                              |
| score         : INTEGER, NOT NULL                           |
| summary       : TEXT, NOT NULL                              |
| created_at    : TIMESTAMP (UTC), NOT NULL, INDEXED          |
+-------------------------------------------------------------+
                               |
                               | 1:N (Cascade Delete)
                               v
+-------------------------------------------------------------+
|                          issues                             |
+-------------------------------------------------------------+
| id            : INTEGER (PK, Auto-increment)                |
| review_id     : INTEGER (FK -> reviews.id, CASCADE)         |
| category      : VARCHAR(50), NOT NULL                       |
| severity      : VARCHAR(20), NOT NULL                       |
| message       : VARCHAR(255), NOT NULL                      |
| line_number   : INTEGER, NULLABLE                           |
| explanation   : TEXT, NOT NULL                              |
| recommendation: TEXT, NOT NULL                              |
| suggested_code: TEXT, NULLABLE                              |
+-------------------------------------------------------------+
```

---

## 6. REST API Endpoints

All endpoints (except health and auth) require an `Authorization: Bearer <token>` header.

| Method | Endpoint | Auth Required | Description | Status Codes |
| :--- | :--- | :---: | :--- | :--- |
| `GET` | `/api/health` | No | System health check (DB connectivity & Gemini config) | `200` |
| `POST` | `/api/register` | No | Create user account with name, email, password | `201`, `400`, `500` |
| `POST` | `/api/login` | No | Authenticate user credentials and return JWT token | `200`, `400`, `401` |
| `GET` | `/api/me` | Yes | Get authenticated user profile | `200`, `401` |
| `POST` | `/api/reviews` | Yes | Submit source code for AI review & persistence | `201`, `400`, `401`, `500` |
| `GET` | `/api/reviews` | Yes | Get all reviews belonging to logged-in user | `200`, `401` |
| `GET` | `/api/reviews/<id>`| Yes | Get single review with full issues and source code | `200`, `401`, `404` |
| `DELETE`| `/api/reviews/<id>`| Yes | Delete a review and all associated child issues | `200`, `401`, `404` |
| `POST` | `/api/reviews/github`| Yes | Fetch file from public GitHub repo and review it | `201`, `400`, `401`, `500` |
| `GET` | `/api/dashboard` | Yes | Aggregate metrics, scores over time, category counts | `200`, `401` |

---

## 7. AI Prompt Strategy & Schema Enforcement

The AI engine in `backend/services/ai_service.py` instructs Google Gemini using a strict developer persona:
- **Enforces JSON Format:** Configured with `responseMimeType: "application/json"`.
- **Explicit Schema Requirements:** Demands `score` (0–100), `summary` (2–4 sentences), and an `issues` array.
- **Defensive Parsing & Normalization:** `validate_and_normalize_review()` guarantees that even if the AI hallucinates unexpected keys, line numbers out of range, or unapproved severity strings, the data is safely sanitized before reaching the database.
- **Static Analysis Fallback:** If `GEMINI_API_KEY` is not provided, the application triggers a local rule-based static analyzer detecting SQL injections, hardcoded secrets, and bare except clauses.

---

## 8. Testing Suite

### A. Pytest (Backend Automated Tests)
The test suite is located in `backend/tests/` and uses an in-memory SQLite database to test database isolation, authentication rules, and AI parsing without side effects.

Run the test suite:
```bash
cd backend
python -m pytest tests -v
```

**Results:**
```
tests/test_ai_service.py::test_clean_json_response PASSED
tests/test_ai_service.py::test_validate_and_normalize_review_valid PASSED
tests/test_ai_service.py::test_validate_and_normalize_review_resilience PASSED
tests/test_ai_service.py::test_static_analysis_detects_flaws PASSED
tests/test_ai_service.py::test_javascript_sql_injection_and_console_log PASSED
tests/test_ai_service.py::test_build_review_prompt_security_checklist PASSED
tests/test_ai_service.py::test_suggested_refactoring_practical_code PASSED
tests/test_ai_service.py::test_sql_injection_severity_calibration PASSED
tests/test_ai_service.py::test_command_injection_detection PASSED
tests/test_ai_service.py::test_command_injection_variants PASSED
tests/test_auth.py::test_register_success PASSED
tests/test_auth.py::test_register_duplicate_email PASSED
tests/test_auth.py::test_register_validation_errors PASSED
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_invalid_password PASSED
tests/test_auth.py::test_get_current_user_profile PASSED
tests/test_reviews.py::test_create_review_unauthorized PASSED
tests/test_reviews.py::test_create_review_empty_code PASSED
tests/test_reviews.py::test_create_review_success PASSED
tests/test_reviews.py::test_create_review_javascript_sql_injection_end_to_end PASSED
tests/test_reviews.py::test_get_reviews_history PASSED
tests/test_reviews.py::test_get_single_review_and_isolation PASSED
tests/test_reviews.py::test_delete_review PASSED
tests/test_reviews.py::test_dashboard_metrics PASSED

============================= 24 passed in 8.71s ==============================
```

### B. Postman Collection
Located in `postman/AI-Code-Review.postman_collection.json` with matching environment file `postman/AI-Code-Review.postman_environment.json`.

**How to use:**
1. Open Postman.
2. Click **Import** and drag in both `.json` files from the `postman/` directory.
3. Select the environment **AI Code Review - Local & Production**.
4. Run the requests in order:
   - `Health Check` -> Returns 200
   - `Register - Success` -> Creates user and sets `auth_token`
   - `Login - Success` -> Logs in and stores `auth_token`
   - `Create Review - Success` -> Creates review and sets `review_id`
   - `Get User Reviews History` -> Verifies review appears in list
   - `Get Dashboard Metrics` -> Verifies aggregated statistics
   - `Delete Review` -> Deletes review and verifies removal

---

## 9. Local Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Git

### Step-by-Step Instructions

1. **Clone or Navigate to the Repository:**
   ```bash
   git clone https://github.com/your-username/ai-code-review.git
   cd ai-code-review
   ```

2. **Create and Activate a Virtual Environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure Environment Variables:**
   ```bash
   # Copy example env file
   cp .env.example .env
   ```
   Open `.env` and set your `GEMINI_API_KEY` (free from [Google AI Studio](https://aistudio.google.com/)).  
   *(Note: If you leave `DATABASE_URL` blank, it will automatically use SQLite locally.)*

5. **Start the Flask Backend:**
   ```bash
   cd backend
   python app.py
   ```
   Backend will start on: `http://localhost:5000`

6. **Open the Frontend:**
   - Option A: Simply open `http://localhost:5000` in your web browser (Flask serves the frontend static files automatically!).
   - Option B: Use VS Code "Live Server" or Python HTTP server:
     ```bash
     cd frontend
     python -m http.server 5500
     ```
     Then open `http://localhost:5500/index.html`.

---

## 10. Public Cloud Deployment Guide

The application is engineered to deploy cleanly across decoupled free-tier cloud platforms:

### A. Deploy Managed PostgreSQL Database (Neon or Supabase or Render)
1. Create a free account at [Neon](https://neon.tech/) or [Supabase](https://supabase.com/).
2. Create a new PostgreSQL project named `ai-code-review`.
3. Copy the database connection string:  
   `postgresql://[user]:[password]@[host]/[dbname]?sslmode=require`

### B. Deploy Flask Backend to Render
1. Push your project to GitHub.
2. Sign in to [Render](https://render.com/) and click **New + > Web Service**.
3. Connect your GitHub repository.
4. Set the following settings:
   - **Root Directory:** `backend`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Add Environment Variables:
   - `DATABASE_URL`: *(paste connection string from Neon/Supabase)*
   - `GEMINI_API_KEY`: *(paste your Google Gemini API key)*
   - `JWT_SECRET_KEY`: *(generate a random 32+ character string)*
   - `SECRET_KEY`: *(generate a random string)*
   - `FRONTEND_URL`: `*` (or your Vercel URL once deployed)
6. Click **Deploy Web Service**.
   - **Primary Live Deployment:** **[https://ai-code-review-v269.onrender.com](https://ai-code-review-v269.onrender.com)** (Serves both the Flask REST API and Frontend SPA).

### C. Deploy Frontend to Vercel
1. Sign in to [Vercel](https://vercel.com/) and click **Add New > Project**.
2. Select your repository.
3. Set **Root Directory** to `frontend`.
4. Click **Deploy**.
5. After deployment, open your Vercel site, go to **Settings** (`settings.html`), enter your Render Backend URL, and click **Save & Ping**.

---

## 11. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

