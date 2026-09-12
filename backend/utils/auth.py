from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from models import User


def hash_password(password: str) -> str:
    """Hash a plain text password using secure salted hashing."""
    return generate_password_hash(password, method='scrypt')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against stored hash."""
    return check_password_hash(hashed_password, plain_password)


def generate_token(user_id: int, email: str, name: str, expires_hours: int = 24) -> str:
    """Generate a signed JWT token containing user identity."""
    payload = {
        'user_id': user_id,
        'email': email,
        'name': name,
        'exp': datetime.now(timezone.utc) + timedelta(hours=expires_hours),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    return jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])


def token_required(f):
    """
    Decorator for protecting Flask routes with Bearer JWT tokens.
    Injects the authenticated User object as current_user.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')

        if not auth_header:
            return jsonify({
                'success': False,
                'error': 'Authorization header is missing. Please log in.'
            }), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                'success': False,
                'error': 'Invalid Authorization header format. Expected "Bearer <token>".'
            }), 401

        token = parts[1]

        try:
            payload = decode_token(token)
            user_id = payload.get('user_id')
            from models import db
            current_user = db.session.get(User, user_id)

            if not current_user:
                return jsonify({
                    'success': False,
                    'error': 'User account no longer exists.'
                }), 401

        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'Your session has expired. Please log in again.'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': 'Invalid authorization token. Please log in again.'
            }), 401
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Authentication failed. Please log in again.'
            }), 401

        return f(current_user, *args, **kwargs)

    return decorated
