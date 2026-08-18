from flask import Blueprint, jsonify, request
from backend.services.order_service import OrderService

bp_orders = Blueprint('orders', __name__, url_prefix='/api/orders')

@bp_orders.route('', methods=['GET'])
def get_orders():
    status = request.args.get('status')
    orders = OrderService.get_orders(status_filter=status)
    return jsonify({"success": True, "count": len(orders), "orders": orders})

@bp_orders.route('/<order_id>', methods=['GET'])
def get_order(order_id):
    order = OrderService.get_order_details(order_id)
    if not order:
        return jsonify({"success": False, "error": f"Order {order_id} not found"}), 404
    return jsonify({"success": True, "order": order})

@bp_orders.route('', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    try:
        new_order = OrderService.create_order(data)
        return jsonify({"success": True, "message": "Order created successfully", "order": new_order}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@bp_orders.route('/recalculate-priorities', methods=['POST'])
def recalculate_priorities():
    res = OrderService.recalculate_all_priorities()
    return jsonify({"success": True, **res})
