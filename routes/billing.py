# routes/billing.py
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Product, Bill, BillItem, Customer
from datetime import datetime
from sqlalchemy import func
from io import BytesIO

# optional: reportlab for PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

bp = Blueprint("billing", __name__, url_prefix="/billing")

DEFAULT_GST = 0.18 

# ---------------------------------------------------
# CRM HELPER (Billing → CRM integration)
# ---------------------------------------------------
def update_customer_after_bill(customer_id, bill_total):
    if not customer_id:
        return

    customer = Customer.query.get(customer_id)
    if not customer:
        return

    customer.total_orders += 1
    customer.total_spent += float(bill_total)
    customer.last_purchase = datetime.utcnow()

    db.session.commit()

# ---------------- Billing page (render) ----------------
@bp.route("/", methods=["GET"])
@login_required
def billing_home():
    products = Product.query.order_by(Product.name).all()
    product_list = []
    for p in products:
        gst = getattr(p, "gst", None)
        product_list.append({
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "stock": int(p.stock),
            "category": getattr(p, "category", ""),
            "gst": float(gst) if gst is not None else DEFAULT_GST
        })
    bills = Bill.query.order_by(Bill.bill_date.desc()).limit(10).all()
    return render_template("billing.html", products=product_list, bills=bills, user=current_user)


# ---------------- Product lookup ----------------
@bp.route("/product/<int:product_id>", methods=["GET"])
@login_required
def get_product(product_id):
    p = Product.query.get_or_404(product_id)
    gst = getattr(p, "gst", None)
    return jsonify({
        "id": p.id,
        "name": p.name,
        "price": float(p.price),
        "stock": int(p.stock),
        "category": getattr(p, "category", ""),
        "gst": float(gst) if gst is not None else DEFAULT_GST
    })


# ---------------- Create bill ----------------
@bp.route("/create", methods=["POST"])
@login_required
def create_bill():
    data = request.get_json() or {}
    items = data.get("items") or []
    customer_id = data.get("customer_id")
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "No items provided"}), 400

    # validate & compute subtotal (use DB price & gst)
    subtotal = 0.0
    validated = []
    for it in items:
        try:
            pid = int(it.get("id"))
            qty = int(it.get("quantity", 0))
        except Exception:
            return jsonify({"error": "Invalid item format"}), 400
        if qty <= 0:
            return jsonify({"error": f"Invalid quantity for product id {pid}"}), 400
        product = Product.query.get(pid)
        if not product:
            return jsonify({"error": f"Product not found: {pid}"}), 404
        if product.stock < qty:
            return jsonify({"error": f"Insufficient stock for {product.name} (available {product.stock})"}), 400

        # product-level GST if present, else default (we will compute gst on whole subtotal)
        line = float(product.price) * qty
        subtotal += line
        validated.append((product, qty, line))

    # compute GST overall as weighted average if product gst present
    # Approach: compute gst per item if product.gst exists, else use DEFAULT_GST.
    gst_amount = 0.0
    for product, qty, line in validated:
        prod_gst = getattr(product, "gst", None)
        rate = float(prod_gst) if prod_gst is not None else DEFAULT_GST
        gst_amount += line * rate

    # round
    gst_amount = round(gst_amount, 2)
    total = round(subtotal + gst_amount, 2)

    # create bill
    bill = Bill(customer_name=data.get("customer_name", "Walk-in Customer"), customer_id=customer_id,
                bill_date=datetime.utcnow(),
                total=total)
    db.session.add(bill)
    db.session.commit() # get id

    # create bill items and update stock
    for product, qty, line in validated:
        bi = BillItem(bill_id=bill.id,
                      product_id=product.id,
                      quantity=qty,
                      subtotal=line)
        product.stock -= qty
        db.session.add(bi)
    db.session.commit()

     # 🔥 CRM UPDATE
    update_customer_after_bill(customer_id, total)

    return jsonify({
        "message": "Bill created",
        "bill_id": bill.id,
        "subtotal": round(subtotal, 2),
        "gst": gst_amount,
        "total": total
    }), 201


