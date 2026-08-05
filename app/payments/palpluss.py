import os
from palpluss import PalPluss
from dotenv import load_dotenv

load_dotenv()


client = PalPluss(
    api_key=os.getenv("PALPLUSS_API_KEY")
)


def send_stk(phone, amount):

    return client.stk_push(
        amount=amount,
        phone=phone,
        account_reference="BETPRO",
        transaction_desc="BetPro Deposit",
        channel_id=os.getenv("PALPLUSS_CHANNEL_ID"),
        callback_url=os.getenv("CALLBACK_URL")
    )
