from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from models import db, Bill, BillItem, Product
from sqlalchemy import func
import os, json
from dotenv import load_dotenv   #type: ignore
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


# ==========================
# 🤖 AI INSIGHT GENERATOR
# ==========================
def generate_ai_insight(daily_sales, top_products, total_bills):
    if not daily_sales or len(daily_sales) < 2:
        return ["📊 Not enough data yet to generate insights."]

    revenues = [float(d.revenue or 0) for d in daily_sales]
    first, last = revenues[0], revenues[-1]
    avg_daily = sum(revenues) / len(revenues)
    growth_pct = ((last - first) / first * 100) if first > 0 else 0

    insights = []

    # Revenue trend
    if growth_pct > 5:
        insights.append(f"📈 Revenue increased by {growth_pct:.1f}%. Customer demand or order values have increased.")
    elif growth_pct < -5:
        insights.append(f"📉 Revenue dropped by {abs(growth_pct):.1f}%.")
        insights.append("Possible seasonal slowdown or fewer customers.")
    else:
        insights.append("📊 Revenue remained stable.")
        insights.append("Sales activity appears consistent.")

    # Bills insight
    if total_bills > 0:
        avg_bill = sum(revenues) / total_bills
        insights.append(f"🧾 Average bill value is ₹{avg_bill:.2f}.")
    else:
        insights.append("🧾 No billing activity yet.")

    # Product concentration
    if top_products and len(top_products) > 1:
        top, second = top_products[0], top_products[1]
        insights.append(f"🧠 '{top.name}' significantly outperforms '{second.name}', showing strong product preference.")
    elif top_products:
        insights.append(f"🧠 Most sales depend on '{top_products[0].name}'. Diversifying promotions could reduce risk.")
    else:
        insights.append("🧠 Product sales distribution is still forming.")

    # Prediction
    predicted_next_month = avg_daily * 30
    insights.append(f"🔮 Expected revenue next month: approx ₹{predicted_next_month:,.0f} if current trend continues.")

    # Risk / Opportunity
    insights.append("⚠️ Focus on retention and offers." if growth_pct < 0 else "🚀 Opportunity to scale marketing or inventory.")

    return insights


def generate_gpt_insights(metrics):
    """
    Returns structured AI insights using GPT
    """
    prompt = f"""
        You are a senior business analyst.
        Analyze the business data below and return insights STRICTLY in JSON with keys:
            trend, reason, prediction, risk, recommendation
        Business Data:
            - Total Revenue: ₹{metrics['total_sales']}
            - Total Bills: {metrics['total_bills']}
            - Revenue Growth (%): {metrics['growth_pct']:.2f}
            - Average Bill Value: ₹{metrics['avg_bill']:.2f}
            - Top Product: {metrics['top_product']}
        Rules:
            - Return concise sentences
            - No paragraphs
            - No emojis
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("GPT INSIGHT ERROR:", e)
        return None


# ==========================
# 📄 REPORTS PAGE
# ==========================
@reports_bp.route("/")
@login_required
def reports_home():
    return render_template("reports.html")


# ==========================
# 📊 REPORTS DATA API
# ==========================
@reports_bp.route("/data")
@login_required
def reports_data():
    # ---- Optimized Queries ----
    # Daily Revenue
    daily_sales = db.session.query(
        func.strftime('%Y-%m-%d', Bill.bill_date).label('date'),
        func.sum(Bill.total).label('revenue')
    ).group_by('date').order_by('date').all()

    # Top Products
    top_products = db.session.query(
        Product.name,
        func.sum(BillItem.quantity).label('sold')
    ).join(BillItem, BillItem.product_id == Product.id) \
     .group_by(Product.id).order_by(func.sum(BillItem.quantity).desc()).limit(5).all()

    # Monthly stats
    monthly_stats = db.session.query(
        func.strftime('%Y-%m', Bill.bill_date).label('month'),
        func.sum(Bill.total).label('revenue'),
        func.count(Bill.id).label('bills')
    ).group_by('month').order_by('month').all()

    # Totals
    total_sales = float(db.session.query(func.sum(Bill.total)).scalar() or 0)
    total_bills = int(db.session.query(func.count(Bill.id)).scalar() or 0)

    # ---- Daily / Monthly arrays ----
    daily_labels = [d.date for d in daily_sales]
    daily_revenue = [float(d.revenue or 0) for d in daily_sales]

    months = [m.month for m in monthly_stats]
    current_month_revenue = [float(m.revenue or 0) for m in monthly_stats]
    previous_month_revenue = [0] + current_month_revenue[:-1]

    current_month_bills = [int(m.bills or 0) for m in monthly_stats]
    previous_month_bills = [0] + current_month_bills[:-1]

    # ---- AI Insights ----
    ai_insights_basic = generate_ai_insight(daily_sales, top_products, total_bills)

    # GPT insights metrics
    revenues = daily_revenue
    growth_pct = ((revenues[-1] - revenues[0]) / revenues[0] * 100) if revenues and revenues[0] > 0 else 0
    avg_bill = (sum(revenues) / total_bills) if total_bills else 0
    metrics = {
        "total_sales": total_sales,
        "total_bills": total_bills,
        "growth_pct": growth_pct,
        "avg_bill": avg_bill,
        "top_product": top_products[0].name if top_products else "None"
    }
    gpt_insights = generate_gpt_insights(metrics)

    return jsonify({
        "daily_labels": daily_labels,
        "daily_revenue": daily_revenue,
        "top_product_names": [p.name for p in top_products],
        "top_product_sales": [int(p.sold) for p in top_products],
        "total_sales": total_sales,
        "total_bills": total_bills,
        "ai_insights_basic": {"sentences": ai_insights_basic},
        "ai_insights_gpt": gpt_insights,
        "months": months,
        "current_month_revenue": current_month_revenue,
        "previous_month_revenue": previous_month_revenue,
        "current_month_bills": current_month_bills,
        "previous_month_bills": previous_month_bills
    })
