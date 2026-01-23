from flask import Flask, jsonify, render_template
from flask_login import LoginManager, login_required, current_user

# Models
from models import db, User, Product, Bill, BillItem  # noqa: F401

# Blueprints
from routes import auth, billing, reports, ai_module, settings
from routes.product import bp as product_bp
from routes.dashboard import dashboard_bp

import os
import sys

# Ensure project root is in path (safe, unchanged behavior)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ==========================
# App Initialization
# ==========================
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret-key"  # change in production

# ==========================
# Extensions
# ==========================
db.init_app(app)

login_manager = LoginManager()
login_manager.login_message = None
login_manager.login_view = "auth.login_page"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================
# Blueprints Registration
# ==========================
app.register_blueprint(auth.bp)
app.register_blueprint(billing.bp)
app.register_blueprint(reports.reports_bp)
app.register_blueprint(ai_module.ai_bp)
app.register_blueprint(settings.settings_bp)
app.register_blueprint(product_bp)
app.register_blueprint(dashboard_bp)


# ==========================
# Routes
# ==========================
@app.route("/")
def index():
    return jsonify({"message": "Billing software backend running"})


@app.route("/init-db", methods=["GET"])
def init_db():
    """Create database tables (run once during setup)."""
    with app.app_context():
        db.create_all()
    return jsonify({"message": "Database initialized (tables created)"}), 201


@app.route("/add-sample-product", methods=["GET"])
def add_sample_product():
    """Add a sample product for testing."""
    product = Product(
        name="Sample Item",
        price=99.0,
        stock=10,
        category="Test"
    )
    db.session.add(product)
    db.session.commit()

    return jsonify(
        {"message": "Sample product added", "product_id": product.id}
    ), 201


@app.route("/dashboard")
@login_required
def dashboard_home():
    return render_template("dashboard.html", user=current_user)


@app.route("/ai-dashboard")
def ai_dashboard():
    return render_template("ai_assistant.html")


@app.route("/reports")
@login_required
def reports_home():
    return render_template("reports.html")


@app.route("/settings")
@login_required
def settings_home():
    return render_template("profile.html")


# ==========================
# Run App
# ==========================
if __name__ == "__main__":
    app.run(debug=False)
