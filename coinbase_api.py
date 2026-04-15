"""
Coinbase Advanced Trade API — JWT auth + REST calls
"""
import os, time, json, requests
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import jwt as pyjwt

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=True)

API_BASE = "https://api.coinbase.com"

def _get_credentials():
    key    = os.getenv("COINBASE_API_KEY", "")
    secret = os.getenv("COINBASE_API_SECRET", "")
    # dotenv stores \n as literal backslash+n (0x5c 0x6e) — convert to real newlines
    secret = secret.encode().replace(b'\x5c\x6e', b'\x0a').decode()
    if not secret.endswith('\n'):
        secret += '\n'
    return key, secret

def _make_jwt(method, path):
    key_name, secret_pem = _get_credentials()
    private_key = serialization.load_pem_private_key(
        secret_pem.encode(), password=None, backend=default_backend()
    )
    payload = {
        "sub":  key_name,
        "iss":  "coinbase-cloud",
        "nbf":  int(time.time()),
        "exp":  int(time.time()) + 120,
        "iat":  int(time.time()),
        "uri":  f"{method} api.coinbase.com{path}",
    }
    token = pyjwt.encode(payload, private_key, algorithm="ES256",
                         headers={"kid": key_name, "nonce": str(int(time.time()*1000))})
    return token

def _get(path, params=None):
    token = _make_jwt("GET", path)
    r = requests.get(f"{API_BASE}{path}", headers={"Authorization": f"Bearer {token}"},
                     params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def _post(path, body):
    token = _make_jwt("POST", path)
    r = requests.post(f"{API_BASE}{path}", headers={"Authorization": f"Bearer {token}",
                      "Content-Type": "application/json"},
                      data=json.dumps(body), timeout=10)
    r.raise_for_status()
    return r.json()

def _delete(path):
    token = _make_jwt("DELETE", path)
    r = requests.delete(f"{API_BASE}{path}", headers={"Authorization": f"Bearer {token}"},
                        timeout=10)
    r.raise_for_status()
    return r.json()

# ── Market data ───────────────────────────────────────────────────────────────

def get_price(product_id="BTC-USD"):
    """Return best bid, ask, and mid for a product."""
    data = _get(f"/api/v3/brokerage/best_bid_ask", params={"product_ids": product_id})
    for entry in data.get("pricebooks", []):
        if entry.get("product_id") == product_id:
            bid = float(entry["bids"][0]["price"]) if entry.get("bids") else 0
            ask = float(entry["asks"][0]["price"]) if entry.get("asks") else 0
            return {"bid": bid, "ask": ask, "mid": round((bid + ask) / 2, 2)}
    return None

def get_accounts():
    data = _get("/api/v3/brokerage/accounts")
    return data.get("accounts", [])

def get_balance(currency="USD"):
    for acct in get_accounts():
        if acct.get("currency") == currency:
            return float(acct.get("available_balance", {}).get("value", 0))
    return 0.0

def get_crypto_balance(currency="BTC"):
    for acct in get_accounts():
        if acct.get("currency") == currency:
            return float(acct.get("available_balance", {}).get("value", 0))
    return 0.0

# ── Order management ──────────────────────────────────────────────────────────

def place_limit_order(product_id, side, size, limit_price, client_order_id=None):
    """Place a limit order. side = 'BUY' or 'SELL'. size in base currency (BTC)."""
    import uuid
    body = {
        "client_order_id": client_order_id or str(uuid.uuid4()),
        "product_id":      product_id,
        "side":            side,
        "order_configuration": {
            "limit_limit_gtc": {
                "base_size":   str(round(size, 8)),
                "limit_price": str(round(limit_price, 2)),
                "post_only":   True,   # maker-only = 0% fee tier eligible
            }
        }
    }
    return _post("/api/v3/brokerage/orders", body)

def cancel_orders(order_ids):
    """Cancel a list of order IDs."""
    if not order_ids:
        return
    return _post("/api/v3/brokerage/orders/batch_cancel", {"order_ids": order_ids})

def list_open_orders(product_id="BTC-USD"):
    data = _get("/api/v3/brokerage/orders/historical/batch",
                params={"product_id": product_id, "order_status": "OPEN"})
    return data.get("orders", [])

def get_order(order_id):
    return _get(f"/api/v3/brokerage/orders/historical/{order_id}")
