# Crypto Grid Bot — CLAUDE.md

## Project
- **Folder:** ~/crypto-grid
- **Port:** 5566 (local) / Railway PORT (deployed)
- **GitHub:** papjamzzz/crypto-grid
- **Stack:** Python + Flask, Coinbase Advanced Trade API, JWT auth

## What It Does
Grid trading bot for BTC-USD (and future pairs). Places a ladder of limit buy/sell orders across a price range. Profits from price oscillation — each round trip (BUY filled → counter SELL filled) locks in grid_spacing × order_size profit.

## Current Settings (paper mode defaults)
- Range: $74,000 – $76,000
- Grids: 40 levels → $50 spacing
- Order size: 0.00005 BTC (~$3.74/order) — 11 active buy levels on $42
- Paper trading: always ON by default

## Key Files
- `app.py` — Flask routes, API endpoints
- `grid_engine.py` — GridEngine class, all trading logic, singleton `engine`
- `coinbase_api.py` — JWT auth + Coinbase REST calls
- `templates/index.html` — full dashboard UI
- `data/trades.json` — persisted trade history (gitignored)

## Architecture Notes
- `engine` is a module-level singleton — lives for the life of the Flask process
- `engine.start(settings)` launches a daemon thread (`_run_loop`)
- Paper fills simulated every 5s against live Coinbase price
- `num_grids` must be stored as `int` — `range()` requires it (bug fixed 2026-04-15)
- Zombie-running guard: `start()` checks `_thread.is_alive()` before bailing

## Environment Variables (Railway)
```
COINBASE_API_KEY=organizations/.../apiKeys/...
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----\n
```

## Deploy
- Railway: auto-deploys from GitHub main branch
- **Live URL:** https://web-production-3d00.up.railway.app
- PORT env var set automatically by Railway — app binds to it
- Local: `python app.py` → http://127.0.0.1:5566

## Re-Entry
Last session: Fixed "Starting..." stuck state (float num_grids bug), tightened grid to $50 spacing, deployed to Railway. Bot is in paper trading mode — accumulating round trips before going live.
