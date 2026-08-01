import requests
import time

from datetime import (
    datetime,
    timezone,
    timedelta
)

from decimal import Decimal

from web3 import Web3

from web3.middleware import (
    ExtraDataToPOAMiddleware
)




from config import (
    BNB_RPC_URL,
    WATCHED_WALLETS,
    EXECUTOR_CONTRACT,
    TOKEN_CONTRACT,
    USDT_CONTRACT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)


# ============================================================
# KONEKSI BNB SMART CHAIN
# ============================================================

web3 = Web3(
    Web3.HTTPProvider(
        BNB_RPC_URL,
        request_kwargs={
            "timeout": 30
        }
    )
)


# BNB Chain menggunakan PoSA.
# Middleware ini diperlukan agar block dapat dibaca oleh Web3.py.
web3.middleware_onion.inject(
    ExtraDataToPOAMiddleware,
    layer=0
)


if not web3.is_connected():

    raise ConnectionError(
        "❌ Gagal terhubung ke BNB Smart Chain"
    )


# ============================================================
# KONFIGURASI TELEGRAM
# ============================================================

telegram_enabled = bool(
    TELEGRAM_BOT_TOKEN
    and
    TELEGRAM_CHAT_ID
)




# ============================================================
# FUNGSI KIRIM TELEGRAM
# ============================================================
# ============================================================
# KONFIGURASI TELEGRAM
# ============================================================

telegram_enabled = bool(
    TELEGRAM_BOT_TOKEN
    and
    TELEGRAM_CHAT_ID
)


def send_telegram(message):

    if not telegram_enabled:

        return


    try:

        telegram_url = (
            f"https://api.telegram.org/"
            f"bot{TELEGRAM_BOT_TOKEN}/"
            f"sendMessage"
        )


        response = requests.post(
            telegram_url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=15
        )


        response.raise_for_status()


        print(
            "📱 Notifikasi Telegram berhasil dikirim"
        )


    except requests.Timeout:

        print(
            "⚠️ Telegram timeout. "
            "Tracker tetap berjalan."
        )


    except requests.RequestException as error:

        print(
            "⚠️ Gagal mengirim "
            "notifikasi Telegram:"
        )

        print(
            error
        )


    except Exception as error:

        print(
            "⚠️ Error Telegram:"
        )

        print(
            error
        )
# ============================================================
# VALIDASI WALLET
# ============================================================

if not WATCHED_WALLETS:

    raise ValueError(
        "❌ WATCHED_WALLETS kosong. "
        "Masukkan minimal satu wallet."
    )


watched_wallets = {}


for wallet_item in WATCHED_WALLETS:

    trader_name = (
        wallet_item.get(
            "name"
        )
    )


    wallet_address = (
        wallet_item.get(
            "wallet"
        )
    )


    if not trader_name:

        raise ValueError(
            "❌ Salah satu wallet "
            "tidak memiliki name."
        )


    if not wallet_address:

        raise ValueError(
            f"❌ Wallet untuk "
            f"{trader_name} kosong."
        )


    if not Web3.is_address(
        wallet_address
    ):

        raise ValueError(
            f"❌ Alamat wallet "
            f"{trader_name} tidak valid: "
            f"{wallet_address}"
        )


    checksum_wallet = (
        Web3.to_checksum_address(
            wallet_address
        )
    )


    watched_wallets[
        checksum_wallet.lower()
    ] = {
        "name": trader_name,

        "wallet": checksum_wallet
    }


# ============================================================
# VALIDASI CONTRACT
# ============================================================

if not Web3.is_address(
    EXECUTOR_CONTRACT
):

    raise ValueError(
        "❌ EXECUTOR_CONTRACT "
        "tidak valid."
    )


if not Web3.is_address(
    TOKEN_CONTRACT
):

    raise ValueError(
        "❌ TOKEN_CONTRACT "
        "tidak valid."
    )


