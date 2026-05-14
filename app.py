import os
import requests as http_requests
from flask import Flask, session, jsonify, request, render_template
from fubon_neo.sdk import FubonSDK
from fubon_neo.constant import MarketType

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Single-user global state
_sdk: FubonSDK | None = None
_account = None
_name_cache: dict[str, str] = {}


def load_env(path=".env"):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


load_env()


def get_taiex():
    try:
        r = http_requests.get(
            "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
            "?ex_ch=tse_t00.tw&json=1&delay=0",
            timeout=5,
        )
        msg = r.json()["msgArray"][0]
        prev_close = float(msg["y"])
        current = float(msg["z"]) if msg.get("z") else prev_close
        change = current - prev_close
        change_pct = change / prev_close * 100
        return {
            "name": msg["n"],
            "price": current,
            "prev_close": prev_close,
            "open": float(msg["o"]) if msg.get("o") else None,
            "high": float(msg["h"]) if msg.get("h") else None,
            "low": float(msg["l"]) if msg.get("l") else None,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "time": msg.get("t", ""),
        }
    except Exception as e:
        return {"error": str(e)}


def get_stock_name(symbol: str) -> str:
    if symbol in _name_cache:
        return _name_cache[symbol]
    for market in ("tse", "otc"):
        try:
            r = http_requests.get(
                f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
                f"?ex_ch={market}_{symbol}.tw&json=1&delay=0",
                timeout=3,
            )
            arr = r.json().get("msgArray", [])
            if arr and arr[0].get("n"):
                _name_cache[symbol] = arr[0]["n"]
                return _name_cache[symbol]
        except Exception:
            pass
    _name_cache[symbol] = symbol
    return symbol


def get_stock_quote(symbol: str):
    if _account is None:
        return {"error": "not logged in"}
    try:
        result = _sdk.stock.query_symbol_quote(_account, symbol)
        if not result.is_success:
            return {"error": result.message}
        q = result.data
        prev_close = q.reference_price or 0
        current = q.last_price or prev_close
        change = current - prev_close
        change_pct = change / prev_close * 100 if prev_close else 0
        odd = None
        try:
            odd_r = _sdk.stock.query_symbol_quote(_account, symbol, MarketType.IntradayOdd)
            if odd_r.is_success and odd_r.data:
                oq = odd_r.data
                odd_prev = oq.reference_price or 0
                odd_cur = oq.last_price or odd_prev
                odd_chg = odd_cur - odd_prev
                odd = {
                    "price": odd_cur,
                    "change": round(odd_chg, 2),
                    "change_pct": round(odd_chg / odd_prev * 100 if odd_prev else 0, 2),
                    "volume": oq.total_volume,
                }
        except Exception:
            pass

        return {
            "symbol": q.symbol,
            "name": get_stock_name(symbol),
            "price": current,
            "prev_close": prev_close,
            "open": q.open_price,
            "bid": q.bid_price,
            "ask": q.ask_price,
            "volume": q.total_volume,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "odd": odd,
        }
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/login", methods=["POST"])
def login():
    global _sdk, _account
    data = request.json or {}
    password = data.get("password") or os.environ.get("FUBON_PASSWORD", "")
    account_id = os.environ.get("FUBON_ACCOUNT", "")
    cert_path = os.environ.get("FUBON_CERT_PATH", "")
    cert_password = os.environ.get("FUBON_CERT_PASSWORD", "")

    try:
        sdk = FubonSDK()
        result = sdk.login(account_id, password, cert_path, cert_password)
        if not result.is_success:
            return jsonify({"ok": False, "message": result.message}), 401
        _sdk = sdk
        _account = result.data[0]
        session["logged_in"] = True
        session["account_name"] = _account.name
        session["account_no"] = _account.account
        return jsonify({
            "ok": True,
            "name": _account.name,
            "account": _account.account,
        })
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500


@app.route("/api/logout", methods=["POST"])
def logout():
    global _sdk, _account
    try:
        if _sdk:
            _sdk.logout()
    except Exception:
        pass
    _sdk = None
    _account = None
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/status")
def status():
    if session.get("logged_in") and _account is not None:
        return jsonify({
            "logged_in": True,
            "name": session.get("account_name"),
            "account": session.get("account_no"),
        })
    return jsonify({"logged_in": False})


@app.route("/api/market")
def market():
    if not session.get("logged_in") or _account is None:
        return jsonify({"error": "not logged in"}), 401
    raw = request.args.get("symbols", "2330,0050")
    symbols = [s.strip() for s in raw.split(",") if s.strip()]
    return jsonify({
        "taiex": get_taiex(),
        "stocks": [get_stock_quote(s) for s in symbols],
    })


if __name__ == "__main__":
    app.run(debug=True, port=8080)
