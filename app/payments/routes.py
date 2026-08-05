from flask import Blueprint, request, jsonify
from app.payments.palpluss import send_stk


payments = Blueprint(
    "payments",
    __name__
)


@payments.route("/deposit", methods=["POST"])
def deposit():

    data = request.json

    phone = data.get("phone")
    amount = data.get("amount")


    response = send_stk(
        phone,
        amount
    )