if not Web3.is_address(
    USDT_CONTRACT
):

    raise ValueError(
        "❌ USDT_CONTRACT "
        "tidak valid."
    )


executor_contract = (
    Web3.to_checksum_address(
        EXECUTOR_CONTRACT
    )
)


token_contract = (
    Web3.to_checksum_address(
        TOKEN_CONTRACT
    )
)


usdt_contract = (
    Web3.to_checksum_address(
        USDT_CONTRACT
    )
)


# ============================================================
# EVENT TRANSFER BEP-20
# ============================================================

TRANSFER_TOPIC = web3.keccak(
    text=(
        "Transfer("
        "address,"
        "address,"
        "uint256"
        ")"
    )
).hex().lower()


# ============================================================
# ABI MINIMUM ERC-20
# ============================================================

ERC20_ABI = [
    {
        "name": "symbol",

        "type": "function",

        "stateMutability": "view",

        "inputs": [],

        "outputs": [
            {
                "name": "",

                "type": "string"
            }
        ]
    },

    {
        "name": "decimals",

        "type": "function",

        "stateMutability": "view",

        "inputs": [],

        "outputs": [
            {
                "name": "",

                "type": "uint8"
            }
        ]
    }
]


# ============================================================
# FUNGSI TOKEN
# ============================================================

def get_token_info(
    contract_address
):

    contract = (
        web3.eth.contract(
            address=contract_address,
            abi=ERC20_ABI
        )
    )


    try:

        symbol = (
            contract
            .functions
            .symbol()
            .call()
        )

    except Exception:

        symbol = "UNKNOWN"


    try:

        decimals = (
            contract
            .functions
            .decimals()
            .call()
        )

    except Exception:

        decimals = 18


    return (
        symbol,
        decimals
    )


def normalize_amount(
    raw_amount,
    decimals
):

    return (

        Decimal(
            raw_amount
        )

        /

        Decimal(
            10 ** decimals
        )

    )


def topic_to_address(
    topic
):

    return (

        Web3.to_checksum_address(

            "0x"

            +

            topic.hex()[-40:]

        )

    )


# ============================================================
# INFORMASI TOKEN
# ============================================================

(
    token_symbol,
    token_decimals
) = get_token_info(
    token_contract
)


(
    usdt_symbol,
    usdt_decimals
) = get_token_info(
    usdt_contract
)


# ============================================================
# POSISI TERPISAH UNTUK SETIAP WALLET
# ============================================================

positions = {}


for wallet_key in watched_wallets:

    positions[
        wallet_key
    ] = {

        "total_buy": Decimal("0"),

        "total_sell": Decimal("0"),

        "total_usdt_spent": Decimal("0"),

        "total_usdt_received": Decimal("0"),

        "transaction_count": 0

    }


# ============================================================
# WAKTU WIB
# ============================================================

wib_timezone = timezone(
    timedelta(
        hours=7
    )
)


# ============================================================
# BLOCK AWAL
# ============================================================

last_block = (
    web3.eth.block_number
)


# ============================================================
# TAMPILKAN POSISI
# ============================================================

def print_position(
    trader,
    position
):

    total_buy = (
        position[
            "total_buy"
        ]
    )


    total_sell = (
        position[
            "total_sell"
        ]
    )


    net_position = (

        total_buy

        -

        total_sell

    )


    print()

    print(
        "📊 POSISI ESTIMASI"
    )

    print()

    print(
        f"👤 Trader: "
        f"{trader['name']}"
    )

    print(
        f"👀 Wallet: "
        f"{trader['wallet']}"
    )

    print()

    print(
        f"Total BUY : "
        f"{total_buy:,.8f} "
        f"{token_symbol}"
    )

    print(
        f"Total SELL: "
        f"{total_sell:,.8f} "
        f"{token_symbol}"
    )

    print(
        f"Net posisi: "
        f"{net_position:,.8f} "
        f"{token_symbol}"
    )

    print()

    print(
        f"Jumlah transaksi: "
        f"{position['transaction_count']}"
    )

    print()


    if net_position > 0:

        print(
            "Status:"
        )

        print(
            "🟢 MASIH MEMILIKI POSISI"
        )


    elif net_position == 0:

        print(
            "Status:"
        )

        print(
            "🔴 POSISI BERSIH NOL"
        )


    else:

        print(
            "Status:"
        )

        print(
            "⚠️ DATA POSISI "
            "BELUM LENGKAP"
        )


    return net_position


