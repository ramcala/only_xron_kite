from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class KiteUser(db.Model):
    __tablename__ = "kite_users"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), unique=True, nullable=True)
    api_key = db.Column(db.String(256), unique=True, nullable=False)
    api_secret = db.Column(db.String(256), nullable=False)
    access_token = db.Column(db.String(1024), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    email = db.Column(db.String(256), nullable=True)
    user_name = db.Column(db.String(256), nullable=True)
    user_shortname = db.Column(db.String(256), nullable=True)
    broker = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    exchanges = db.Column(db.String(256), nullable=True)  # comma-separated list
    products = db.Column(db.String(256), nullable=True)   # comma-separated list
    order_types = db.Column(db.String(256), nullable=True)  # comma-separated list
    avatar_url = db.Column(db.String(1024), nullable=True)
    token_set_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "api_key": self.api_key,
            "api_secret": "*****",
            "access_token": bool(self.access_token),
            "email": self.email,
            "user_name": self.user_name,
            "user_shortname": self.user_shortname,
            "broker": self.broker,
            "created_at": self.created_at.isoformat(),
            "exchanges": self.exchanges.split(",") if self.exchanges else [],
            "products": self.products.split(",") if self.products else [],
            "order_types": self.order_types.split(",") if self.order_types else [],
            "avatar_url": self.avatar_url,
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


class ScheduledOrderLog(db.Model):
    __tablename__ = "scheduled_order_logs"
    id = db.Column(db.Integer, primary_key=True)
    scheduled_order_id = db.Column(db.Integer, db.ForeignKey('scheduled_orders.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('kite_users.id'), nullable=False)
    status = db.Column(db.String(64), nullable=False)
    message = db.Column(db.String(1024), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "scheduled_order_id": self.scheduled_order_id,
            "user_id": self.user_id,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }


class ScheduledOrderBulkAudit(db.Model):
    __tablename__ = 'scheduled_order_bulk_audits'
    id = db.Column(db.Integer, primary_key=True)
    initiator = db.Column(db.String(256), nullable=True)  # who triggered the bulk schedule (optional)
    stock_symbol = db.Column(db.String(64), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order_type = db.Column(db.String(16), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    users_targeted = db.Column(db.Integer, nullable=False, default=0)
    users_created = db.Column(db.Integer, nullable=False, default=0)
    message = db.Column(db.String(1024), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'initiator': self.initiator,
            'stock_symbol': self.stock_symbol,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'scheduled_time': self.scheduled_time.isoformat(),
            'users_targeted': self.users_targeted,
            'users_created': self.users_created,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
        }


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
        }
