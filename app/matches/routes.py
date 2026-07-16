"""Match listing and detail routes."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Match, Odds, Sport, League
from app.matches import matches_bp
from app.constants import *


@matches_bp.route('/')
def index():
    sport_slug = request.args.get('sport')
    status = request.args.get('status', 'upcoming')
    date_filter = request.args.get('date')

    query = Match.query

    if sport_slug:
        sport = Sport.query.filter_by(slug=sport_slug).first()
        if sport:
            query = query.filter_by(sport_id=sport.id)

    if status == 'live':
        query = query.filter_by(is_live=True, status=MATCH_LIVE)
    elif status == 'upcoming':
        query = query.filter(Match.status.in_([MATCH_SCHEDULED]))
    elif status == 'finished':
        query = query.filter_by(status=MATCH_FINISHED)

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
            day_end = filter_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Match.match_date.between(filter_date, day_end))
        except ValueError:
            pass

    matches = query.order_by(Match.is_live.desc(), Match.match_date.asc()).all()
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.display_order).all()

    # Organize by league
    leagues = {}
    for match in matches:
        league_name = match.league.name if match.league else 'Unknown'
        if league_name not in leagues:
            leagues[league_name] = []
        leagues[league_name].append(match)

    return render_template('matches/index.html', matches=matches,
                         leagues=leagues, sports=sports,
                         current_sport=sport_slug, current_status=status)


@matches_bp.route('/<int:match_id>')
def detail(match_id):
    match = Match.query.get_or_404(match_id)
    odds = match.main_odds
    return render_template('matches/detail.html', match=match, odds=odds)