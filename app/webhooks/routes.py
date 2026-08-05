from flask import Blueprint, request, jsonify

from app import db
from app.models import Deposit
from app.services import WalletService
from app.constants import REQUEST_APPROVED

webhook = Blueprint(
    "webhook",
    __name__
)


@webhook.route("/palpluss", methods=["POST"])
def palpluss_callback():

    data = request.get_json(silent=True) or {}

    print("=" * 60)
    print("PALPLUSS CALLBACK")
    print(data)
    print("=" * 60)

    # ----------------------------------------------------
    # Try to get transaction/reference from callback
    # ----------------------------------------------------
    transaction_id = (
        data.get("transaction_id")
        or data.get("TransactionID")
        or data.get("reference")
        or data.get("reference_id")
        or data.get("checkout_request_id")
    )

    if not transaction_id:
        return jsonify({
            "success": False,
            "message": "Missing transaction id."
        }), 400

    deposit = Deposit.query.filter_by(
        checkout_request_id=str(transaction_id)
    ).first()

    if not deposit:
        return jsonify({
            "success": False,
            "message": "Deposit not found."
        }), 404

    # Prevent duplicate crediting
    if deposit.status == REQUEST_APPROVED:
        return jsonify({
            "success": True,
            "message": "Already processed."
        })

    deposit.status = REQUEST_APPROVED

    db.session.commit()

    WalletService.add_funds(
        deposit.user,
        deposit.amount,
        "PalPluss Deposit"
    )

    return jsonify({
        "success": True,
        "message": "Deposit approved."
    })