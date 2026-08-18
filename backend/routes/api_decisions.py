import json
from flask import Blueprint, jsonify, request
from backend.database.db import query_db

bp_decisions = Blueprint('decisions', __name__, url_prefix='/api/decisions')

@bp_decisions.route('', methods=['GET'])
def get_decisions():
    entity_id = request.args.get('entity_id')
    decision_type = request.args.get('decision_type')
    limit = int(request.args.get('limit', 20))

    query = "SELECT * FROM decision_audit_logs"
    params = []
    clauses = []

    if entity_id:
        clauses.append("(entity_id = ? OR rationale LIKE ?)")
        params.extend([entity_id, f"%{entity_id}%"])
    if decision_type:
        clauses.append("decision_type = ?")
        params.append(decision_type)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY executed_at DESC LIMIT ?"
    params.append(limit)

    logs = query_db(query, params)
    for log in logs:
        try:
            log['factors'] = json.loads(log['factors_json'])
        except Exception:
            log['factors'] = {}
        try:
            log['alternatives'] = json.loads(log['alternatives_json'])
        except Exception:
            log['alternatives'] = []

    return jsonify({"success": True, "count": len(logs), "decisions": logs})

@bp_decisions.route('/<int:decision_id>', methods=['GET'])
def get_decision(decision_id):
    log = query_db("SELECT * FROM decision_audit_logs WHERE id = ?", (decision_id,), one=True)
    if not log:
        return jsonify({"success": False, "error": f"Decision #{decision_id} not found"}), 404
    try:
        log['factors'] = json.loads(log['factors_json'])
        log['alternatives'] = json.loads(log['alternatives_json'])
    except Exception:
        log['factors'] = {}
        log['alternatives'] = []
    return jsonify({"success": True, "decision": log})
