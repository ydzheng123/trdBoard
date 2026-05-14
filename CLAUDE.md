# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project has two parts:
1. **`market_data.py`** — standalone script for ad-hoc SDK queries
2. **`app.py` + `templates/index.html`** — Flask web app: a live market dashboard (行情看板)

## Environment Setup

Credentials are loaded from `.env` (copy from `.env.example`):

```
FUBON_ACCOUNT=身分證字號
FUBON_PASSWORD=證券登入密碼
FUBON_CERT_PATH=./憑證檔名.pfx
FUBON_CERT_PASSWORD=憑證密碼
```

The virtual environment is at `.venv`.

```bash
source .venv/bin/activate
python app.py          # start the dashboard at http://127.0.0.1:8080
python market_data.py  # run standalone script
```

Port 5000 is occupied by macOS AirPlay; the app runs on **8080**.

## Web App Architecture (`app.py`)

Single-user Flask app. Login state is held in a Flask session; the SDK instance and account object are globals (`_sdk`, `_account`).

**Routes:**
| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Serve dashboard HTML |
| `/api/login` | POST | Login — takes `{"password": "..."}`, reads account/cert from env |
| `/api/logout` | POST | Logout and clear session |
| `/api/status` | GET | Check if session is still active |
| `/api/market` | GET | Return market data; accepts `?symbols=2330,0050` |

**`/api/market` response shape:**
```json
{
  "taiex": { "price": 41374, "change": -523, "change_pct": -1.25, "open": ..., "high": ..., "low": ..., "time": "13:30:00" },
  "stocks": [
    {
      "symbol": "2330", "name": "台積電",
      "price": 2220, "change": -35, "change_pct": -1.55,
      "open": 2250, "bid": 2220, "ask": 2225, "volume": 35237,
      "odd": { "price": 2220, "change": -35, "change_pct": -1.55, "volume": 54010 }
    }
  ]
}
```

**Key helper functions:**
- `get_taiex()` — fetches TAIEX index from TWSE public API (`mis.twse.com.tw`)
- `get_stock_quote(symbol)` — queries both regular (`Common`) and intraday odd lot (`IntradayOdd`) via Fubon SDK; odd lot result is nested under `"odd"`
- `get_stock_name(symbol)` — fetches name from TWSE API (tries `tse` then `otc`); results are cached in `_name_cache` for the process lifetime

## Dashboard Frontend (`templates/index.html`)

Single-page app, no build step. Uses Tailwind CSS via CDN.

**Login screen:** password-only input (account/cert from env). Enter key submits.

**Dashboard table columns:** 代號 (editable) | 名稱 | 成交價 | 漲跌 | 成交量 | 開盤 | 委買 | 委賣 | 零股成交價 | 零股漲跌 | 零股成交量

**Behaviour:**
- 7 stock rows (r0–r6); first two default to 2330 and 0050
- Symbol inputs are editable; Enter or clicking Refresh fetches new data
- Watchlist persisted in `localStorage` — symbols survive page reload
- Auto-refresh every **15 seconds** while the tab is in the foreground; pauses via Page Visibility API when the tab is hidden
- Clearing a symbol input and refreshing clears that row's data

**JS key functions:**
- `fetchMarket()` — reads all non-empty `.sym-input` values, calls `/api/market?symbols=...`
- `updateDashboard(data)` — maps API response to table rows by index; clears empty rows
- `setChangeCell(id, change, pct)` — renders change + `(pct%)` on two lines using `innerHTML`
- `saveSymbols()` / `loadSymbols()` — `localStorage` persistence

## SDK Architecture

All functionality flows through `FubonSDK`:

```python
from fubon_neo.sdk import FubonSDK, Order, Mode
from fubon_neo.constant import BSAction, MarketType, PriceType, TimeInForce, OrderType

sdk = FubonSDK()
accounts = sdk.login(account, password, cert_path, cert_password)
account = accounts.data[0]
```

**Three main modules after login:**
- `sdk.stock` — REST API for stock queries and order management
- `sdk.accounting` — account balances, P&L, settlement
- `sdk.futopt` — futures and options

**Key API distinction:**

| Method | Purpose | Signature |
|--------|---------|-----------|
| `sdk.stock.query_symbol_quote` | Single stock quote | `(account, symbol, market_type=None)` |
| `sdk.stock.query_symbol_snapshot` | All stocks in a market | `(account, market_type=None, stock_types=None)` |

Pass `MarketType.IntradayOdd` as `market_type` to get intraday odd lot data.

## Enum Reference

- **`MarketType`**: `Common`, `Emg`, `IntradayOdd`, `Odd`, `EmgOdd`, `Fixing`
- **`PriceType`**: `Limit`, `Market`, `LimitUp`, `LimitDown`, `Reference`
- **`TimeInForce`**: `ROD`, `IOC`, `FOK`
- **`OrderType`**: `Stock`, `Margin`, `Short`, `DayTrade`, `SBL`
- **`BSAction`**: `Buy`, `Sell`

## Logs

Runtime logs are written to `./log/` with date suffixes (`program.log.YYYYMMDD`, `client.log.YYYYMMDD`, `notify.log.YYYYMMDD`). Logs are base64-encoded internally by the SDK.
