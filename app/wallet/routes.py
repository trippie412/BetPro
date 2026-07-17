"""Wallet routes for deposits, withdrawals, and transactions."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Deposit, Withdrawal, WalletTransaction, Wallet
from app.wallet import wallet_bp
from app.wallet.forms import DepositForm, WithdrawalForm
from app.constants import *
from app.services import WalletService, BonusService, NotificationService, AuditService, PaymentService
from app.decorators import suspended_check


@wallet_bp.route('/')
@login_required
@suspended_check
def index():
    wallet = current_user.wallet
    transactions = WalletTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(WalletTransaction.created_at.desc()).limit(10).all()
    deposits = Deposit.query.filter_by(user_id=current_user.id)\
        .order_by(Deposit.created_at.desc()).limit(5).all()
    withdrawals = Withdrawal.query.filter_by(user_id=current_user.id)\
        .order_by(Withdrawal.created_at.desc()).limit(5).all()
    return render_template('wallet/index.html', wallet=wallet,
                         transactions=transactions, deposits=deposits,
                         withdrawals=withdrawals)


@wallet_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
@suspended_check
def deposit():
    form = DepositForm()
    
    if form.validate_on_submit():
        amount = form.amount.data
        min_dep = current_app.config.get('MINIMUM_DEPOSIT', 50)

        if amount < min_dep:
            flash(f'Minimum deposit is KES {min_dep:,.2f}', 'warning')
            return render_template('wallet/deposit.html', form=form)

        # Get phone number from form
        phone = form.phone_number.data

        # Create deposit record
        deposit = Deposit(
            user_id=current_user.id,
            amount=amount,
            payment_method=form.payment_method.data,
            phone_number=phone,
            status=REQUEST_PENDING
        )
        db.session.add(deposit)
        db.session.commit()

        # Process payment via M-Pesa
        result = PaymentService.process_deposit(deposit)

        if result.get("success"):
            # STK Push sent successfully.
            # DO NOT credit the wallet here — wait for callback.
            deposit.status = REQUEST_PENDING
            deposit.checkout_request_id = result.get('checkout_request_id')
            db.session.commit()

            flash(
                "STK Push sent successfully. Please check your phone and enter your M-Pesa PIN to complete the payment.",
                "info"
            )
        else:
            deposit.status = REQUEST_FAILED
            db.session.commit()

            flash(
                result.get('message', 'Failed to send STK Push. Please try again.'),
                "danger"
            )

        return redirect(url_for("wallet.index"))

    return render_template('wallet/deposit.html', form=form)


@wallet_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
@suspended_check
def withdraw():
    form = WithdrawalForm()
    
    if form.validate_on_submit():
        amount = form.amount.data
        wallet = current_user.wallet
        
        if not wallet or wallet.balance < amount:
            flash('Insufficient balance.', 'danger')
            return render_template('wallet/withdraw.html', form=form)
        
        min_wd = current_app.config.get('MINIMUM_WITHDRAWAL', 100)
        max_wd = current_app.config.get('MAXIMUM_WITHDRAWAL', 50000)
        
        if amount < min_wd:
            flash(f'Minimum withdrawal is KES {min_wd:,.2f}', 'warning')
            return render_template('wallet/withdraw.html', form=form)
        
        if amount > max_wd:
            flash(f'Maximum withdrawal is KES {max_wd:,.2f}', 'warning')
            return render_template('wallet/withdraw.html', form=form)
        
        withdrawal = Withdrawal(
            user_id=current_user.id,
            amount=amount,
            phone_number=form.phone_number.data,
            payment_method=form.payment_method.data,
            status=WITHDRAWAL_PENDING
        )
        db.session.add(withdrawal)
        
        # Deduct from wallet
        wallet.deduct_balance(amount)
        db.session.commit()
        
        flash(
            f'Withdrawal request of KES {amount:,.2f} submitted. It will be processed shortly.',
            'success'
        )
        
        NotificationService.send(
            current_user.id,
            'Withdrawal Requested',
            f'KES {amount:,.2f} withdrawal requested.',
            NOTIFICATION_WITHDRAWAL,
            withdrawal.id
        )
        
        return redirect(url_for('wallet.index'))
    
    return render_template('wallet/withdraw.html', form=form)


@wallet_bp.route('/transactions')
@login_required
@suspended_check
def transactions():
    page = request.args.get('page', 1, type=int)
    txns = WalletTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(WalletTransaction.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('wallet/transactions.html', transactions=txns)


@wallet_bp.route('/history')
@login_required
@suspended_check
def history():
    deposits = Deposit.query.filter_by(user_id=current_user.id)\
        .order_by(Deposit.created_at.desc()).all()
    withdrawals = Withdrawal.query.filter_by(user_id=current_user.id)\
        .order_by(Withdrawal.created_at.desc()).all()
    return render_template('wallet/history.html', deposits=deposits, withdrawals=withdrawals)