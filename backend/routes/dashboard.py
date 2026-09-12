from flask import Blueprint, jsonify
from sqlalchemy import func
from models import db, Review, Issue
from utils.auth import token_required

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api')


@dashboard_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard_data(current_user):
    """
    Compute real-time dashboard analytics from PostgreSQL for the authenticated user.
    Aggregates review counts, average quality score, issue severities, and trends.
    """
    user_id = current_user.id

    # 1. Total Reviews
    total_reviews = Review.query.filter_by(user_id=user_id).count()

    if total_reviews == 0:
        return jsonify({
            'success': True,
            'stats': {
                'total_reviews': 0,
                'average_score': 0,
                'critical_issues': 0,
                'security_issues': 0
            },
            'score_trend': [],
            'category_distribution': {
                'Security': 0,
                'Bugs': 0,
                'Performance': 0,
                'Code Quality': 0,
                'Best Practices': 0,
                'Maintainability': 0
            },
            'recent_reviews': []
        }), 200

    # 2. Average Score
    avg_score_res = db.session.query(func.avg(Review.score)).filter(Review.user_id == user_id).scalar()
    average_score = round(float(avg_score_res)) if avg_score_res is not None else 0

    # 3. Critical Issues count
    critical_issues = db.session.query(func.count(Issue.id))\
        .join(Review, Review.id == Issue.review_id)\
        .filter(Review.user_id == user_id, Issue.severity == 'Critical')\
        .scalar() or 0

    # 4. Security Issues count
    security_issues = db.session.query(func.count(Issue.id))\
        .join(Review, Review.id == Issue.review_id)\
        .filter(Review.user_id == user_id, Issue.category == 'Security')\
        .scalar() or 0

    # 5. Issues by Category breakdown
    category_counts = db.session.query(Issue.category, func.count(Issue.id))\
        .join(Review, Review.id == Issue.review_id)\
        .filter(Review.user_id == user_id)\
        .group_by(Issue.category)\
        .all()

    category_map = {
        'Security': 0,
        'Bugs': 0,
        'Performance': 0,
        'Code Quality': 0,
        'Best Practices': 0,
        'Maintainability': 0
    }
    for cat, count in category_counts:
        category_map[cat] = count

    # 6. Score Trend over time (up to last 15 reviews chronologically)
    trend_reviews = Review.query.filter_by(user_id=user_id)\
        .order_by(Review.created_at.desc())\
        .limit(15)\
        .all()
    # Reverse to show chronological left-to-right progression
    score_trend = [
        {
            'id': r.id,
            'date': r.created_at.strftime('%b %d, %H:%M') if r.created_at else '',
            'score': r.score,
            'language': r.language
        }
        for r in reversed(trend_reviews)
    ]

    # 7. Recent 5 reviews
    recent_reviews = Review.query.filter_by(user_id=user_id)\
        .order_by(Review.created_at.desc())\
        .limit(5)\
        .all()

    recent_data = [
        {
            'id': r.id,
            'language': r.language,
            'score': r.score,
            'summary': r.summary[:120] + ('...' if len(r.summary) > 120 else ''),
            'issues_count': len(r.issues),
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else ''
        }
        for r in recent_reviews
    ]

    return jsonify({
        'success': True,
        'stats': {
            'total_reviews': total_reviews,
            'average_score': average_score,
            'critical_issues': critical_issues,
            'security_issues': security_issues
        },
        'score_trend': score_trend,
        'category_distribution': category_map,
        'recent_reviews': recent_data
    }), 200
