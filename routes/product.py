from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from models import db, Product

bp = Blueprint("product", __name__, url_prefix="/products")  


# ---------- Helpers ----------
def _to_dict(p: Product):
    return {
        "id": p.id,
        "name": p.name,
        "category": getattr(p, "category", "") or "",
        "price": float(p.price),
        "stock": int(p.stock),
        "gst": (
            float(getattr(p, "gst", 0.18))
            if getattr(p, "gst", None) is not None
            else None
        ),
    }


# ---------- Pages ----------
@bp.route("/", methods=["GET"])
@login_required
def page_products():
    return render_template("product.html")


# ---------- APIs ----------
@bp.route("/api", methods=["GET"])
@login_required
def api_list():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "name")

    query = Product.query

    if q:
        q_like = f"%{q}%"

        if q.isdigit():
            query = query.filter(
                (Product.id == int(q))
                | Product.name.ilike(q_like)
                | getattr(Product, "category", Product.name).ilike(q_like)
            )
        else:
            query = query.filter(
                Product.name.ilike(q_like)
                | getattr(Product, "category", Product.name).ilike(q_like)
            )

    desc = False
    if sort.startswith("-"):
        desc = True
        sort = sort[1:]

    order_col = Product.name
    if sort == "price":
        order_col = Product.price
    elif sort == "stock":
        order_col = Product.stock

    if desc:
        order_col = order_col.desc()

    products = query.order_by(order_col).all()

    return jsonify({
        "products": [_to_dict(p) for p in products]
    })


@bp.route("/api", methods=["POST"])
@login_required
def api_create():
    data = request.get_json() or {}

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Product name required"}), 400

    try:
        price = float(data.get("price", 0))
        stock = int(data.get("stock", 0))
    except Exception:
        return jsonify({"error": "Invalid numeric values"}), 400

    category = data.get("category", "") or ""
    gst = data.get("gst", None)

    p = Product(
        name=name,
        price=price,
        stock=stock,
        category=category,
    )

    if hasattr(p, "gst") and gst is not None:
        try:
            p.gst = float(gst)
        except Exception:
            pass

    db.session.add(p)
    db.session.commit()

    return jsonify({
        "message": "Created",
        "product": _to_dict(p),
    }), 201


@bp.route("/api/<int:product_id>", methods=["PUT"])  # ✅ fixed syntax
@login_required
def api_update(product_id):
    p = Product.query.get_or_404(product_id)
    data = request.get_json() or {}

    if "name" in data:
        p.name = str(data["name"]).strip()

    if "category" in data:
        p.category = data["category"] or ""

    if "price" in data:
        try:
            p.price = float(data["price"])
        except Exception:
            return jsonify({"error": "Invalid price"}), 400

    if "stock" in data:
        try:
            p.stock = int(data["stock"])
        except Exception:
            return jsonify({"error": "Invalid stock"}), 400

    if "gst" in data and hasattr(p, "gst"):
        try:
            p.gst = float(data["gst"])
        except Exception:
            pass

    db.session.commit()

    return jsonify({
        "message": "Updated",
        "product": _to_dict(p),
    })


@bp.route("/api/<int:product_id>", methods=["DELETE"])  # ✅ fixed syntax
@login_required
def api_delete(product_id):
    p = Product.query.get_or_404(product_id)

    db.session.delete(p)
    db.session.commit()

    return jsonify({"message": "Deleted"})

