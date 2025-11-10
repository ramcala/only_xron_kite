# only_cron_kite

Simple Flask API to store Kite (Zerodha) credentials and schedule orders to be placed at a given time.

Features
- Store Kite user credentials (api_key, api_secret, access_token)
- Schedule buy/sell orders for a stock at a given datetime
- Background scheduler checks pending orders and places them via KiteConnect (or simulates if credentials missing)

Quick start

1. Create a virtual environment and install dependencies:

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Export environment variables (optional):

# If using real Kite account, set KITE_ENABLE_REAL=true
```
setx KITE_ENABLE_REAL "false"
```

3. Run the app:

```pwsh
python app.py
```

API Endpoints
- POST /users - create a Kite user record (body: api_key, api_secret, access_token optional)
- GET /users - list users
- POST /orders - schedule an order (user_id, stock_symbol, quantity, order_type (buy|sell), scheduled_time ISO)
- GET /orders - list scheduled orders
- POST /orders/<id>/place - try to place a scheduled order immediately

Notes
- This is a minimal example. When connecting to real Kite endpoints, ensure secure handling of secrets and tokens.
- The scheduler runs in-process using APScheduler and checks every minute for pending orders.
