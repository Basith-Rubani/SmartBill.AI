from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from sqlalchemy import func

from models import db, Customer, Bill

crm_bp = Blueprint("crm", __name__, url_prefix="/crm")


# ========================
# CRM MAIN PAGE
# ========================
@crm_bp.route("/")
@login_required
def crm_page():
    return render_template("crm.html")


# ========================
# CUSTOMER PROFILE PAGE (HTML)
# ========================
@crm_bp.route("/customer/<int:customer_id>")
@login_required
def customer_profile(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    bills = (
    Bill.query
    .filter_by(customer_id=customer_id)
    .order_by(Bill.bill_date.desc())
    .all()
    )

    bill_chart_data = [
    {
        "date": b.bill_date.isoformat(),
        "total": float(b.total)
    }
    for b in bills
    ]


    total_spend = sum(b.total for b in bills)
    total_bills = len(bills)

    return render_template(
    "customer_profile.html",
    customer=customer,
    bills=bills,                     # for table
    bill_chart_data=bill_chart_data, # for chart
    total_spend=round(total_spend, 2),
    total_bills=total_bills
)


# ========================
# API: GET ALL CUSTOMERS
# ========================
@crm_bp.route("/api/customers")
@login_required
def get_customers():
    customers = Customer.query.order_by(Customer.total_spent.desc()).all()
    return jsonify([c.to_dict() for c in customers])


# ========================
# API: ADD CUSTOMER
# ========================
@crm_bp.route("/api/customer", methods=["POST"])
@login_required
def add_customer():
    data = request.json

    customer = Customer(
        name=data.get("name"),
        phone=data.get("phone"),
        email=data.get("email"),
        address=data.get("address"),
        notes=data.get("notes"),
    )

    db.session.add(customer)
    db.session.commit()

    return jsonify({"success": True, "customer_id": customer.id})


# ========================
# API: CUSTOMER DETAILS (JSON)
# ========================
@crm_bp.route("/api/customer/<int:customer_id>")
@login_required
def customer_details(customer_id):
    customer = Customer.query.get_or_404(customer_id)

    bills = (
        Bill.query
        .filter_by(customer_id=customer_id)
        .order_by(Bill.bill_date.desc())
        .all()
    )

    return jsonify({
        "customer": customer.to_dict(),
        "bills": [
            {
                "id": b.id,
                "total": b.total,
                "date": b.bill_date.isoformat()
            } for b in bills
        ]
    })

@crm_bp.route("/api/customer/<int:customer_id>", methods=["PUT"])
@login_required
def update_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    data = request.json

    customer.name = data.get("name", customer.name)
    customer.phone = data.get("phone", customer.phone)
    customer.email = data.get("email", customer.email)
    customer.address = data.get("address", customer.address)

    db.session.commit()
    return jsonify({"success": True})

# ========================
# CRM METRICS
# ========================
@crm_bp.route("/api/metrics")
@login_required
def crm_metrics():
    now = datetime.utcnow()
    inactive_cutoff = now - timedelta(days=30)

    total_customers = Customer.query.count()

    repeat_customers = Customer.query.filter(
        Customer.total_orders > 1
    ).count()

    # 🔥 TOP CUSTOMER
    top_customer = (
        Customer.query
        .filter(Customer.total_spent > 0)
        .order_by(Customer.total_spent.desc())
        .first()
    )

    # 🔥 INACTIVE CUSTOMERS
    inactive_customers = Customer.query.filter(
        (Customer.last_purchase == None) |
        (Customer.last_purchase < inactive_cutoff)
    ).count()

    return jsonify({
        "total_customers": total_customers,
        "repeat_customers": repeat_customers,
        "top_customer": top_customer.name if top_customer else "—",
        "inactive_customers": inactive_customers
    })

@crm_bp.route("/api/ai-insight")
@login_required
def ai_crm_insight():
    total = Customer.query.count()
    repeat = Customer.query.filter(Customer.total_orders > 1).count()

    if total == 0:
        insight = "No customer data available yet."
    else:
        repeat_ratio = round((repeat / total) * 100, 1)

        if repeat_ratio > 50:
            insight = f"{repeat_ratio}% of customers are repeat buyers. Loyalty programs can boost revenue further."
        elif repeat_ratio > 25:
            insight = f"Only {repeat_ratio}% customers return. Consider follow-up offers or SMS reminders."
        else:
            insight = "Low repeat rate detected. First-time customer conversion needs improvement."

    return jsonify({"insight": insight})


# ⚠️ ADMIN ONLY — one-time migration / maintenance

@crm_bp.route("/admin/rebuild-crm", methods=["GET", "POST"])
@login_required
def rebuild_crm():
    customers = Customer.query.all()

    for customer in customers:
        # 🔗 link old bills by name (case-insensitive)
        bills = Bill.query.filter(
            func.lower(Bill.customer_name) == func.lower(customer.name)
        ).all()

        # attach customer_id to bills
        for bill in bills:
            bill.customer_id = customer.id

        customer.total_orders = len(bills)
        customer.total_spent = sum(b.total for b in bills)
        customer.last_purchase = (
            max(b.bill_date for b in bills) if bills else None
        )

    db.session.commit()
    return jsonify({"status": "CRM rebuilt successfully"})

@crm_bp.route("/admin/bootstrap-customers", methods=["GET","POST"])
@login_required
def bootstrap_customers():
    # 1. Get distinct customer names from bills
    bill_names = (
        db.session.query(Bill.customer_name)
        .filter(Bill.customer_name.isnot(None))
        .distinct()
        .all()
    )

    created = 0

    for (name,) in bill_names:
        # skip empty / walk-in names
        if not name or name.lower() in ["walk-in", "walk in", "cash"]:
            continue

        # check if customer already exists
        customer = Customer.query.filter(
            func.lower(Customer.name) == func.lower(name)
        ).first()

        if not customer:
            customer = Customer(name=name)
            db.session.add(customer)
            db.session.flush()  # get customer.id
            created += 1

        # link bills
        bills = Bill.query.filter(
            func.lower(Bill.customer_name) == func.lower(name)
        ).all()

        for bill in bills:
            bill.customer_id = customer.id

        # calculate CRM metrics
        customer.total_orders = len(bills)
        customer.total_spent = sum(b.total for b in bills)
        customer.last_purchase = (
            max(b.bill_date for b in bills) if bills else None
        )

    db.session.commit()

    return jsonify({
        "status": "customers bootstrapped",
        "created_customers": created
    })
