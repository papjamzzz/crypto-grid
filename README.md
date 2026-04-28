# Crypto Grid — Autonomous Grid Trading Bot

**Self-adjusting buy/sell grid engine. Runs 24/7. Factory without lights.**

Crypto Grid is an autonomous trading bot that deploys a dynamic grid strategy across crypto markets. It places layered buy and sell orders at calculated intervals, captures spread on volatility, and adjusts the grid as price moves — without manual intervention.

---

## How It Works

1. **Grid deployment** — places N buy orders below current price, N sell orders above
2. **Fill detection** — monitors for filled orders in real time
3. **Auto-reorder** — when a sell fills, places a new buy below; when a buy fills, places a new sell above
4. **P&L tracking** — live realized and unrealized profit display
5. **Risk controls** — configurable max drawdown, grid spacing, and position size limits

## Stack

```
Python · Flask · Vanilla JS
Railway (24/7 cloud deployment)
```

## Run Locally

```bash
pip install -r requirements.txt
cp .env.example .env  # add exchange API keys
python app.py
```

## Configuration

| Parameter | Description |
|-----------|-------------|
| `GRID_LEVELS` | Number of buy/sell levels on each side |
| `GRID_SPACING` | % distance between grid levels |
| `POSITION_SIZE` | Base order size per level |
| `MAX_DRAWDOWN` | Stop threshold — halts bot if breached |

---

*A Creative Konsoles project. Use at your own risk — automated trading involves significant financial risk.*
