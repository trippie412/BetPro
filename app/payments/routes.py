"""Payment gateway routes."""
import json
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Deposit, Withdrawal
from app.payments import payments_bp
from app.payments.forms import PaymentConfigForm
from app.decorators import admin_required
from app.services import PaymentService
from app.constants import REQUEST_APPROVED, REQUEST_REJECTED


from app.services import MpesaService, WalletService,  PesapalService

@payments_bp.route("/callback/mpesa", methods=["POST"])
def payment_callback():
    data = request.get_json(force=True)

    result = MpesaService.process_callback(data)

    checkout_id = result["CheckoutRequestID"]

    deposit = Deposit.query.filter_by(
        checkout_request_id=checkout_id
    ).first()

    if not deposit:
        return jsonify({"ResultCode": 0})

    if result["success"]:

        # Prevent duplicate crediting
        if deposit.status != REQUEST_APPROVED:

            deposit.status = REQUEST_APPROVED
            deposit.receipt_number = result["receipt"]
            deposit.transaction_code = result["receipt"]

            WalletService.add_funds(
                deposit.user,
                deposit.amount,
                "M-Pesa Deposit"
            )

            db.session.commit()

    else:
        deposit.status = REQUEST_REJECTED
        db.session.commit()

    return jsonify({"ResultCode": 0})


@payments_bp.route("/callback/pesapal", methods=["GET"])
def pesapal_callback():
    """
    User is redirected here by Pesapal after payment.
    """

    order_tracking_id = request.args.get("OrderTrackingId")

    if not order_tracking_id:
        flash("Missing Pesapal tracking ID.", "danger")
        return redirect(url_for("wallet.index"))

    return redirect(
        url_for(
            "payments.pesapal_verify",
            tracking_id=order_tracking_id
        )
    )
    
@payments_bp.route("/verify/pesapal/<tracking_id>")
def pesapal_verify(tracking_id):

    result = PesapalService.get_transaction_status(tracking_id)

    if not result["success"]:
        flash("Unable to verify payment.", "danger")
        return redirect(url_for("wallet.index"))

    flash("Payment verified successfully.", "success")

    return redirect(url_for("wallet.index"))


@payments_bp.route('/status/<reference>')
@login_required
def payment_status(reference):
    deposit = Deposit.query.filter_by(reference=reference, user_id=current_user.id).first_or_404()
    return jsonify({
        'status': deposit.status,
        'amount': deposit.amount,
        'reference': deposit.reference,
        'receipt': deposit.receipt_number,
    })


@payments_bp.route('/config', methods=['GET', 'POST'])
@login_required
@admin_required
def config():
    form = PaymentConfigForm()
    if form.validate_on_submit():
        flash('Payment configuration saved.', 'success')
        return redirect(url_for('admin.index'))
    return render_template('payments/config.html', form=form)