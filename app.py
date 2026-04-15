"""
Crypto Grid Bot — Flask dashboard
Port 5566
"""
import os
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=True)

from grid_engine import engine
import coinbase_api as cb

app = Flask(__name__)

# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    return jsonify(engine.get_status())

@app.route("/api/price")
def api_price():
    try:
        product = request.args.get("product", "BTC-USD")
        data = cb.get_price(product)
        return jsonify(data or {})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/balance")
def api_balance():
    try:
        usd = cb.get_balance("USD")
        btc = cb.get_crypto_balance("BTC")
        price = cb.get_price("BTC-USD")
        mid = price["mid"] if price else 0
        return jsonify({"usd": round(usd, 2), "btc": round(btc, 8),
                        "btc_usd": round(btc * mid, 2), "total_usd": round(usd + btc * mid, 2)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.json or {}
    settings = {}
    for key in ("lower", "upper", "num_grids", "order_size"):
        if key in data:
            settings[key] = float(data[key])
    if "paper_trading" in data:
        settings["paper_trading"] = bool(data["paper_trading"])
    if "product_id" in data:
        settings["product_id"] = data["product_id"]
    engine.start(settings)
    return jsonify({"ok": True})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    engine.stop()
    return jsonify({"ok": True})

@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.json or {}
    for key in ("lower", "upper", "num_grids", "order_size"):
        if key in data:
            engine.settings[key] = float(data[key])
    if "paper_trading" in data:
        engine.settings["paper_trading"] = bool(data["paper_trading"])
    return jsonify({"ok": True, "settings": engine.settings})

if __name__ == "__main__":
    print("  ₿  Crypto Grid Bot")
    print("  🌐 http://localhost:5566")
    app.run(host="127.0.0.1", port=5566, debug=False)
