from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """User account model for authentication and review ownership."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    reviews = db.relationship('Review', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Review(db.Model):
    """Code review submission model storing user code, score, and summary."""
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    language = db.Column(db.String(50), nullable=False)
    code = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationship to issues
    issues = db.relationship('Issue', backref='review', lazy='selectin', cascade='all, delete-orphan')

    def to_dict(self, include_code=True, include_issues=True):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'language': self.language,
            'score': self.score,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'issues_count': len(self.issues) if self.issues else 0
        }
        if include_code:
            data['code'] = self.code
        if include_issues:
            data['issues'] = [issue.to_dict() for issue in self.issues]
        return data


class Issue(db.Model):
    """Specific issue detected by AI review within a code snippet."""
    __tablename__ = 'issues'

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id', ondelete='CASCADE'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)  # Security, Bugs, Performance, Code Quality, Best Practices
    severity = db.Column(db.String(20), nullable=False)  # Critical, High, Medium, Low
    message = db.Column(db.String(255), nullable=False)
    line_number = db.Column(db.Integer, nullable=True)
    explanation = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    suggested_code = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'review_id': self.review_id,
            'category': self.category,
            'severity': self.severity,
            'message': self.message,
            'line_number': self.line_number,
            'explanation': self.explanation,
            'recommendation': self.recommendation,
            'suggested_code': self.suggested_code
        }
