from flask import Blueprint, jsonify, request
from backend.database.db import query_db, execute_db
from backend.services.decision_engine.exception_triage import ExceptionTriageEngine

bp_exceptions = Blueprint('exceptions', __name__, url_prefix='/api/exceptions')

@bp_exceptions.route('', methods=['GET'])
def get_exceptions():
    status = request.args.get('status')
    query = """
        SELECT e.*, p.name as product_name, o.customer_name
        FROM exceptions_log e
        LEFT JOIN products p ON e.product_id = p.id
        LEFT JOIN orders o ON e.order_id = o.id
    """
    params = []
    if status:
        query += " WHERE e.status = ?"
        params.append(status)
    query += " ORDER BY e.created_at DESC"
    
    exceptions = query_db(query, params)
    return jsonify({"success": True, "count": len(exceptions), "exceptions": exceptions})

@bp_exceptions.route('/report-damaged', methods=['POST'])
def report_damaged():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    bin_id = data.get('bin_id')
    damaged_qty = int(data.get('damaged_qty', 1))
    order_id = data.get('order_id')
    reported_by = data.get('reported_by', 'Floor Operator')

    if not product_id or not bin_id:
        return jsonify({"success": False, "error": "product_id and bin_id are required"}), 400

    try:
        res = ExceptionTriageEngine.report_damaged_item(
            product_id=product_id,
            bin_id=bin_id,
            damaged_qty=damaged_qty,
            order_id=order_id,
            reported_by=reported_by
        )
        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp_exceptions.route('/report-missing', methods=['POST'])
def report_missing():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    bin_id = data.get('bin_id')
    order_id = data.get('order_id')
    reported_by = data.get('reported_by', 'Floor Operator')

    if not product_id or not bin_id:
        return jsonify({"success": False, "error": "product_id and bin_id are required"}), 400

    try:
        res = ExceptionTriageEngine.report_missing_item(
            product_id=product_id,
            bin_id=bin_id,
            order_id=order_id,
            reported_by=reported_by
        )
        return jsonify({"success": True, "result": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp_exceptions.route('/<int:exc_id>/resolve', methods=['POST'])
def resolve_exception(exc_id):
    data = request.get_json() or {}
    applied_resolution = data.get('applied_resolution', 'Manually resolved by supervisor.')
    resolved_by = data.get('resolved_by', 'Warehouse Supervisor')

    execute_db("""
        UPDATE exceptions_log 
        SET status = 'RESOLVED', applied_resolution = ?, resolved_by = ?, resolved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (applied_resolution, resolved_by, exc_id))

    return jsonify({"success": True, "message": f"Exception #{exc_id} marked as resolved."})
