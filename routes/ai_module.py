# ai_module.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from textblob import TextBlob
from sklearn.linear_model import LinearRegression
from sqlalchemy import func
from models import db, Product, Bill, BillItem
import numpy as np
import pandas as pd
import random
import datetime

ai_bp = Blueprint("ai_module", __name__, url_prefix="/ai")

# ==========================
# 📊 SAMPLE SALES DATA (ML DEMO)
# ==========================
sales_data = pd.DataFrame({
    "day": np.arange(1, 11),
    "sales": [1200, 1350, 1280, 1450, 1600, 1580, 1700, 1720, 1800, 1900]
})

# ==========================
# 💬 FEEDBACK SAMPLES
# ==========================
feedback_samples = [
    "I love the new billing interface!",
    "The app is okay but slow sometimes.",
    "Terrible experience with checkout.",
    "Smooth and easy billing process!",
    "Good but can improve."
]

# ==========================
# 🤖 AI DASHBOARD
# ==========================
@ai_bp.route("/")
@login_required
def ai_dashboard():
    return render_template("ai_assistant.html")

# ==========================
# 😊 SENTIMENT ANALYSIS
# ==========================
@ai_bp.route("/sentiment", methods=["GET"])
@login_required
def sentiment_report():
    sentiments = {"positive": 0, "neutral": 0, "negative": 0}

    for feedback in feedback_samples:
        polarity = TextBlob(feedback).sentiment.polarity
        if polarity > 0.1:
            sentiments["positive"] += 1
        elif polarity < -0.1:
            sentiments["negative"] += 1
        else:
            sentiments["neutral"] += 1

    return jsonify(sentiments)

# ==========================
# 📈 SALES PREDICTION (ML)
# ==========================
@ai_bp.route("/predict_sales", methods=["GET"])
@login_required
def predict_sales():
    X = sales_data["day"].values.reshape(-1, 1)
    y = sales_data["sales"].values

    model = LinearRegression()
    model.fit(X, y)

    future_days = np.arange(11, 16).reshape(-1, 1)
    future_sales = model.predict(future_days)

    return jsonify({
        "future_days": future_days.flatten().tolist(),
        "predicted_sales": future_sales.round(2).tolist()
    })

# ==========================
# 🧠 SMART CHAT ASSISTANT
# ==========================
@ai_bp.route("/chat", methods=["POST"])
@login_required
def ai_chat():
    user_msg = request.json.get("message", "").lower()

    # ---- BASIC METRICS ----
    total_sales = float(db.session.query(func.sum(Bill.total)).scalar() or 0)
    total_bills = int(db.session.query(func.count(Bill.id)).scalar() or 0)
    avg_bill = (total_sales / total_bills) if total_bills else 0

    # ---- TODAY SALES ----
    today = datetime.date.today()
    today_sales = float(
        db.session.query(func.sum(Bill.total))
        .filter(func.date(Bill.bill_date) == today)
        .scalar() or 0
    )

    # ---- TOP PRODUCT ----
    top_product = db.session.query(
        Product.name,
        func.sum(BillItem.quantity).label("qty")
    ).join(BillItem, BillItem.product_id == Product.id) \
     .group_by(Product.id) \
     .order_by(func.sum(BillItem.quantity).desc()) \
     .first()

    # ---- LOW STOCK ----
    low_stock_products = db.session.query(Product.name, Product.stock) \
        .filter(Product.stock <= 5).all()

    # ==========================
    # 🎯 INTENT HANDLING
    # ==========================
    if "today" in user_msg and "sale" in user_msg:
        return jsonify({
            "response": f"Today's total sales are ₹{today_sales:.2f}."
        })

    if "total sale" in user_msg or "overall sale" in user_msg:
        return jsonify({
            "response": f"Your total sales so far are ₹{total_sales:.2f} from {total_bills} bills."
        })

    if "average" in user_msg and "bill" in user_msg:
        return jsonify({
            "response": f"The average bill value is ₹{avg_bill:.2f}."
        })

    if "top" in user_msg or "best" in user_msg:
        if top_product:
            return jsonify({
                "response": f"Your top-selling product is '{top_product.name}' with {top_product.qty} units sold."
            })
        return jsonify({"response": "Top product data is not available yet."})

    if "low stock" in user_msg or "out of stock" in user_msg:
        if not low_stock_products:
            return jsonify({"response": "All products have sufficient stock."})
        names = ", ".join(f"{p.name} ({p.stock})" for p in low_stock_products)
        return jsonify({
            "response": f"Low stock items: {names}."
        })

    if "predict" in user_msg or "future" in user_msg:
        predicted = int(sales_data["sales"].mean() * 30)
        return jsonify({
            "response": f"Based on current trends, expected revenue next month is around ₹{predicted:,}."
        })

    if "help" in user_msg or "what can you do" in user_msg:
        return jsonify({
            "response": (
                "I can help with sales summary, top products, low stock alerts, "
                "average bills, trends, and future predictions."
            )
        })

    # ==========================
    # 🟡 FALLBACK
    # ==========================
    return jsonify({
        "response": (
            "I can help with sales, products, stock, trends, and predictions. "
            "Try asking: 'today’s sales', 'top product', or 'low stock items'."
        )
    })

# ==========================
# 💡 AI BUSINESS TIPS
# ==========================
AI_TIPS = [
    "Offer small discounts on slow-moving products to clear inventory.",
    "Restock fast-selling products before weekends.",
    "Track average bill value to spot upsell opportunities.",
    "Promote high-margin products during peak hours.",
    "Review low-stock items daily to avoid lost sales.",
    "Use sales trends to plan next month’s inventory.",
    "Encourage repeat customers with loyalty rewards.",
    "Analyze best-selling products to optimize pricing.",
    "Monitor daily sales to catch drops early.",
    "Automate reports to save time and reduce errors."
]

@ai_bp.route("/tips", methods=["GET"])
@login_required
def get_ai_tip():
    return jsonify({"tip": random.choice(AI_TIPS)})
