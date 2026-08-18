from flask import Blueprint, render_template, jsonify
from backend.database.seeder import seed_database

bp_views = Blueprint('views', __name__)

@bp_views.route('/')
def index():
    return render_template('index.html')

@bp_views.route('/api/system/reset-demo', methods=['POST'])
def reset_demo():
    try:
        seed_database()
        return jsonify({"success": True, "message": "WarehouseIQ environment re-seeded to initial hackathon state with Contention Scenario."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
