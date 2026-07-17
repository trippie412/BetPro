"""REST API routes for external integrations."""
from flask import jsonify, request, current_app
from app import db
from app.models import Match, Odds, Sport, League, User, Bet
from app.api import api_bp
from app.constants import *
from datetime import datetime, timezone
import hashlib
import hmac


@api_bp.route('/matches')
def get_matches():
    sport = request.args.get('sport')
    status = request.args.get('status', MATCH_SCHEDULED)

    query = Match.query
    if sport:
        sport_obj = Sport.query.filter_by(slug=sport).first()
        if sport_obj:
            query = query.filter_by(sport_id=sport_obj.id)
    if status:
        query = query.filter_by(status=status)

    matches = query.order_by(Match.match_date.asc()).all()

    return jsonify({
        'success': True,
        'count': len(matches),
        'matches': [{
            'id': m.id,
            'sport': m.sport.name if m.sport else None,
            'league': m.league.name if m.league else None,
            'home_team': m.home_team,
            'away_team': m.away_team,
            'match_date': m.match_date.isoformat(),
            'status': m.status,
            'is_live': m.is_live,
            'odds': {
                'home_win': m.main_odds.home_win if m.main_odds else None,
                'draw': m.main_odds.draw if m.main_odds else None,
                'away_win': m.main_odds.away_win if m.main_odds else None,
            } if m.main_odds else None
        } for m in matches]
    })


@api_bp.route('/matches/<int:match_id>')
def get_match(match_id):
    match = Match.query.get_or_404(match_id)
    return jsonify({
        'success': True,
        'match': {
            'id': match.id,
            'sport': match.sport.name if match.sport else None,
            'league': match.league.name if match.league else None,
            'home_team': match.home_team,
            'away_team': match.away_team,
            'home_score': match.home_score,
            'away_score': match.away_score,
            'match_date': match.match_date.isoformat(),
            'status': match.status,
            'is_live': match.is_live,
            'is_featured': match.is_featured,
        }
    })


@api_bp.route('/sports')
def get_sports():
    sports = Sport.query.filter_by(is_active=True).order_by(Sport.display_order).all()
    return jsonify({
        'success': True,
        'sports': [{'id': s.id, 'name': s.name, 'slug': s.slug, 'icon': s.icon} for s in sports]
    })


@api_bp.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0'
    })
    
from app.services import LiveDataService

@api_bp.route("/sync-matches")
def sync_matches():
    imported = LiveDataService.sync_matches_to_db()

    return jsonify({
        "success": True,
        "imported": imported
    })