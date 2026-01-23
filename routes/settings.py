from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db  # Import your SQLAlchemy db object
from models import User  # Import your User model

# Create blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

# Profile / Settings dashboard
@settings_bp.route('/', methods=['GET'])
@login_required
def settings_home():
    return render_template('profile.html', current_user=current_user, title="Profile Settings")


# Update Profile route
@settings_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        # Get form data
        name = request.form.get('name')
        phone = request.form.get('phone')
        company = request.form.get('company')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip')
        tax_id = request.form.get('tax_id')

        # Update current_user
        current_user.name = name
        current_user.phone = phone
        current_user.company = company
        current_user.address = address
        current_user.city = city
        current_user.state = state
        current_user.zip = zip_code
        current_user.tax_id = tax_id

        # Commit changes
        db.session.commit()
        return jsonify({"message": "Profile updated successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Failed to update profile: {str(e)}"}), 500


# Change Password route
@settings_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_new_password = request.form.get('confirm_new_password')

        # Validate current password
        if not check_password_hash(current_user.password, current_password):
            return jsonify({"message": "Current password is incorrect."}), 400

        # Confirm new password matches
        if new_password != confirm_new_password:
            return jsonify({"message": "New passwords do not match."}), 400

        # Update password
        current_user.password = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({"message": "Password updated successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Failed to update password: {str(e)}"}), 500
