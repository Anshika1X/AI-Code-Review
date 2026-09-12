import re
import requests
from flask import Blueprint, request, jsonify
from models import db, Review, Issue
from utils.auth import token_required
from services.ai_service import analyze_code_with_gemini

reviews_bp = Blueprint('reviews', __name__, url_prefix='/api')

SUPPORTED_LANGUAGES = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'C', 'C++', 'C#',
    'Go', 'Rust', 'PHP', 'Ruby', 'SQL', 'HTML', 'CSS', 'Bash'
]


@reviews_bp.route('/reviews', methods=['POST'])
@token_required
def create_review(current_user):
    """
    Submit source code for AI review.
    Analyzes code via Gemini AI service and persists review and issues to PostgreSQL.
    """
    data = request.get_json(silent=True) or {}

    raw_code = data.get('code')
    language = (data.get('language') or 'Python').strip()

    # Required validation
    if not raw_code or not str(raw_code).strip():
        return jsonify({
            'success': False,
            'error': 'Please enter some code before starting the review.'
        }), 400

    code = str(raw_code).strip()

    # Run AI review service
    try:
        analysis = analyze_code_with_gemini(code, language)
    except Exception as exc:
        return jsonify({
            'success': False,
            'error': 'Unable to complete the AI review right now. Please try again.'
        }), 500

    # Save to database
    try:
        review = Review(
            user_id=current_user.id,
            language=language,
            code=code,
            score=analysis.get('score', 75),
            summary=analysis.get('summary', 'Code review completed.')
        )
        db.session.add(review)
        db.session.flush()  # Populates review.id for child issues

        for issue_data in analysis.get('issues', []):
            issue = Issue(
                review_id=review.id,
                category=issue_data.get('category', 'Code Quality'),
                severity=issue_data.get('severity', 'Medium'),
                message=issue_data.get('message', 'Issue identified'),
                line_number=issue_data.get('line_number'),
                explanation=issue_data.get('explanation', ''),
                recommendation=issue_data.get('recommendation', ''),
                suggested_code=issue_data.get('suggested_code')
            )
            db.session.add(issue)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Code review completed successfully.',
            'review': review.to_dict()
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Something went wrong while saving your review.'
        }), 500


@reviews_bp.route('/reviews', methods=['GET'])
@token_required
def get_user_reviews(current_user):
    """Retrieve all reviews for the authenticated user."""
    language_filter = request.args.get('language')
    limit = request.args.get('limit', default=50, type=int)

    query = Review.query.filter_by(user_id=current_user.id)

    if language_filter:
        query = query.filter(Review.language.ilike(f"%{language_filter}%"))

    reviews = query.order_by(Review.created_at.desc()).limit(limit).all()

    return jsonify({
        'success': True,
        'count': len(reviews),
        'reviews': [r.to_dict(include_code=False, include_issues=False) for r in reviews]
    }), 200


@reviews_bp.route('/reviews/<int:review_id>', methods=['GET'])
@token_required
def get_single_review(current_user, review_id):
    """Retrieve a single review by ID, ensuring user ownership."""
    review = Review.query.filter_by(id=review_id, user_id=current_user.id).first()

    if not review:
        return jsonify({
            'success': False,
            'error': 'Review not found.'
        }), 404

    return jsonify({
        'success': True,
        'review': review.to_dict(include_code=True, include_issues=True)
    }), 200


@reviews_bp.route('/reviews/<int:review_id>', methods=['DELETE'])
@token_required
def delete_review(current_user, review_id):
    """Delete a review and all associated issues."""
    review = Review.query.filter_by(id=review_id, user_id=current_user.id).first()

    if not review:
        return jsonify({
            'success': False,
            'error': 'Review not found.'
        }), 404

    try:
        db.session.delete(review)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Review deleted successfully.'
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to delete review. Please try again.'
        }), 500


@reviews_bp.route('/reviews/github', methods=['POST'])
@token_required
def review_github_repo_file(current_user):
    """
    Optional GitHub integration:
    Fetches raw source file from a public GitHub repo URL and executes review.
    """
    data = request.get_json(silent=True) or {}
    github_url = (data.get('repo_url') or '').strip()
    file_path = (data.get('file_path') or '').strip().lstrip('/')
    branch = (data.get('branch') or 'main').strip()

    if not github_url or not file_path:
        return jsonify({
            'success': False,
            'error': 'Both GitHub repository URL and file path are required.'
        }), 400

    # Extract owner and repo from URL like https://github.com/owner/repo
    match = re.search(r'github\.com/([^/]+)/([^/]+)', github_url)
    if not match:
        return jsonify({
            'success': False,
            'error': 'Invalid GitHub repository URL format. Example: https://github.com/pallets/flask'
        }), 400

    owner, repo = match.group(1), match.group(2).replace('.git', '')
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"

    try:
        res = requests.get(raw_url, timeout=15)
        if res.status_code == 404 and branch == 'main':
            # Try fallback branch 'master'
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{file_path}"
            res = requests.get(raw_url, timeout=15)

        if res.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Could not retrieve file "{file_path}" from repository (HTTP {res.status_code}). Please check repo visibility and file path.'
            }), 400

        source_code = res.text

        # Infer language from file extension
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        ext_map = {
            'py': 'Python', 'js': 'JavaScript', 'ts': 'TypeScript', 'java': 'Java',
            'c': 'C', 'cpp': 'C++', 'cs': 'C#', 'go': 'Go', 'rs': 'Rust',
            'sql': 'SQL', 'html': 'HTML', 'css': 'CSS', 'sh': 'Bash'
        }
        language = ext_map.get(ext, 'Python')

        # Run review via standard pipeline
        analysis = analyze_code_with_gemini(source_code, language)

        review = Review(
            user_id=current_user.id,
            language=f"{language} ({repo}/{file_path})",
            code=source_code,
            score=analysis.get('score', 75),
            summary=analysis.get('summary', 'GitHub code review completed.')
        )
        db.session.add(review)
        db.session.flush()

        for issue_data in analysis.get('issues', []):
            issue = Issue(
                review_id=review.id,
                category=issue_data.get('category', 'Code Quality'),
                severity=issue_data.get('severity', 'Medium'),
                message=issue_data.get('message', 'Issue identified'),
                line_number=issue_data.get('line_number'),
                explanation=issue_data.get('explanation', ''),
                recommendation=issue_data.get('recommendation', ''),
                suggested_code=issue_data.get('suggested_code')
            )
            db.session.add(issue)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Successfully analyzed {file_path} from GitHub.',
            'review': review.to_dict()
        }), 201

    except requests.RequestException:
        return jsonify({
            'success': False,
            'error': 'Network error while attempting to connect to GitHub.'
        }), 500
    except Exception:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Error saving review from GitHub file.'
        }), 500
