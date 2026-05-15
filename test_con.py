import os
from fubon_neo.sdk import FubonSDK
from fubon_neo.constant import TimeInForce, OrderType, MarketType, PriceType


def load_env(path=".env"):
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


load_env()

sdk = FubonSDK()

try:
    accounts = sdk.login(
        os.environ["FUBON_ACCOUNT"],
        os.environ["FUBON_PASSWORD"],
        os.environ["FUBON_CERT_PATH"],
        os.environ["FUBON_CERT_PASSWORD"],
    )
    print("登入結果:", accounts)
except Exception as e:
    print("觸發測試回傳:", e)
