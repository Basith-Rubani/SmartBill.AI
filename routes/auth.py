from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import re

from models import db, User

bp = Blueprint("auth", __name__)

EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"


# ===================================
# LOGIN
# ===================================
@bp.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_home"))

    if request.method == "POST":
        is_ajax = request.is_json

        # ---- Input Handling (AJAX + Form) ----
        data = request.get_json() if is_ajax else request.form
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        # ---- Validation ----
        if not email or not password:
            return _auth_error(
                "All fields are required.",
                is_ajax,
                redirect_to="auth.login_page",
                status=400,
            )

        user = User.query.filter_by(email=email).first()

        # ---- Authentication ----
        if user and check_password_hash(user.password, password):
            login_user(user)

            if is_ajax:
                return jsonify(
                    {
                        "status": "success",
                        "redirect_url": url_for("dashboard_home"),
                        "username": user.name,
                    }
                ), 200

            flash(f"Welcome back, {user.name}! 👋", "success")
            return redirect(url_for("dashboard_home"))

        return _auth_error(
            "Invalid email or password.",
            is_ajax,
            redirect_to="auth.login_page",
            status=401,
        )

    return render_template("login.html", title="Login - SmartBill.AI")


# ===================================
# REGISTER
# ===================================
@bp.route("/register", methods=["GET", "POST"])
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        # ---- Validation ----
        if not all([name, email, password, confirm]):
            flash("All fields are required.", "warning")
            return redirect(url_for("auth.register_page"))

        if not re.match(EMAIL_REGEX, email):
            flash("Invalid email format.", "danger")
            return redirect(url_for("auth.register_page"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register_page"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return redirect(url_for("auth.register_page"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for("auth.login_page"))

        # ---- Create User ----
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(name=name, email=email, password=hashed_pw)

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in. 🎉", "success")
        return redirect(url_for("auth.login_page"))

    return render_template("register.html", title="Register - SmartBill.AI")


# ===================================
# LOGOUT
# ===================================
@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login_page"))


# ===================================
# HELPER FUNCTIONS
# ===================================
def _auth_error(message, is_ajax, redirect_to, status=400):
    """Unified auth error handler (AJAX + Form)"""
    if is_ajax:
        return jsonify({"status": "error", "message": message}), status

    flash(message, "danger")
    return redirect(url_for(redirect_to))
