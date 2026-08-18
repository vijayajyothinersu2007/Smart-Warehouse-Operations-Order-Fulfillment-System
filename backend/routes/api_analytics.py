from flask import Blueprint, jsonify
from backend.services.analytics_service import AnalyticsService

bp_analytics = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@bp_analytics.route('/dashboard', methods=['GET'])
def get_dashboard_summary():
    summary = AnalyticsService.get_dashboard_summary()
    return jsonify({"success": True, "summary": summary})

@bp_analytics.route('/metrics', methods=['GET'])
def get_analytics_metrics():
    metrics = AnalyticsService.get_analytics_metrics()
    return jsonify({"success": True, "metrics": metrics})
