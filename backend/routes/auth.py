import re
from flask import Blueprint, request, jsonify
from models import db, User
from utils.auth import hash_password, verify_password, generate_token, token_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account with validation and password hashing."""
    data = request.get_json(silent=True) or {}

    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or data.get('confirmPassword') or ''

    # Required field validation
    if not name:
        return jsonify({'success': False, 'error': 'Name is required.'}), 400
    if not email:
        return jsonify({'success': False, 'error': 'Email is required.'}), 400
    if not password:
        return jsonify({'success': False, 'error': 'Password is required.'}), 400

    # Email format validation
    if not EMAIL_REGEX.match(email):
        return jsonify({'success': False, 'error': 'Please provide a valid email address.'}), 400

    # Password length validation
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters long.'}), 400

    # Password confirmation
    if confirm_password and password != confirm_password:
        return jsonify({'success': False, 'error': 'Passwords do not match.'}), 400

    # Duplicate email check
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'An account with this email already exists.'}), 400

    try:
        new_user = User(
            name=name,
            email=email,
            password_hash=hash_password(password)
        )
        db.session.add(new_user)
        db.session.commit()

        token = generate_token(new_user.id, new_user.email, new_user.name)

        return jsonify({
            'success': True,
            'message': 'Account registered successfully.',
            'token': token,
            'user': new_user.to_dict()
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred while creating your account. Please try again.'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user with email and password, returning a JWT token."""
    data = request.get_json(silent=True) or {}

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'success': False, 'error': 'Both email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not verify_password(password, user.password_hash):
        return jsonify({'success': False, 'error': 'Invalid email or password.'}), 401

    token = generate_token(user.id, user.email, user.name)

    return jsonify({
        'success': True,
        'message': 'Login successful.',
        'token': token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Retrieve details of the authenticated user."""
    return jsonify({
        'success': True,
        'user': current_user.to_dict()
    }), 200
