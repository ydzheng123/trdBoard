import os
from fubon_neo.sdk import FubonSDK


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

accounts = sdk.login(
    os.environ["FUBON_ACCOUNT"],
    os.environ["FUBON_PASSWORD"],
    os.environ["FUBON_CERT_PATH"],
    os.environ["FUBON_CERT_PASSWORD"],
)

print(accounts)

account = accounts.data[0]

result = sdk.stock.query_symbol_quote(account, "2330")

print(result)