# ============================================================
# INFORMASI AWAL
# ============================================================

print()

print(
    "✅ Multi-wallet position tracker aktif"
)

print()

print(
    f"🪙 Token: "
    f"{token_symbol}"
)

print(
    f"📄 Token contract:"
)

print(
    token_contract
)

print()

print(
    "⚙️ Executor bersama:"
)

print(
    executor_contract
)

print()

print(
    f"👥 Jumlah wallet: "
    f"{len(watched_wallets)}"
)

print()


for number, trader in enumerate(

    watched_wallets.values(),

    start=1

):

    print(
        f"{number}. "
        f"{trader['name']}"
    )

    print(
        f"   {trader['wallet']}"
    )


print()

print(
    f"📦 Mulai dari block: "
    f"{last_block}"
)

print()

if telegram_enabled:

    print(
        "📱 Notifikasi Telegram: AKTIF"
    )

else:

    print(
        "📱 Notifikasi Telegram: NONAKTIF"
    )


print()

print(
    f"⏳ Memantau aktivitas "
    f"{token_symbol}..."
)

print()


# ============================================================
# LOOP MONITOR
# ============================================================

while True:

    try:

        latest_block = (
            web3.eth.block_number
        )


        if latest_block <= last_block:

            time.sleep(2)

            continue


        for block_number in range(

            last_block + 1,

            latest_block + 1

        ):


            block = (
                web3.eth.get_block(
                    block_number,
                    full_transactions=True
                )
            )


            # =================================================
            # WAKTU BLOCK
            # =================================================

            block_time = (
                datetime.fromtimestamp(
                    block["timestamp"],
                    tz=timezone.utc
                )
            )


            block_time_wib = (
                block_time.astimezone(
                    wib_timezone
                )
            )


            formatted_time = (
                block_time_wib.strftime(
                    "%Y-%m-%d "
                    "%H:%M:%S WIB"
                )
            )


            # =================================================
            # TRANSAKSI DALAM BLOCK
            # =================================================

            for transaction in (
                block["transactions"]
            ):


                transaction_from = (

                    transaction["from"]

                    .lower()

                )


                # Hanya proses wallet terdaftar
                if (

                    transaction_from

                    not in

                    watched_wallets

                ):

                    continue


                current_trader = (

                    watched_wallets[
                        transaction_from
                    ]

                )


                current_position = (

                    positions[
                        transaction_from
                    ]

                )


                tx_hash = (
                    transaction["hash"]
                )


                receipt = (

                    web3.eth
                    .get_transaction_receipt(
                        tx_hash
                    )

                )


                # Abaikan transaksi gagal
                if (

                    receipt["status"]

                    !=

                    1

                ):

                    continue


                # =================================================
                # DATA TRANSAKSI
                # =================================================

                token_in = Decimal("0")

                token_out = Decimal("0")

                usdt_in = Decimal("0")

                usdt_out = Decimal("0")

                found_token_activity = False


                # =================================================
                # BACA EVENT TRANSFER
                # =================================================

                for log in (
                    receipt["logs"]
                ):


                    if (

                        len(
                            log["topics"]
                        )

                        <

                        3

                    ):

                        continue


                    event_signature = (

                        log["topics"][0]

                        .hex()

                        .lower()

                    )


                    if (

                        event_signature

                        !=

                        TRANSFER_TOPIC

                    ):

                        continue


                    from_address = (
                        topic_to_address(
                            log["topics"][1]
                        )
                    )


                    to_address = (
                        topic_to_address(
                            log["topics"][2]
                        )
                    )


                    log_token_contract = (

                        Web3.to_checksum_address(
                            log["address"]
                        )

                    )


                    raw_amount = int(

                        log["data"].hex(),

                        16

                    )


                    # =============================================
                    # TOKEN YANG DIPANTAU
                    # =============================================

                    if (

                        log_token_contract
                        .lower()

                        ==

                        token_contract
                        .lower()

                    ):


                        amount = (
                            normalize_amount(
                                raw_amount,
                                token_decimals
                            )
                        )


                        if (

                            to_address
                            .lower()

                            ==

                            executor_contract
                            .lower()

                        ):

                            token_in += amount

                            found_token_activity = True


                        elif (

                            from_address
                            .lower()

                            ==

                            executor_contract
                            .lower()

                        ):

                            token_out += amount

                            found_token_activity = True


                    # =============================================
                    # USDT
                    # =============================================

                    elif (

                        log_token_contract
                        .lower()

                        ==

                        usdt_contract
                        .lower()

                    ):


                        amount = (
                            normalize_amount(
                                raw_amount,
                                usdt_decimals
                            )
                        )


                        if (

                            to_address
                            .lower()

                            ==

                            executor_contract
                            .lower()

                        ):

                            usdt_in += amount


                        elif (

                            from_address
                            .lower()

                            ==

                            executor_contract
                            .lower()

                        ):

                            usdt_out += amount


                # =================================================
                # JANGAN TAMPILKAN TOKEN LAIN
                # =================================================

                if not found_token_activity:

                    continue


                # =================================================
                # INFORMASI DASAR
                # =================================================

                print()

                print(
                    "🚨 AKTIVITAS TOKEN "
                    "TERDETEKSI"
                )

                print()

                print(
                    f"👤 Trader: "
                    f"{current_trader['name']}"
                )

                print(
                    f"👀 Wallet: "
                    f"{current_trader['wallet']}"
                )

                print()

                print(
                    f"🕒 Waktu:"
                )

                print(
                    formatted_time
                )

                print()

                print(
                    f"🪙 Token: "
                    f"{token_symbol}"
                )

                print()

                print(
                    "TX:"
                )

                print(
                    "0x"
                    +
                    tx_hash.hex()
                )


                # =================================================
                # BUY
                # =================================================

                if (

                    token_in > 0

                    and

                    token_out == 0

                ):


                    current_position[
                        "total_buy"
                    ] += token_in


                    current_position[
                        "total_usdt_spent"
                    ] += usdt_out


                    current_position[
                        "transaction_count"
                    ] += 1


                    net_position = (

                        current_position[
                            "total_buy"
                        ]

                        -

                        current_position[
                            "total_sell"
                        ]

                    )


                    buy_price = None


                    if usdt_out > 0:

                        buy_price = (

                            usdt_out

                            /

                            token_in

                        )


                    print()

                    print(
                        "🟢 BUY TERDETEKSI"
                    )

                    print()

                    print(
                        f"{token_symbol} masuk:"
                    )

                    print(
                        f"{token_in:,.8f}"
                    )


                    if usdt_out > 0:

                        print()

                        print(
                            f"{usdt_symbol} "
                            "digunakan:"
                        )

                        print(
                            f"${usdt_out:,.6f}"
                        )

                        print(
                            "Harga beli:"
                        )

                        print(
                            f"${buy_price:.12f}"
                        )


                    # =============================================
                    # PESAN TELEGRAM BUY
                    # =============================================

                    telegram_message = f"""
🚨 <b>{token_symbol} BUY DETECTED</b>

👤 <b>Trader:</b>
{current_trader["name"]}

👀 <b>Wallet:</b>
<code>{current_trader["wallet"]}</code>

🟢 <b>BUY</b>

🪙 <b>{token_symbol} masuk:</b>
{token_in:,.8f}

💵 <b>{usdt_symbol} digunakan:</b>
${usdt_out:,.6f}
"""


                    if buy_price is not None:

                        telegram_message += f"""

📈 <b>Harga beli:</b>
${buy_price:.12f}
"""


                    telegram_message += f"""

📊 <b>Net posisi:</b>
{net_position:,.8f} {token_symbol}

🕒 <b>Waktu:</b>
{formatted_time}

🔗 <a href="https://bscscan.com/tx/0x{tx_hash.hex()}">Lihat transaksi di BscScan</a>
"""


                    send_telegram(
                        telegram_message
                    )


                # =================================================
                # SELL
                # =================================================

                elif (

                    token_out > 0

                    and

                    token_in == 0

                ):


                    current_position[
                        "total_sell"
                    ] += token_out


                    current_position[
                        "total_usdt_received"
                    ] += usdt_in


                    current_position[
                        "transaction_count"
                    ] += 1


                    net_position = (

                        current_position[
                            "total_buy"
                        ]

                        -

                        current_position[
                            "total_sell"
                        ]

                    )


                    sell_price = None


                    if usdt_in > 0:

                        sell_price = (

                            usdt_in

                            /

                            token_out

                        )


                    print()

                    print(
                        "🔴 SELL TERDETEKSI"
                    )

                    print()

                    print(
                        f"{token_symbol} keluar:"
                    )

                    print(
                        f"{token_out:,.8f}"
                    )


                    if usdt_in > 0:

                        print()

                        print(
                            f"{usdt_symbol} "
                            "diterima:"
                        )

                        print(
                            f"${usdt_in:,.6f}"
                        )

                        print(
                            "Harga jual:"
                        )

                        print(
                            f"${sell_price:.12f}"
                        )


                    # =============================================
                    # PESAN TELEGRAM SELL
                    # =============================================

                    telegram_message = f"""
🚨 <b>{token_symbol} SELL DETECTED</b>

👤 <b>Trader:</b>
{current_trader["name"]}

👀 <b>Wallet:</b>
<code>{current_trader["wallet"]}</code>

🔴 <b>SELL</b>

🪙 <b>{token_symbol} keluar:</b>
{token_out:,.8f}

💵 <b>{usdt_symbol} diterima:</b>
${usdt_in:,.6f}
"""


                    if sell_price is not None:

                        telegram_message += f"""

📉 <b>Harga jual:</b>
${sell_price:.12f}
"""


                    telegram_message += f"""

📊 <b>Net posisi:</b>
{net_position:,.8f} {token_symbol}

🕒 <b>Waktu:</b>
{formatted_time}

🔗 <a href="https://bscscan.com/tx/0x{tx_hash.hex()}">Lihat transaksi di BscScan</a>
"""


                    send_telegram(
                        telegram_message
                    )


                # =================================================
                # AKTIVITAS KOMPLEKS
                # =================================================

                else:

                    print()

                    print(
                        "🟡 AKTIVITAS KOMPLEKS"
                    )

                    print(
                        f"{token_symbol} masuk "
                        "dan keluar dalam "
                        "satu transaksi."
                    )


                # =================================================
                # TAMPILKAN POSISI
                # =================================================

                print_position(

                    current_trader,

                    current_position

                )


                print()

                print(
                    "=" * 70
                )


        # ====================================================
        # UPDATE BLOCK TERAKHIR
        # ====================================================

        last_block = (
            latest_block
        )


        time.sleep(2)


    except KeyboardInterrupt:

        print()

        print(
            "🛑 Tracker dihentikan."
        )

        break


    except Exception as error:

        print()

        print(
            "❌ Error:"
        )

        print(
            error
        )

        print()

        print(
            "Mencoba lagi "
            "dalam 5 detik..."
        )

        time.sleep(5)