# ---------------- View bill (HTML printable) ----------------
@bp.route("/view/<int:bill_id>", methods=["GET"])
@login_required
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    items = BillItem.query.filter_by(bill_id=bill.id).all()
    # ensure product relationships accessible in template
    return render_template("view_bill.html", bill=bill, items=items, user=current_user)


# ---------------- Billing data (products + recent + low-stock) ----------------
@bp.route("/data", methods=["GET"])
@login_required
def billing_data():
    products = Product.query.order_by(Product.name).all()
    product_list = [{"id": p.id, "name": p.name, "price": float(p.price), "stock": int(p.stock)} for p in products]
    bills = Bill.query.order_by(Bill.bill_date.desc()).limit(10).all()
    recent = [{"id": b.id, "customer_name": b.customer_name, "date": b.bill_date.strftime("%Y-%m-%d %H:%M"), "total": float(b.total)} for b in bills]
    # low stock
    low = Product.query.filter(Product.stock < 5).order_by(Product.stock.asc()).all()
    low_stock = [{"id": p.id, "name": p.name, "stock": int(p.stock)} for p in low]
    return jsonify({"products": product_list, "recent_bills": recent, "low_stock": low_stock})


# ---------------- Invoice PDF (server) ----------------
@bp.route("/invoice/<int:bill_id>/pdf", methods=["GET"])
@login_required
def invoice_pdf(bill_id):
    if not REPORTLAB_AVAILABLE:
        return jsonify({"error": "reportlab not installed on server"}), 500

    bill = Bill.query.get_or_404(bill_id)
    items = BillItem.query.filter_by(bill_id=bill.id).all()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - inch, "Invoice - SmartBill.AI")

    # Bill meta
    c.setFont("Helvetica", 11)
    c.drawString(inch, height - 1.5 * inch, f"Bill ID: {bill.id}")
    c.drawString(inch, height - 1.8 * inch, f"Customer: {bill.customer_name}")
    c.drawString(inch, height - 2.1 * inch, f"Date: {bill.bill_date.strftime('%Y-%m-%d %H:%M')}")

    # Table header
    y = height - 2.6 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(inch, y, "Item")
    c.drawRightString(width - inch, y, "Subtotal")
    y -= 0.18 * inch
    c.line(inch, y, width - inch, y)
    y -= 0.12 * inch

    c.setFont("Helvetica", 10)
    subtotal = 0.0
    for it in items:
        prod = Product.query.get(it.product_id)
        text = f"{prod.name} x {it.quantity}"
        c.drawString(inch, y, text)
        c.drawRightString(width - inch, y, f"{it.subtotal:.2f}")
        subtotal += it.subtotal
        y -= 0.25 * inch
        if y < inch:
            c.showPage()
            y = height - inch

    # GST: compute as total - subtotal if possible
    gst_amount = round(bill.total - subtotal, 2) if bill.total else round(subtotal * DEFAULT_GST, 2)
    total_amount = round(bill.total, 2) if bill.total else round(subtotal + gst_amount, 2)

    y -= 0.12 * inch
    c.line(inch, y, width - inch, y)
    y -= 0.25 * inch
    c.drawString(inch, y, "Subtotal:")
    c.drawRightString(width - inch, y, f"Rs. {subtotal:.2f}")
    y -= 0.22 * inch
    c.drawString(inch, y, "GST (approx):")
    c.drawRightString(width - inch, y, f"Rs. {gst_amount:.2f}")
    y -= 0.22 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch, y, "Total:")
    c.drawRightString(width - inch, y, f"Rs. {total_amount:.2f}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"invoice_{bill.id}.pdf")

@bp.route("/print/<int:bill_id>")
@login_required
def print_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    items = BillItem.query.filter_by(bill_id=bill.id).all()
    return render_template(
        "print_bill.html",
        bill=bill,
        items=items,
        user=current_user
    )

