import time

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from config import BNB_RPC_URL, WATCHED_WALLET


web3 = Web3(
    Web3.HTTPProvider(
        BNB_RPC_URL,
        request_kwargs={"timeout": 30}
    )
)

web3.middleware_onion.inject(
    ExtraDataToPOAMiddleware,
    layer=0
)

if not web3.is_connected():
    raise ConnectionError(
        "Gagal terhubung ke BNB Smart Chain"
    )

watched_wallet = Web3.to_checksum_address(
    WATCHED_WALLET
)

TRANSFER_TOPIC = web3.keccak(
    text="Transfer(address,address,uint256)"
).hex()

last_block = web3.eth.block_number

print("✅ Wallet monitor aktif")
print(f"👀 Wallet: {watched_wallet}")
print(f"📦 Mulai dari block: {last_block}")
print("⏳ Memantau transaksi baru...\n")


def topic_to_address(topic):

    return Web3.to_checksum_address(
        "0x" + topic.hex()[-40:]
    )


while True:

    try:

        latest_block = web3.eth.block_number

        if latest_block > last_block:

            for block_number in range(
                last_block + 1,
                latest_block + 1
            ):

                block = web3.eth.get_block(
                    block_number,
                    full_transactions=True
                )

                for transaction in block["transactions"]:

                    if (
                        transaction["from"].lower()
                        != watched_wallet.lower()
                    ):
                        continue

                    tx_hash = transaction["hash"]

                    print("\n🚨 TRANSAKSI BARU")

                    print(
                        "TX Hash:",
                        "0x" + tx_hash.hex()
                    )

                    print(
                        "Contract:",
                        transaction["to"]
                    )

                    print(
                        "Nonce:",
                        transaction["nonce"]
                    )

                    receipt = (
                        web3.eth.get_transaction_receipt(
                            tx_hash
                        )
                    )

                    print(
                        "Status:",
                        receipt["status"]
                    )

                    print(
                        "\n📦 SEMUA TOKEN TRANSFERS:"
                    )

                    found_transfer = False

                    for log in receipt["logs"]:

                        if len(log["topics"]) < 3:
                            continue

                        if (
                            log["topics"][0].hex().lower()
                            != TRANSFER_TOPIC.lower()
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

                        token_contract = (
                            Web3.to_checksum_address(
                                log["address"]
                            )
                        )

                        amount_raw = int(
                            log["data"].hex(),
                            16
                        )

                        found_transfer = True

                        print(
                            "\n🪙 Token contract:",
                            token_contract
                        )

                        print(
                            "From:",
                            from_address
                        )

                        print(
                            "To:",
                            to_address
                        )

                        print(
                            "Raw amount:",
                            amount_raw
                        )

                        if (
                            from_address.lower()
                            == watched_wallet.lower()
                        ):

                            print(
                                "Direction: "
                                "WALLET KELUAR ⬆️"
                            )

                        elif (
                            to_address.lower()
                            == watched_wallet.lower()
                        ):

                            print(
                                "Direction: "
                                "WALLET MASUK ⬇️"
                            )

                        else:

                            print(
                                "Direction: "
                                "INTERNAL CONTRACT 🔄"
                            )

                    if not found_transfer:

                        print(
                            "Tidak ada event "
                            "Transfer BEP-20."
                        )

                    print(
                        "\n" + "=" * 65
                    )

            last_block = latest_block

        time.sleep(2)

    except Exception as error:

        print(
            "❌ Error:",
            error
        )

        time.sleep(5)