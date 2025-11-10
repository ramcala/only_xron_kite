from flask import Flask, request, jsonify
from config import DATABASE_URL
from models import db, KiteUser, ScheduledOrder
from datetime import datetime
from scheduler import start_scheduler, place_order
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # create DB
    with app.app_context():
        db.create_all()

    # session maker for scheduler
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)

    # start scheduler
    start_scheduler(app, Session)


    @app.route('/users', methods=['POST'])
    def create_user():
        data = request.json or {}
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        access_token = data.get('access_token')
        if not api_key or not api_secret:
            return jsonify({"error": "api_key and api_secret required"}), 400
        user = KiteUser(api_key=api_key, api_secret=api_secret, access_token=access_token)
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201


    @app.route('/users', methods=['GET'])
    def list_users():
        users = KiteUser.query.all()
        return jsonify([u.to_dict() for u in users])


    @app.route('/orders', methods=['POST'])
    def schedule_order():
        data = request.json or {}
        user_id = data.get('user_id')
        stock_symbol = data.get('stock_symbol')
        quantity = data.get('quantity')
        order_type = data.get('order_type')
        scheduled_time = data.get('scheduled_time')

        if not all([user_id, stock_symbol, quantity, order_type, scheduled_time]):
            return jsonify({"error": "user_id, stock_symbol, quantity, order_type, scheduled_time required"}), 400
        try:
            dt = datetime.fromisoformat(scheduled_time)
        except Exception:
            return jsonify({"error": "scheduled_time must be ISO format"}), 400

        order = ScheduledOrder(
            user_id=user_id,
            stock_symbol=stock_symbol,
            quantity=int(quantity),
            order_type=order_type.lower(),
            scheduled_time=dt,
        )
        db.session.add(order)
        db.session.commit()
        return jsonify(order.to_dict()), 201


    @app.route('/orders', methods=['GET'])
    def list_orders():
        orders = ScheduledOrder.query.order_by(ScheduledOrder.scheduled_time.asc()).all()
        return jsonify([o.to_dict() for o in orders])


    @app.route('/orders/<int:order_id>/place', methods=['POST'])
    def place_order_now(order_id):
        order = ScheduledOrder.query.get(order_id)
        if not order:
            return jsonify({"error": "order not found"}), 404
        # use direct DB session with SQLAlchemy's sessionmaker to pass into scheduler place_order
        engine = create_engine(DATABASE_URL, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            res = place_order(session, order)
        finally:
            session.close()
        return jsonify(res)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
