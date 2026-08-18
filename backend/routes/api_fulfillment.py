from flask import Blueprint, jsonify, request
from backend.services.fulfillment_service import FulfillmentService

bp_fulfillment = Blueprint('fulfillment', __name__, url_prefix='/api/fulfillment')

@bp_fulfillment.route('/board', methods=['GET'])
def get_board():
    board = FulfillmentService.get_fulfillment_board()
    return jsonify({"success": True, "board": board})

@bp_fulfillment.route('/advance', methods=['POST'])
def advance_order():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    target_stage = data.get('target_stage')
    extra_data = data.get('extra_data', {})

    if not order_id:
        return jsonify({"success": False, "error": "order_id is required"}), 400

    try:
        res = FulfillmentService.advance_order_stage(order_id, target_stage=target_stage, extra_data=extra_data)
        if "error" in res:
            return jsonify({"success": False, **res}), 400
        return jsonify({"success": True, **res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
