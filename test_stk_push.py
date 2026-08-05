from palpluss import PalPluss, PalPlussApiError


client = PalPluss(
    api_key="pp_live_b8d1690cb96cb20076d4e27dab4745bf7a2faa9420193064"
)


try:

    response = client.stk_push(
        amount=10,
        phone="+254708209070",
        account_reference="BETPRO001",
        transaction_desc="BetPro Wallet Deposit",
        channel_id="9b59fd9f-e5f5-4d58-9991-e46e6eac472a",
        callback_url="https://yourdomain.com/webhooks/palpluss"
    )


    print("STK PUSH SENT ✅")
    print(response)


except PalPlussApiError as e:

    print("PALPLUSS ERROR ❌")
    print(e)


except Exception as e:

    print("SYSTEM ERROR ❌")
    print(e)
