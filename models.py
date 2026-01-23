from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


# ==========================
# User Model
# ==========================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.name}>"


# ==========================
# Product Model
# ==========================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    gst = db.Column(db.Float, default=0.18)
    stock = db.Column(db.Integer, nullable=False, default=0)
    category = db.Column(db.String(50), default="Uncategorized")

    def __repr__(self):
        return f"<Product {self.name}>"


# ==========================
# Bill Model
# ==========================
class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    bill_date = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<Bill {self.id}>"


# ==========================
# Bill Item Model
# ==========================
class BillItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    bill_id = db.Column(
        db.Integer,
        db.ForeignKey("bill.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    product = db.relationship("Product")
    bill = db.relationship(
        "Bill",
        backref=db.backref("items", lazy=True)
    )

    def __repr__(self):
        return f"<BillItem bill={self.bill_id} product={self.product_id}>"
