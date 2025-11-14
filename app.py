from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from config import DATABASE_URL
from models import db, KiteUser, ScheduledOrder, ScheduledOrderLog, ScheduledOrderBulkAudit, Admin
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from scheduler import start_scheduler, place_order
from kiteconnect import KiteConnect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from functools import wraps
import os

# Allowed stock list (symbol -> metadata)
ALLOWED_STOCKS = [
    {"symbol": "AXISBANK", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "SBIN", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "BHARTIARTL", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "HCLTECH", "percentage": "1.1339", "leverage": "4.92x"},
    {"symbol": "CIPLA", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "TRENT", "percentage": "0.8722", "leverage": "3.78x"},
    {"symbol": "SBILIFE", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "SHRIRAMFIN", "percentage": "0.9342", "leverage": "4.05x"},
    {"symbol": "ADANIENT", "percentage": "0.8263", "leverage": "3.58x"},
    {"symbol": "TITAN", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "TECHM", "percentage": "1.1178", "leverage": "4.85x"},
    {"symbol": "TATACONSUM", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "JSWSTEEL", "percentage": "1.1247", "leverage": "4.88x"},
    {"symbol": "DRREDDY", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "ADANIPORTS", "percentage": "0.9457", "leverage": "4.1x"},
    {"symbol": "HINDALCO", "percentage": "1.0443", "leverage": "4.53x"},
    {"symbol": "TATASTEEL", "percentage": "1.0512", "leverage": "4.56x"},
    {"symbol": "BAJFINANCE", "percentage": "1.1017", "leverage": "4.78x"},
    {"symbol": "BAJAJFINSV", "percentage": "1.1453", "leverage": "4.97x"},
    {"symbol": "BEL", "percentage": "0.9824", "leverage": "4.26x"},
    {"symbol": "SUNPHARMA", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "ICICIBANK", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "TATAMOTORS", "percentage": "1.0283", "leverage": "4.46x"},
    {"symbol": "NESTLEIND", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "ONGC", "percentage": "1.0535", "leverage": "4.57x"},
    {"symbol": "APOLLOHOSP", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "COALINDIA", "percentage": "1.1293", "leverage": "4.9x"},
    {"symbol": "GRASIM", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "POWERGRID", "percentage": "1.1224", "leverage": "4.87x"},
    {"symbol": "HDFCLIFE", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "RELIANCE", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "M&M", "percentage": "1.0535", "leverage": "4.57x"},
    {"symbol": "ITC", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "WIPRO", "percentage": "1.104", "leverage": "4.79x"},
    {"symbol": "NTPC", "percentage": "1.1247", "leverage": "4.88x"},
    {"symbol": "INFY", "percentage": "1.1407", "leverage": "4.95x"},
    {"symbol": "LT", "percentage": "1.1453", "leverage": "4.97x"},
    {"symbol": "INDUSINDBK", "percentage": "0.8401", "leverage": "3.64x"},
    {"symbol": "HDFCBANK", "percentage": "1.1522", "leverage": "5x"},
    {"symbol": "ETERNAL", "percentage": "0.8585", "leverage": "3.72x"},
    {"symbol": "JIOFIN", "percentage": "0.9985", "leverage": "4.33x"},
    {"symbol": "IDEA", "percentage": "0.443", "leverage": "2x"},
]
ALLOWED_SYMBOLS = {s["symbol"] for s in ALLOWED_STOCKS}


