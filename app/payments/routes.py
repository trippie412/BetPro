"""Payment gateway routes."""
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Deposit, Withdrawal
from app.payments import payments_bp
from app.payments.forms import PaymentConfigForm
from app.decorators import admin_required
from app.services import PaymentService


@payments_bp.route('/callback/<payment_method>', methods=['POST'])
def payment_callback(payment_method):
    """Handle payment gateway callback/webhook."""
    data = request.get_json() or request.form.to_dict()
    # In production, verify the callback signature
    transaction_id = data.get('transaction_id')
    status = data.get('status')
    reference = data.get('reference')

    if not transaction_id:
        return jsonify({'error': 'Missing transaction_id'}), 400

    # Find the deposit by reference
    deposit = Deposit.query.filter_by(reference=reference).first()
    if deposit:
        if status == 'completed':
            deposit.status = 'approved'
            from app.services import WalletService
            WalletService.add_funds(deposit.user, deposit.amount, f'Payment callback: {transaction_id}')
            db.session.commit()
        elif status == 'failed':
            deposit.status = 'rejected'
            db.session.commit()

    return jsonify({'status': 'received'})


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