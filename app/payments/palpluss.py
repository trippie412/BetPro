import os
from dotenv import load_dotenv
from palpluss import PalPluss


# Load local .env only
# On Vercel, environment variables come from Vercel settings
load_dotenv()


def get_palpluss_client():

    api_key = os.getenv("PALPLUSS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "PALPLUSS_API_KEY is not configured. "
            "Add it in Vercel Environment Variables."
        )

    return PalPluss(
        api_key=api_key
    )


def send_stk(phone, amount):

    channel_id = os.getenv("PALPLUSS_CHANNEL_ID")
    callback_url = os.getenv("CALLBACK_URL")

    if not channel_id:
        raise RuntimeError(
            "PALPLUSS_CHANNEL_ID is missing."
        )

    if not callback_url:
        raise RuntimeError(
            "CALLBACK_URL is missing."
        )

    client = get_palpluss_client()

    try:
        response = client.stk_push(
            amount=amount,
            phone=phone,
            account_reference="BETPRO",
            transaction_desc="BetPro Deposit",
            channel_id=channel_id,
            callback_url=callback_url
        )

        return response

    except Exception as e:
        raise RuntimeError(
            f"PalPluss STK push failed: {str(e)}"
        )