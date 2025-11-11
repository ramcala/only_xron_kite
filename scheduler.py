from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from zoneinfo import ZoneInfo
from models import db, ScheduledOrder, KiteUser
from models import ScheduledOrderLog
import json
from kite_client import KiteClientWrapper
import logging

logger = logging.getLogger(__name__)


def place_order(session, order: ScheduledOrder):
    user = session.query(KiteUser).get(order.user_id)
    if not user:
        order.status = "failed"
        session.add(order)
        session.commit()
        # log failure
        try:
            log = ScheduledOrderLog(
                scheduled_order_id=order.id,
                user_id=order.user_id,
                status='failed',
                message='Kite user not found during execution',
            )
            session.add(log)
            session.commit()
        except Exception:
            logger.exception('Failed to write order log for missing user')
        return {"status": "error", "error": "kite user not found"}

    kc = KiteClientWrapper(user.api_key, user.api_secret, user.access_token)
    tx = "BUY" if order.order_type.lower() == "buy" else "SELL"
    res = kc.place_order(order.stock_symbol, order.quantity, tx)
    if res.get("status") == "success":
        order.status = "completed"
        order.kite_order_id = res.get("order_id")
    else:
        order.status = "failed"
    session.add(order)
    session.commit()

    # create execution log
    try:
        msg = None
        try:
            msg = json.dumps(res)
        except Exception:
            msg = str(res)
        log = ScheduledOrderLog(
            scheduled_order_id=order.id,
            user_id=order.user_id,
            status=order.status,
            message=msg,
        )
        session.add(log)
        session.commit()
    except Exception:
        logger.exception('Failed to write order execution log for order %s', order.id)
    return res


def place_pending_orders(app, session_maker):
    """Find pending orders scheduled <= now and try to place them."""
    with app.app_context():
        session = session_maker()
        # Get current time in IST (same timezone as stored scheduled_time)
        ist = ZoneInfo('Asia/Kolkata')
        now_ist = datetime.now(ist).replace(tzinfo=None)
        pending = session.query(ScheduledOrder).filter(
            ScheduledOrder.status == "pending",
            ScheduledOrder.scheduled_time <= now_ist,
        ).all()
        for order in pending:
            logger.info("Placing scheduled order id=%s for %s", order.id, order.stock_symbol)
            try:
                place_order(session, order)
            except Exception:
                logger.exception("Failed to place order %s", order.id)


def start_scheduler(app, session_maker):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: place_pending_orders(app, session_maker),
        'interval',
        minutes=1,
        id='place_pending_orders'
    )
    scheduler.start()
    return scheduler
