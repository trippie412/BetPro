"""Wallet routes for deposits, withdrawals, and transactions."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Deposit, Withdrawal, WalletTransaction, Wallet
from app.wallet import wallet_bp
from app.wallet.forms import DepositForm, WithdrawalForm
from app.constants import *
from app.services import WalletService, BonusService, NotificationService, AuditService
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

        deposit = Deposit(
            user_id=current_user.id, amount=amount,
            payment_method=form.payment_method.data,
            phone_number=form.phone_number.data,
            status=REQUEST_PENDING
        )
        db.session.add(deposit)
        db.session.commit()

        # Process payment (mock)
        from app.services import PaymentService
        result = PaymentService.process_deposit(deposit)

        if result.get('success'):
            deposit.status = REQUEST_APPROVED
            deposit.transaction_code = result.get('transaction_id')
            deposit.receipt_number = f'RCT-{deposit.reference[:8]}'
            deposit.approved_at = datetime.now(timezone.utc)

            # Credit wallet
            WalletService.add_funds(current_user, amount, f'Deposit via {form.payment_method.data}')

            # Check welcome bonus
            bonus_result = BonusService.check_welcome_bonus(current_user, amount)
            if bonus_result[0]:
                flash(bonus_result[1], 'success')

            db.session.commit()
            flash(f'KES {amount:,.2f} deposited successfully!', 'success')
        else:
            flash('Deposit processing failed. Please try again.', 'danger')

        return redirect(url_for('wallet.index'))

    return render_template('wallet/deposit.html', form=form)


@wallet_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
@suspended_check
def withdraw():
    form = WithdrawalForm()
    wallet = current_user.wallet

    if form.validate_on_submit():
        amount = form.amount.data
        min_wd = current_app.config.get('MINIMUM_WITHDRAWAL', 100)

        if amount < min_wd:
            flash(f'Minimum withdrawal is KES {min_wd:,.2f}', 'warning')
            return render_template('wallet/withdraw.html', form=form)

        if amount > wallet.balance:
            flash('Insufficient balance for withdrawal.', 'danger')
            return render_template('wallet/withdraw.html', form=form)

        withdrawal = Withdrawal(
            user_id=current_user.id, amount=amount,
            payment_method=form.payment_method.data,
            phone_number=form.phone_number.data,
            account_name=form.account_name.data,
            account_number=form.account_number.data,
            status=REQUEST_PENDING
        )
        db.session.add(withdrawal)
        db.session.commit()

        NotificationService.send(current_user.id, '💰 Withdrawal Request Submitted',
                                 f'Your withdrawal of KES {amount:,.2f} is pending approval.',
                                 NOTIFICATION_WITHDRAWAL, withdrawal.id)

        flash('Withdrawal request submitted for approval.', 'info')
        return redirect(url_for('wallet.index'))

    return render_template('wallet/withdraw.html', form=form, wallet=wallet)


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


from flask import current_app