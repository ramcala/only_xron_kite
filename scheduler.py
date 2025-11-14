from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from zoneinfo import ZoneInfo
from models import ScheduledOrder, KiteUser
from models import ScheduledOrderLog
import json
from kite_client import KiteClientWrapper
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Polling and concurrency configuration
POLL_INTERVAL_SECONDS = 5
BATCH_SIZE = 50
MAX_WORKERS = 10

# Module-level executor reused across polls
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


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


def _process_order_worker(app, session_maker, order_id):
    """Background worker that claims an order atomically and processes it with its own session."""
    try:
        with app.app_context():
            session = session_maker()
            try:
                # Atomically claim the order (pending -> processing). If another worker claimed it, rowcount will be 0.
                rows = session.query(ScheduledOrder).filter(
                    ScheduledOrder.id == order_id,
                    ScheduledOrder.status == "pending",
                ).update({"status": "processing"}, synchronize_session=False)
                session.commit()
                if not rows:
                    # already claimed/processed by another worker
                    return

                # Re-load the order within this session
                order = session.query(ScheduledOrder).filter_by(id=order_id).one_or_none()
                if not order:
                    logger.warning('Order %s was claimed but not found afterwards', order_id)
                    return

                logger.info("Worker placing scheduled order id=%s for %s", order.id, order.stock_symbol)
                try:
                    place_order(session, order)
                except Exception:
                    logger.exception("Failed to place order %s in worker", order.id)
            finally:
                try:
                    session.close()
                except Exception:
                    pass
    except Exception:
        logger.exception('Unhandled exception in order worker for order %s', order_id)


def place_pending_orders(app, session_maker):
    """Find pending orders scheduled <= now and submit them to executor for background processing."""
    with app.app_context():
        session = session_maker()
        try:
            # Get current time in IST (same timezone as stored scheduled_time)
            ist = ZoneInfo('Asia/Kolkata')
            now_ist = datetime.now(ist).replace(tzinfo=None)

            # Fetch a small ordered batch of pending orders and submit each to executor by id
            pending = session.query(ScheduledOrder).filter(
                ScheduledOrder.status == "pending",
                ScheduledOrder.scheduled_time <= now_ist,
            ).order_by(ScheduledOrder.scheduled_time.asc()).limit(BATCH_SIZE).all()

            if not pending:
                return

            for order in pending:
                logger.info("Submitting scheduled order id=%s for %s to executor", order.id, order.stock_symbol)
                try:
                    # Submit the background worker with order id so each worker uses its own session
                    executor.submit(_process_order_worker, app, session_maker, order.id)
                except Exception:
                    logger.exception("Failed to submit order %s to executor", order.id)
        finally:
            try:
                session.close()
            except Exception:
                pass


def start_scheduler(app, session_maker):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: place_pending_orders(app, session_maker),
        'interval',
        seconds=POLL_INTERVAL_SECONDS,
        id='place_pending_orders',
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
