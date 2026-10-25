"""Database models: User -> Property -> TaxDemand -> Payment."""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), default="citizen", nullable=False)  # citizen | admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    properties = db.relationship("Property", backref="owner", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)  # never store plain text

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    property_no = db.Column(db.String(30), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    ward = db.Column(db.String(50))
    property_type = db.Column(db.String(20), nullable=False)  # Residential | Commercial | Industrial
    area_sqft = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    demands = db.relationship(
        "TaxDemand", backref="property", lazy=True, cascade="all, delete-orphan"
    )


class TaxDemand(db.Model):
    """One bill per property per financial year."""
    __tablename__ = "tax_demands"
    __table_args__ = (db.UniqueConstraint("property_id", "financial_year"),)

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    financial_year = db.Column(db.String(10), nullable=False)  # e.g. "2026-27"
    base_amount = db.Column(db.Float, nullable=False)
    rebate_deadline = db.Column(db.Date, nullable=False)  # pay by this date -> rebate
    due_date = db.Column(db.Date, nullable=False)         # pay after this -> penalty
    status = db.Column(db.String(10), default="Unpaid", nullable=False)  # Unpaid | Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship("Payment", backref="demand", lazy=True)


class Payment(db.Model):
    """Every payment attempt (online or manual). Only status='success' counts."""
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    demand_id = db.Column(db.Integer, db.ForeignKey("tax_demands.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # property owner
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # admin, for manual entries

    base_amount = db.Column(db.Float, nullable=False)
    penalty = db.Column(db.Float, default=0)
    rebate = db.Column(db.Float, default=0)
    amount = db.Column(db.Float, nullable=False)  # final amount = base + penalty - rebate

    method = db.Column(db.String(20), default="Razorpay")  # Razorpay | Cash | Cheque | DD
    reference = db.Column(db.String(60))                   # cheque / DD number etc.
    razorpay_order_id = db.Column(db.String(60), index=True)
    razorpay_payment_id = db.Column(db.String(60))
    razorpay_signature = db.Column(db.String(200))

    status = db.Column(db.String(10), default="created")  # created | success | failed
    receipt_no = db.Column(db.String(30), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)

    user = db.relationship("User", foreign_keys=[user_id])

    def mark_success(self, razorpay_payment_id=None, razorpay_signature=None):
        """Finalise a payment: set status, receipt number and close the demand.
        Safe to call twice (verify route + webhook may both arrive)."""
        if self.status == "success":
            return
        db.session.flush()  # make sure self.id exists
        self.status = "success"
        self.paid_at = datetime.utcnow()
        self.receipt_no = f"MTC-{self.paid_at:%Y}-{self.id:06d}"
        if razorpay_payment_id:
            self.razorpay_payment_id = razorpay_payment_id
        if razorpay_signature:
            self.razorpay_signature = razorpay_signature
        self.demand.status = "Paid"
