"""Sports listing routes."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Sport, League, Match
from app.sports import sports_bp
from app.constants import *


@sports_bp.route('/')
def index():
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.display_order).all()

    sport_data = []
    for sport in sports:
        match_count = Match.query.filter_by(sport_id=sport.id)\
            .filter(Match.status.in_([MATCH_SCHEDULED, MATCH_LIVE])).count()
        league_count = League.query.filter_by(sport_id=sport.id, is_active=True).count()
        sport_data.append({
            'sport': sport,
            'match_count': match_count,
            'league_count': league_count,
        })

    return render_template('sports/index.html', sport_data=sport_data)


@sports_bp.route('/<sport_slug>')
def detail(sport_slug):
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    leagues = League.query.filter_by(sport_id=sport.id, is_active=True).all()

    league_data = []
    for league in leagues:
        matches = Match.query.filter_by(league_id=league.id)\
            .filter(Match.status.in_([MATCH_SCHEDULED, MATCH_LIVE]))\
            .order_by(Match.match_date.asc()).all()
        league_data.append({'league': league, 'matches': matches})

    return render_template('sports/detail.html', sport=sport, league_data=league_data)