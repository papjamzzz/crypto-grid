"""
Grid Engine — places and manages a grid of limit orders on Coinbase.

Strategy:
  - Divide price range into N equal levels
  - Place BUY limit at every level below current price
  - Place SELL limit at every level above current price
  - When a BUY fills → place SELL one level up
  - When a SELL fills → place BUY one level down
  - Each round trip = grid_spacing profit (minus fees)

Paper trading mode: simulates fills against live price, no real orders.
"""

import os, time, json, threading, uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=True)

import coinbase_api as cb

TRADES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "trades.json")
STATE_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "grid_state.json")

os.makedirs(os.path.dirname(TRADES_FILE), exist_ok=True)

# ── Default grid settings ─────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "product_id":    "BTC-USD",
    "lower":         74000.0,    # bottom of grid
    "upper":         76000.0,    # top of grid
    "num_grids":     40,         # number of grid lines → $50 spacing
    "order_size":    0.00005,    # BTC per order (~$3.74 at $74k) — 11 active levels on $42
    "paper_trading": True,       # ALWAYS start in paper mode
}

class GridEngine:
    def __init__(self):
        self._lock     = threading.Lock()
        self.settings  = dict(DEFAULT_SETTINGS)
        self.running   = False
        self._thread   = None
        self._status   = "Idle"
        self._last_price = None
        self._grid_levels = []     # sorted list of price levels
        self._orders   = {}        # level_price → {order_id, side, status, fill_price, pnl}
        self._trades   = self._load_trades()
        self._total_pnl   = 0.0
        self._total_fills = 0
        self._wins     = 0
        self._losses   = 0
        self._last_error = None
        self._price_history = []   # (timestamp, price) last 200 points for chart

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_trades(self):
        if os.path.exists(TRADES_FILE):
            try:
                with open(TRADES_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_trades(self):
        with open(TRADES_FILE, "w") as f:
            json.dump(self._trades, f, indent=2)

    # ── Grid math ─────────────────────────────────────────────────────────────

    def _build_levels(self):
        lo   = self.settings["lower"]
        hi   = self.settings["upper"]
        n    = self.settings["num_grids"]
        step = (hi - lo) / n
        return [round(lo + i * step, 2) for i in range(int(n) + 1)]

    def _grid_spacing(self):
        lo = self.settings["lower"]
        hi = self.settings["upper"]
        n  = self.settings["num_grids"]
        return round((hi - lo) / n, 2)

    def _profit_per_trade(self):
        size    = self.settings["order_size"]
        spacing = self._grid_spacing()
        # Rough estimate: spacing * size, minus ~0.1% fees each side
        gross = spacing * size
        fees  = gross * 0.002   # 0.1% each side
        return round(gross - fees, 4)

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def start(self, settings=None):
        if settings:
            self.settings.update(settings)
        # Recover from zombie state: running=True but thread dead
        if self.running and self._thread and self._thread.is_alive():
            return
        self.running   = True
        self._status   = "Starting..."
        self._orders   = {}
        self._grid_levels = self._build_levels()
        self._thread   = threading.Thread(target=self._run_loop, daemon=True, name="grid-engine")
        self._thread.start()

    def stop(self):
        self.running = False
        self._status = "Stopped"
        if not self.settings["paper_trading"]:
            self._cancel_all_orders()

    def _cancel_all_orders(self):
        try:
            ids = [o["order_id"] for o in self._orders.values()
                   if o.get("order_id") and o.get("status") == "open"]
            if ids:
                cb.cancel_orders(ids)
                print(f"  🗑 Cancelled {len(ids)} open orders")
        except Exception as e:
            print(f"  ⚠ Cancel error: {e}")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run_loop(self):
        paper = self.settings["paper_trading"]
        print(f"  🤖 Grid Engine started {'[PAPER]' if paper else '[LIVE]'}")
        self._place_initial_grid()

        while self.running:
            try:
                price_data = cb.get_price(self.settings["product_id"])
                if not price_data:
                    time.sleep(5)
                    continue

                price = price_data["mid"]
                self._last_price = price

                # Store price history for chart (cap at 200)
                with self._lock:
                    self._price_history.append((datetime.now().isoformat(), price))
                    if len(self._price_history) > 200:
                        self._price_history.pop(0)

                if paper:
                    self._check_paper_fills(price)
                else:
                    self._check_live_fills(price)

                self._status = f"Running — BTC ${price:,.2f}"
                time.sleep(5)

            except Exception as e:
                self._last_error = str(e)[:120]
                self._status = f"Error: {self._last_error}"
                print(f"  ⚠ Grid loop error: {e}")
                time.sleep(10)

    # ── Grid placement ────────────────────────────────────────────────────────

    def _place_initial_grid(self):
        paper = self.settings["paper_trading"]
        price_data = cb.get_price(self.settings["product_id"])
        if not price_data:
            print("  ⚠ Could not fetch price for initial grid placement")
            return

        price  = price_data["mid"]
        levels = self._grid_levels
        size   = self.settings["order_size"]

        print(f"  📐 Placing grid: {len(levels)} levels | ${levels[0]:,.0f}–${levels[-1]:,.0f} | price=${price:,.2f}")

        for level in levels:
            if level < price:
                side = "BUY"
            elif level > price:
                side = "SELL"
            else:
                continue   # skip level exactly at price

            order_id = str(uuid.uuid4())
            order = {
                "order_id":    order_id,
                "level":       level,
                "side":        side,
                "size":        size,
                "status":      "open",
                "placed_at":   datetime.now().isoformat(),
                "fill_price":  None,
                "pnl":         None,
            }

            if not paper:
                try:
                    resp = cb.place_limit_order(
                        self.settings["product_id"], side, size, level,
                        client_order_id=order_id
                    )
                    order["order_id"] = (resp.get("order_id") or
                                         resp.get("success_response", {}).get("order_id", order_id))
                except Exception as e:
                    print(f"  ⚠ Order placement error at ${level}: {e}")
                    continue

            with self._lock:
                self._orders[level] = order

        print(f"  ✅ Grid live — {sum(1 for o in self._orders.values() if o['side']=='BUY')} buys, "
              f"{sum(1 for o in self._orders.values() if o['side']=='SELL')} sells")

    # ── Paper fill simulation ─────────────────────────────────────────────────

    def _check_paper_fills(self, price):
        """Simulate fills: BUY fills when price <= level, SELL fills when price >= level."""
        filled_levels = []

        with self._lock:
            for level, order in list(self._orders.items()):
                if order["status"] != "open":
                    continue
                side = order["side"]
                if side == "BUY"  and price <= level:
                    filled_levels.append((level, "BUY",  price))
                elif side == "SELL" and price >= level:
                    filled_levels.append((level, "SELL", price))

        for level, side, fill_price in filled_levels:
            self._handle_fill(level, side, fill_price, paper=True)

    def _check_live_fills(self, price):
        """Check actual Coinbase order statuses."""
        with self._lock:
            open_orders = {lv: o for lv, o in self._orders.items()
                           if o["status"] == "open" and o.get("order_id")}

        for level, order in open_orders.items():
            try:
                resp = cb.get_order(order["order_id"])
                status = resp.get("order", {}).get("status", "")
                if status == "FILLED":
                    fill_price = float(resp.get("order", {}).get("average_filled_price", level))
                    self._handle_fill(level, order["side"], fill_price, paper=False)
            except Exception:
                pass

    # ── Fill handler ──────────────────────────────────────────────────────────

    def _handle_fill(self, level, side, fill_price, paper):
        size    = self.settings["order_size"]
        spacing = self._grid_spacing()
        product = self.settings["product_id"]

        # Calculate P&L for completed round trips
        if side == "SELL":
            # Find the paired BUY level (one grid below)
            buy_level = round(level - spacing, 2)
            pnl = round((fill_price - buy_level) * size, 4)
        else:
            pnl = None   # BUY fill — P&L realised on the paired SELL

        with self._lock:
            if level in self._orders:
                self._orders[level]["status"]     = "filled"
                self._orders[level]["fill_price"] = fill_price
                self._orders[level]["filled_at"]  = datetime.now().isoformat()
                self._orders[level]["pnl"]        = pnl

            if pnl is not None:
                self._total_pnl   += pnl
                self._total_fills += 1
                if pnl >= 0:
                    self._wins += 1
                else:
                    self._losses += 1

        # Record trade
        trade = {
            "level":      level,
            "side":       side,
            "fill_price": fill_price,
            "size":       size,
            "pnl":        pnl,
            "time":       datetime.now().isoformat(),
            "paper":      paper,
        }
        self._trades.append(trade)
        self._save_trades()

        mode = "📋" if paper else ("🟢" if (pnl or 0) >= 0 else "🔴")
        pnl_str = f" | P&L ${pnl:+.4f}" if pnl is not None else ""
        print(f"  {mode} FILL: {side} {size} BTC @ ${fill_price:,.2f} (grid ${level:,.0f}){pnl_str}")

        # Place counter-order at the next level
        self._place_counter_order(level, side, paper)

    def _place_counter_order(self, filled_level, filled_side, paper):
        """After a fill, place the counter order one level away."""
        spacing = self._grid_spacing()
        size    = self.settings["order_size"]
        product = self.settings["product_id"]
        levels  = self._grid_levels

        if filled_side == "BUY":
            # BUY filled → place SELL one level up
            counter_level = round(filled_level + spacing, 2)
            counter_side  = "SELL"
        else:
            # SELL filled → place BUY one level down
            counter_level = round(filled_level - spacing, 2)
            counter_side  = "BUY"

        # Stay within grid bounds
        if counter_level < levels[0] or counter_level > levels[-1]:
            return

        order_id = str(uuid.uuid4())
        order = {
            "order_id":  order_id,
            "level":     counter_level,
            "side":      counter_side,
            "size":      size,
            "status":    "open",
            "placed_at": datetime.now().isoformat(),
            "fill_price": None,
            "pnl":       None,
        }

        if not paper:
            try:
                resp = cb.place_limit_order(product, counter_side, size, counter_level,
                                            client_order_id=order_id)
                order["order_id"] = (resp.get("order_id") or
                                     resp.get("success_response", {}).get("order_id", order_id))
            except Exception as e:
                print(f"  ⚠ Counter-order error at ${counter_level}: {e}")
                return

        with self._lock:
            self._orders[counter_level] = order

    # ── Status for dashboard ──────────────────────────────────────────────────

    def get_status(self):
        with self._lock:
            orders_snap    = dict(self._orders)
            price_hist     = list(self._price_history)
            trades_snap    = list(self._trades[-50:])  # last 50

        open_buys  = [o for o in orders_snap.values() if o["status"] == "open"  and o["side"] == "BUY"]
        open_sells = [o for o in orders_snap.values() if o["status"] == "open"  and o["side"] == "SELL"]
        fills      = [o for o in orders_snap.values() if o["status"] == "filled"]

        return {
            "running":       self.running,
            "paper_trading": self.settings["paper_trading"],
            "status_msg":    self._status,
            "product_id":    self.settings["product_id"],
            "last_price":    self._last_price,
            "settings":      dict(self.settings),
            "grid_levels":   self._grid_levels,
            "grid_spacing":  self._grid_spacing(),
            "profit_per_trade": self._profit_per_trade(),
            "open_buys":     len(open_buys),
            "open_sells":    len(open_sells),
            "total_fills":   self._total_fills,
            "total_pnl":     round(self._total_pnl, 4),
            "wins":          self._wins,
            "losses":        self._losses,
            "last_error":    self._last_error,
            "orders":        sorted(orders_snap.values(), key=lambda o: o["level"], reverse=True),
            "trades":        trades_snap,
            "price_history": price_hist,
        }

# ── Singleton ─────────────────────────────────────────────────────────────────
engine = GridEngine()
