import os
from dotenv import load_dotenv
from palpluss import PalPluss

# Load .env locally (ignored on Vercel if variables are already configured)
load_dotenv()


def get_palpluss_client():

    api_key = os.getenv("PALPLUSS_API_KEY")

    if not api_key:
        raise ValueError(
            "PALPLUSS_API_KEY is missing. Add it to Vercel Environment Variables."
        )

    return PalPluss(
        api_key=api_key
    )


def send_stk(phone, amount):

    client = get_palpluss_client()

    return client.stk_push(
        amount=amount,
        phone=phone,
        account_reference="BETPRO",
        transaction_desc="BetPro Deposit",
        channel_id=os.getenv("PALPLUSS_CHANNEL_ID"),
        callback_url=os.getenv("CALLBACK_URL")
    )