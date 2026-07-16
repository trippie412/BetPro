"""Betting routes for placing bets and viewing history."""
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app import db
from app.models import Bet, BetSelection, Match, Odds, Wallet
from app.betting import betting_bp
from app.decorators import suspended_check
from app.services import BettingService, NotificationService
from app.constants import *


@betting_bp.route('/')
@login_required
@suspended_check
def index():
    """Main betting page."""
    from app.models import Sport, League
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.display_order).all()
    matches = Match.query.filter(
        Match.status.in_([MATCH_SCHEDULED, MATCH_LIVE])
    ).order_by(Match.is_live.desc(), Match.match_date.asc()).all()

    # Group matches by league
    matches_by_league = {}
    for match in matches:
        league_name = match.league.name if match.league else 'Unknown'
        if league_name not in matches_by_league:
            matches_by_league[league_name] = []
        matches_by_league[league_name].append(match)

    return render_template('betting/index.html',
                         sports=sports, matches=matches,
                         matches_by_league=matches_by_league)


@betting_bp.route('/place-bet', methods=['POST'])
@login_required
@suspended_check
def place_bet():
    """Place a bet via AJAX."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        selections = data.get('selections', [])
        stake = float(data.get('stake', 0))
        use_bonus = data.get('use_bonus', False)

        if not selections or stake <= 0:
            return jsonify({'success': False, 'error': 'Invalid selections or stake'}), 400

        success, result = BettingService.place_bet(current_user, selections, stake, use_bonus)

        if success:
            bet = result
            return jsonify({
                'success': True,
                'bet_reference': bet.bet_reference,
                'total_odds': bet.total_odds,
                'potential_winnings': bet.potential_winnings,
                'message': f'Bet placed successfully! Reference: {bet.bet_reference}'
            })
        else:
            return jsonify({'success': False, 'error': result}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@betting_bp.route('/bet-slip')
@login_required
def bet_slip():
    """View current bet slip."""
    return render_template('betting/bet_slip.html')


@betting_bp.route('/history')
@login_required
@suspended_check
def history():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')

    query = Bet.query.filter_by(user_id=current_user.id)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    bets = query.order_by(Bet.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)

    return render_template('betting/history.html', bets=bets, current_status=status_filter)


@betting_bp.route('/detail/<bet_reference>')
@login_required
@suspended_check
def detail(bet_reference):
    bet = Bet.query.filter_by(bet_reference=bet_reference, user_id=current_user.id).first_or_404()
    return render_template('betting/detail.html', bet=bet)


@betting_bp.route('/get-odds/<int:match_id>')
@login_required
def get_odds(match_id):
    match = Match.query.get_or_404(match_id)
    odds = match.main_odds
    if not odds:
        return jsonify({'error': 'No odds available'}), 404
    return jsonify({
        'match_id': match.id,
        'home_team': match.home_team,
        'away_team': match.away_team,
        'home_win': odds.home_win,
        'draw': odds.draw,
        'away_win': odds.away_win,
        'btts_yes': odds.btts_yes,
        'btts_no': odds.btts_no,
        'over_under_line': odds.over_under_line,
        'over': odds.over,
        'under': odds.under,
        'double_chance_1x': odds.double_chance_1x,
        'double_chance_12': odds.double_chance_12,
        'double_chance_2x': odds.double_chance_2x,
    })


@betting_bp.route('/calculate', methods=['POST'])
@login_required
def calculate():
    """Calculate potential winnings from bet slip."""
    data = request.get_json()
    selections = data.get('selections', [])
    stake = float(data.get('stake', 0))

    if not selections or stake <= 0:
        return jsonify({'total_odds': 0, 'potential': 0})

    total_odds = 1.0
    for sel in selections:
        match = Match.query.get(sel.get('match_id'))
        if match and match.main_odds:
            odds_val = getattr(match.main_odds, sel.get('type', 'home_win'), 1.0)
            if odds_val:
                total_odds *= odds_val

    total_odds = round(total_odds, 2)
    potential = round(stake * total_odds, 2)

    return jsonify({'total_odds': total_odds, 'potential': potential})