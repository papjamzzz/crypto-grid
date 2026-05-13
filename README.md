<p align="center">
  <img src="static/logo.png" width="120" alt="Crypto Grid logo"/>
</p>

# Crypto Grid — Autonomous Grid Trading Bot

> **The factory without lights. Crypto edition.**

A self-running grid trading bot for BTC-USD on Coinbase. Places a ladder of buy/sell limit orders across a price range. Every round trip locks in profit. Runs 24/7 on Railway.

---

## How Grid Trading Works

```
Price range: $74,000 – $76,000
Grid levels: 40 (one order every $50)
  ↓
Bot places limit BUYs at every grid below market price
  ↓
Price dips → BUY fills → counter SELL placed $50 above
  ↓
Price recovers → SELL fills → profit locked in
  ↓
Repeat indefinitely. No emotion. No fatigue.
```

---

## Features

- **Autonomous execution** — set range, grids, and size once. Bot runs forever.
- **Live Coinbase integration** — JWT-authenticated Coinbase Advanced Trade API
- **Paper mode** — safe default. Simulates fills against live price without real orders.
- **Real-time dashboard** — P&L tracker, fill log, active grid visualization
- **Railway-deployed** — always on, no local machine required
- **Self-adjusting** — monitors fill state and replaces completed levels

---

## Dashboard

| Section | What It Shows |
|---------|--------------|
| Grid map | All active buy/sell levels, current price overlay |
| P&L tracker | Running profit from completed round trips |
| Fill log | Every BUY and SELL that hit, with price and time |
| Settings panel | Adjust range, grids, and order size mid-session |

---

## Configuration

| Setting | Default | What It Does |
|---------|---------|-------------|
| Price range | $74k–$76k | Upper and lower bounds of the grid |
| Grid levels | 40 | Number of buy/sell price steps |
| Order size | 0.00005 BTC | Size per grid level |
| Paper mode | ON | Simulate fills without real money |

---

## Stack

Python · Flask · Coinbase Advanced Trade API · SQLite · Vanilla JS · Railway

---

## Setup

```bash
git clone https://github.com/papjamzzz/crypto-grid.git
cd crypto-grid
cp .env.example .env
# Add COINBASE_API_KEY_NAME and COINBASE_PRIVATE_KEY to .env
python app.py
```

---

## Part of Creative Konsoles

Built by [Creative Konsoles](https://creativekonsoles.com) — tools built using thought.

**[creativekonsoles.com](https://creativekonsoles.com)** &nbsp;·&nbsp; support@creativekonsoles.com

<!-- repo maintenance: 2026-05-12 -->