def create_app():
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['KITE_CALLBACK_URL'] = os.environ.get('KITE_CALLBACK_URL', 'http://localhost:5000/kite/callback')
    db.init_app(app)

    # create DB
    with app.app_context():
        db.create_all()
        
        # Auto-create default admin from env vars if not exists
        from config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
        if DEFAULT_ADMIN_USERNAME and DEFAULT_ADMIN_PASSWORD:
            existing = Admin.query.filter_by(
                username=DEFAULT_ADMIN_USERNAME
            ).first()
            if not existing:
                admin = Admin(username=DEFAULT_ADMIN_USERNAME)
                admin.set_password(DEFAULT_ADMIN_PASSWORD)
                db.session.add(admin)
                db.session.commit()
                print(f"[INFO] Default admin '{DEFAULT_ADMIN_USERNAME}' created from environment variables")

    # session maker for scheduler
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)

    # start scheduler
    start_scheduler(app, Session)

    # Admin session protection decorator
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_id' not in session:
                flash('Please login as admin first', 'error')
                return redirect(url_for('admin_login'))
            return f(*args, **kwargs)
        return decorated_function

    # Admin login route
    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            admin = Admin.query.filter_by(username=username).first()
            if admin and admin.check_password(password):
                session['admin_id'] = admin.id
                session['admin_username'] = admin.username
                flash(
                    f'Welcome, {admin.username}!', 'success'
                )
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('admin_login.html')

    # Admin logout route
    @app.route('/admin/logout')
    def admin_logout():
        session.clear()
        flash('Logged out successfully', 'success')
        return redirect(url_for('admin_login'))

    # Admin creation UI route (for logged-in admins)
    @app.route('/admin/create', methods=['GET', 'POST'])
    @admin_required
    def admin_create():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            email = request.form.get('email', '')
            
            # Validate input
            if not username or not password:
                flash('Username and password are required', 'error')
                return redirect(url_for('admin_create'))
            
            # Check if admin already exists
            existing = Admin.query.filter_by(username=username).first()
            if existing:
                flash(f'Admin "{username}" already exists', 'error')
                return redirect(url_for('admin_create'))
            
            # Create new admin
            try:
                admin = Admin(
                    username=username,
                    email=email or None
                )
                admin.set_password(password)
                db.session.add(admin)
                db.session.commit()
                flash(
                    f'Admin "{username}" created successfully',
                    'success'
                )
                return redirect(url_for('admin_create'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating admin: {str(e)}', 'error')
                return redirect(url_for('admin_create'))
        
        # GET request - show form with list of existing admins
        admins = Admin.query.order_by(Admin.created_at.desc()).all()
        return render_template('admin_create.html', admins=admins)

    @app.route('/users', methods=['POST'])
    def create_user():
        data = request.json or {}
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')
        if not api_key or not api_secret:
            return jsonify({"error": "api_key and api_secret required"}), 400
        user = KiteUser(api_key=api_key, api_secret=api_secret)
        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "api_key already exists"}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
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
    
    @app.route('/')
    def index():
        return redirect(url_for('dashboard'))


    # Dashboard views
    @app.route('/dashboard')
    @admin_required
    def dashboard():
        users = KiteUser.query.order_by(KiteUser.created_at.desc()).all()
        orders = ScheduledOrder.query.order_by(ScheduledOrder.scheduled_time.asc()).all()
        ist = ZoneInfo('Asia/Kolkata')
        now = datetime.now(ist).replace(tzinfo=None)

        # Attach an IST-formatted expiry string to each user for display
        for u in users:
            u.token_expiry_ist = None
            if u.token_expiry:
                try:
                    # token_expiry is stored as naive UTC; treat it as UTC then convert
                    dt_utc = u.token_expiry.replace(tzinfo=ZoneInfo('UTC'))
                    dt_ist = dt_utc.astimezone(ist)
                    u.token_expiry_ist = dt_ist.strftime('%Y-%m-%d %H:%M:%S %Z')
                except Exception:
                    u.token_expiry_ist = None

        # fetch recent logs for display
        logs = ScheduledOrderLog.query.order_by(ScheduledOrderLog.created_at.desc()).limit(50).all()
        for log_entry in logs:
            try:
                dt_utc = log_entry.created_at.replace(tzinfo=ZoneInfo('UTC'))
                dt_ist = dt_utc.astimezone(ZoneInfo('Asia/Kolkata'))
                log_entry.created_at_ist = dt_ist.strftime('%Y-%m-%d %H:%M:%S %Z')
            except Exception:
                log_entry.created_at_ist = None

        return render_template(
            'dashboard.html',
            users=users,
            orders=orders,
            logs=logs,
            now=now,
            allowed_stocks=ALLOWED_STOCKS,
        )

    @app.route('/dashboard/user/<int:user_id>')
    def user_profile(user_id: int):
        user = KiteUser.query.get_or_404(user_id)
        ist = ZoneInfo('Asia/Kolkata')
        now = datetime.now(ist).replace(tzinfo=None)
        return render_template('user_profile.html', user=user, now=now)

    @app.route('/dashboard/user/<int:user_id>/update', methods=['POST'])
    def update_user(user_id: int):
        user = KiteUser.query.get_or_404(user_id)
        
        # Update API Key
        api_key = request.form.get('api_key')
        if api_key and api_key != user.api_key:
            user.api_key = api_key
            # Clear access token since API key changed
            user.access_token = None
            user.token_expiry = None
        
        # Update API Secret if provided
        api_secret = request.form.get('api_secret')
        if api_secret:
            user.api_secret = api_secret
            # Clear access token since API secret changed
            user.access_token = None
            user.token_expiry = None
        
        try:
            db.session.commit()
            flash('User information updated successfully', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('A user with this API key already exists (first 4 chars: ' + (api_key[:4] if api_key else '') + ').', 'error')
        except Exception as e:
            db.session.rollback()
            flash('Error updating user: ' + str(e), 'error')
        return redirect(url_for('user_profile', user_id=user_id))

    @app.route('/logs')
    @admin_required
    def logs_view():
        # filters: user_id, scheduled_order_id, status, q (search message)
        per_page = 20
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1

        query = ScheduledOrderLog.query.order_by(
            ScheduledOrderLog.created_at.desc()
        )
        user_id = request.args.get('user_id')
        soid = request.args.get('scheduled_order_id')
        status = request.args.get('status')
        q = request.args.get('q')
        if user_id:
            try:
                uid = int(user_id)
                query = query.filter(ScheduledOrderLog.user_id == uid)
            except Exception:
                pass
        if soid:
            try:
                sid = int(soid)
                query = query.filter(ScheduledOrderLog.scheduled_order_id == sid)
            except Exception:
                pass
        if status:
            query = query.filter(
                ScheduledOrderLog.status.ilike(f"%{status}%")
            )
        if q:
            query = query.filter(
                ScheduledOrderLog.message.ilike(f"%{q}%")
            )

        total_count = query.count()
        total_pages = (total_count + per_page - 1) // per_page
        if page > total_pages and total_pages > 0:
            page = total_pages

        logs = query.offset((page - 1) * per_page).limit(per_page).all()
        # attach IST formatted created time
        ist = ZoneInfo('Asia/Kolkata')
        for entry in logs:
            try:
                dt_utc = entry.created_at.replace(tzinfo=ZoneInfo('UTC'))
                dt_ist = dt_utc.astimezone(ist)
                entry.created_at_ist = dt_ist.strftime(
                    '%Y-%m-%d %H:%M:%S %Z'
                )
            except Exception:
                entry.created_at_ist = None

        page_range = range(
            max(1, page - 2), min(total_pages + 1, page + 3)
        )

        return render_template(
            'logs.html',
            logs=logs,
            current_page=page,
            total_pages=total_pages,
            page_range=page_range,
        )

    @app.route('/dashboard/users/create', methods=['POST'])
    def dashboard_create_user():
        api_key = request.form.get('api_key')
        api_secret = request.form.get('api_secret')
        if not api_key or not api_secret:
            flash('api_key and api_secret are required', 'error')
            return redirect(url_for('dashboard'))
        user = KiteUser(api_key=api_key, api_secret=api_secret)
        try:
            db.session.add(user)
            db.session.commit()
            flash('User created. Please login with Kite to complete setup.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('A user with this API key already exists (first 4 chars: ' + (api_key[:4] if api_key else '') + ').', 'error')
        except Exception as e:
            db.session.rollback()
            flash('Error creating user: ' + str(e), 'error')
        return redirect(url_for('dashboard'))


    @app.route('/dashboard/users/<int:user_id>/login')
    def kite_login(user_id):
        user = KiteUser.query.get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Store user_id in session for callback
        session['kite_login_user_id'] = user_id
        
        # Create login URL
        kite = KiteConnect(api_key=user.api_key)
        login_url = f"https://kite.zerodha.com/connect/login?api_key={user.api_key}&v=3"
        return redirect(login_url)

    @app.route('/kite/callback')
    def kite_callback():
        user_id = session.get('kite_login_user_id')
        if not user_id:
            flash('No active login session', 'error')
            return redirect(url_for('dashboard'))
        
        user = KiteUser.query.get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard'))

        request_token = request.args.get('request_token')
        if not request_token:
            flash('No request token received', 'error')
            return redirect(url_for('dashboard'))

        try:
            # Exchange request token for access token
            kite = KiteConnect(api_key=user.api_key)
            data = kite.generate_session(request_token, api_secret=user.api_secret)
            access_token = data.get('access_token')
            
            if access_token:
                # Get user profile from Kite
                kite.set_access_token(access_token)
                profile = kite.profile()
                
                # Calculate token expiry as next 06:00 IST, and store as UTC naive datetime
                ist = ZoneInfo('Asia/Kolkata')
                now_ist = datetime.now(tz=ist)
                expiry_ist = now_ist.replace(hour=6, minute=0, second=0, microsecond=0)
                if now_ist.hour >= 6:
                    expiry_ist = expiry_ist + timedelta(days=1)
                # convert to UTC and store as naive UTC datetime for comparison with utcnow()
                expiry_utc = expiry_ist.astimezone(ZoneInfo('UTC')).replace(tzinfo=None)
                expiry = expiry_utc
                
                # Update user with profile data
                user.access_token = access_token
                user.token_expiry = expiry
                user.token_set_at = datetime.now(ist).replace(tzinfo=None)
                user.user_id = str(profile.get('user_id'))
                user.email = profile.get('email')
                user.user_name = profile.get('user_name')
                user.user_shortname = profile.get('user_shortname')
                user.broker = profile.get('broker')
                user.exchanges = ','.join(profile.get('exchanges', []))
                user.products = ','.join(profile.get('products', []))
                user.order_types = ','.join(profile.get('order_types', []))
                user.avatar_url = profile.get('avatar_url')
                
                db.session.add(user)
                db.session.commit()
                flash('Successfully logged in to Kite', 'success')
            else:
                flash('No access token received', 'error')
        except Exception as e:
            flash(f'Failed to get access token: {str(e)}', 'error')
        
        return redirect(url_for('dashboard'))

    @app.route('/dashboard/orders/create', methods=['POST'])
    @admin_required
    def dashboard_create_order():
        try:
            stock_symbol = request.form.get('stock_symbol')
            quantity = int(request.form.get('quantity'))
            order_type = request.form.get('order_type')
            scheduled_time = request.form.get('scheduled_time')  # HH:MM:SS (time-only with seconds)

            # Validate stock symbol is allowed
            if not stock_symbol or stock_symbol not in ALLOWED_SYMBOLS:
                flash('Invalid stock symbol selected. Please choose from the allowed list.', 'error')
                return redirect(url_for('dashboard'))

            if not scheduled_time:
                flash('scheduled_time is required', 'error')
                return redirect(url_for('dashboard'))

            # Parse time (HH:MM:SS) and build datetime in IST
            ist = ZoneInfo('Asia/Kolkata')
            now_ist = datetime.now(ist)
            time_parts = scheduled_time.split(':')
            hh = int(time_parts[0])
            mm = int(time_parts[1])
            ss = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            # Store as IST datetime (naive - the DB will store it as IST)
            dt = now_ist.replace(
                hour=hh, minute=mm, second=ss, microsecond=0, tzinfo=None
            )

            # Ensure same-day scheduling (in IST)
            if dt.date() != now_ist.date():
                flash('Scheduled orders must be for today only', 'error')
                return redirect(url_for('dashboard'))

            # Check if order is scheduled in the past (in IST)
            if dt <= now_ist.replace(tzinfo=None):
                flash('Cannot schedule orders in the past', 'error')
                return redirect(url_for('dashboard'))

            # Validate trading hours (09:30 - 15:30)
            time_float = hh + mm / 60 + ss / 3600
            if time_float < 9.5 or time_float > 15.5:
                flash('Orders can only be scheduled between 09:30 and 15:30', 'error')
                return redirect(url_for('dashboard'))
                
        except Exception as e:
            flash(f'Invalid order input: {str(e)}', 'error')
            return redirect(url_for('dashboard'))
        # Create the same scheduled order for all users in the system
        # Prepare audit record for this bulk schedule
        audit = ScheduledOrderBulkAudit(
            initiator=None,
            stock_symbol=stock_symbol,
            quantity=quantity,
            order_type=(order_type or '').lower(),
            scheduled_time=dt,
        )
        db.session.add(audit)
        db.session.flush()

        # Only schedule for users with valid tokens (non-null access_token and non-expired)
        users = KiteUser.query.filter(
            KiteUser.access_token.isnot(None),
            KiteUser.token_expiry.isnot(None),
            KiteUser.token_expiry > datetime.now(ZoneInfo('UTC')).replace(tzinfo=None),
        ).all()
        audit.users_targeted = len(users)
        db.session.add(audit)
        db.session.flush()
        if not users:
            flash('No users available to schedule orders for', 'error')
            return redirect(url_for('dashboard'))

        created = 0
        for u in users:
            order = ScheduledOrder(
                user_id=u.id,
                stock_symbol=stock_symbol,
                quantity=quantity,
                order_type=(order_type or '').lower(),
                scheduled_time=dt,
            )
            db.session.add(order)
            db.session.flush()  # ensure order.id is populated

            # create initial log entry for this scheduled order
            log = ScheduledOrderLog(
                scheduled_order_id=order.id,
                user_id=u.id,
                status='scheduled',
                message='Created via dashboard bulk schedule',
            )
            db.session.add(log)
            created += 1

        # update audit with created count
        audit.users_created = created
        audit.message = f'Created orders for {created} users'
        db.session.add(audit)
        db.session.commit()
        flash(f'Order scheduled for {created} users', 'success')
        return redirect(url_for('dashboard'))


    # Health check
    @app.route('/health')
    def health_check():
        status = {'status': 'ok'}
        try:
            # quick DB ping
            db.session.execute('SELECT 1')
            pending = ScheduledOrder.query.filter(ScheduledOrder.status == 'pending').count()
            status['db'] = 'ok'
            status['pending_orders'] = pending
        except Exception as e:
            status['db'] = 'error'
            status['error'] = str(e)
        return jsonify(status)


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
