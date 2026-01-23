from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime, date, time

from models import db, Product, Bill

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

# -------- Dashboard Page --------
@dashboard_bp.route("/")
@login_required
def dashboard_home():
    return render_template("dashboard.html")


# -------- Dashboard Metrics API --------
@dashboard_bp.route("/api/metrics")
@login_required
def dashboard_metrics():
    # Product metrics
    total_products = db.session.query(func.count(Product.id)).scalar() or 0
    low_stock = Product.query.filter(Product.stock < 5).count()
    low_stock_items = Product.query.filter(Product.stock <= 5).all()

    # Sales metrics
    total_sales = (
        db.session.query(func.coalesce(func.sum(Bill.total), 0))
        .scalar()
    )

    # Today's date range
    today = date.today()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)

    bills_today = (
        db.session.query(func.count(Bill.id))
        .filter(Bill.bill_date >= start, Bill.bill_date <= end)
        .scalar()
        or 0
    )

    today_sales = (
        db.session.query(func.coalesce(func.sum(Bill.total), 0))
        .filter(Bill.bill_date >= start, Bill.bill_date <= end)
        .scalar()
    )

    return jsonify({
        "today_sales": float(today_sales),
        "bills_today": bills_today,
        "total_products": total_products,
        "low_stock": low_stock,
        "total_sales": float(total_sales),
        "low_stock_items": [
            {"name": p.name, "stock": p.stock} for p in low_stock_items
        ]
    })
