from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class KiteUser(db.Model):
    __tablename__ = "kite_users"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), unique=True, nullable=False)
    api_key = db.Column(db.String(256), nullable=False)
    api_secret = db.Column(db.String(256), nullable=False)
    access_token = db.Column(db.String(1024), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "api_key": self.api_key,
            "user_id": self.user_id,
            "api_secret": "*****",
            "access_token": bool(self.access_token),
            "created_at": self.created_at.isoformat(),
        }


class ScheduledOrder(db.Model):
    __tablename__ = "scheduled_orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('kite_users.id'), nullable=False)
    stock_symbol = db.Column(db.String(64), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order_type = db.Column(db.String(8), nullable=False)  # buy or sell
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(32), default="pending")  # pending, completed, failed
    kite_order_id = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "stock_symbol": self.stock_symbol,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "scheduled_time": self.scheduled_time.isoformat(),
            "status": self.status,
            "kite_order_id": self.kite_order_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
