import os
from dotenv import load_dotenv

load_dotenv()

BNB_RPC_URL = os.getenv("BNB_RPC_URL")

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)


TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"  
)
# Ganti dengan wallet yang ingin dipantau
WATCHED_WALLET = "0x69d9340E9fD1016998a9A8344B00b3fAc86a4661"


WATCHED_WALLETS = [
    {
        "name": "Top Trader 1",
        "wallet": "0x69d9340E9fD1016998a9A8344B00b3fAc86a4661"
    },
    {
        "name": "Top Trader 2",
        "wallet": "0xb8c4464974B31295FA183C52d055a3e14AfF7731"
    },
    {
        "name": "Top Trader 3",
        "wallet": "0x29d23322d88f4e5bd1BE86C7791Fc5E127f2E294"
    },
    {
        "name": "Top Trader 4",
        "wallet": "0x3EDb9e4b77C0F7a053387fD49c031d41d45D27EB"
    },
    {
        "name": "Top Trader 5",
        "wallet": "0xc6e2672b8E7adAbBCad9AD1D694d0567c0927014"
    }
]


# Ganti dengan contract token BEP-20
TOKEN_CONTRACT = "0xd5eaAaC47bD1993d661bc087E15dfb079a7f3C19"
# USDT BNB Smart Chain
USDT_CONTRACT = (
    "0x55d398326f99059fF775485246999027B3197955"
)
# Contract executor yang dipanggil wallet
EXECUTOR_CONTRACT = (
    "0x4E7ED91e702EF2FF0c58e251c6E20D1dC1E31a5f"
)