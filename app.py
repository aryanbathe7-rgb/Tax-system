"""Application factory. Run with:  python app.py   (or: flask --app app run)"""
from datetime import datetime, timedelta

from flask import Flask, redirect, send_from_directory, url_for
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import db, login_manager
from models import Payment, Property, TaxDemand, User
from utils.tax_calculator import calculate_base_tax, current_fy_start, fy_dates, fy_label


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Hosts such as Render put a proxy in front of the app; this makes Flask see https correctly
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # --- extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- blueprints (route registration) ---
    from routes.auth import bp as auth_bp
    from routes.citizen import bp as citizen_bp
    from routes.admin import bp as admin_bp
    from routes.payment import bp as payment_bp

    for blueprint in (auth_bp, citizen_bp, admin_bp, payment_bp):
        app.register_blueprint(blueprint)

    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        target = "admin.dashboard" if current_user.is_admin else "citizen.dashboard"
        return redirect(url_for(target))

    # --- PWA files ---
    # The service worker must be served from "/" (not /static/) so it can control the whole site.
    @app.route("/service-worker.js")
    def service_worker():
        response = send_from_directory(app.static_folder, "service-worker.js",
                                       mimetype="application/javascript")
        response.headers["Cache-Control"] = "no-cache"  # browser re-checks for updates
        response.headers["Service-Worker-Allowed"] = "/"
        return response

    @app.route("/manifest.webmanifest")
    def manifest():
        return send_from_directory(app.static_folder, "manifest.json",
                                   mimetype="application/manifest+json")

    # Jinja filter: {{ 1234.5 | inr }} -> ₹1,234.50
    @app.template_filter("inr")
    def inr(value):
        return "₹{:,.2f}".format(value or 0)

    # --- create tables + default admin on first run ---
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="admin").first():
            admin = User(name="Tax Officer", email=app.config["ADMIN_EMAIL"], role="admin")
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.add(admin)
            db.session.commit()
        if app.config["SEED_DEMO"]:
            seed_demo_data()

    register_cli(app)
    return app


def seed_demo_data():
    """Create a demo citizen with 2 properties, 3 years of bills and some payments.
    Returns a message string. Safe to call repeatedly."""
    if User.query.filter_by(email="citizen@example.com").first():
        return "Demo data already exists."
    user = User(name="Demo Citizen", email="citizen@example.com", phone="9876543210")
    user.set_password("Citizen@123")
    db.session.add(user)
    db.session.flush()

    props = [
        Property(owner_id=user.id, property_no="KOP-001", ward="Ward A",
                 address="12 Rajarampuri, Kolhapur", property_type="Residential", area_sqft=1200),
        Property(owner_id=user.id, property_no="KOP-002", ward="Ward B",
                 address="45 Station Road, Kolhapur", property_type="Commercial", area_sqft=800),
    ]
    db.session.add_all(props)
    db.session.flush()

    fy = current_fy_start()
    for prop in props:
        for start in (fy - 2, fy - 1, fy):
            rebate_deadline, due_date = fy_dates(start)
            db.session.add(TaxDemand(
                property_id=prop.id, financial_year=fy_label(start),
                base_amount=calculate_base_tax(prop.area_sqft, prop.property_type),
                rebate_deadline=rebate_deadline, due_date=due_date))
    db.session.flush()

    # Pay the oldest bill of each property at different past dates so charts have data
    for i, prop in enumerate(props):
        demand = TaxDemand.query.filter_by(
            property_id=prop.id, financial_year=fy_label(fy - 2)).first()
        pay = Payment(demand_id=demand.id, user_id=user.id, base_amount=demand.base_amount,
                      amount=demand.base_amount, method="Cash")
        db.session.add(pay)
        pay.mark_success()
        pay.paid_at = datetime.utcnow() - timedelta(days=40 * (i + 1))
    db.session.commit()
    return "Demo data created.  Citizen login: citizen@example.com / Citizen@123"


def register_cli(app):
    @app.cli.command("seed-demo")
    def seed_demo():
        """flask --app app seed-demo"""
        print(seed_demo_data())


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
