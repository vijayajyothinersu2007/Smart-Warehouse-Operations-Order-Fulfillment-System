from flask import Blueprint, jsonify, request
from backend.services.inventory_service import InventoryService

bp_inventory = Blueprint('inventory', __name__, url_prefix='/api/inventory')

@bp_inventory.route('', methods=['GET'])
def get_inventory():
    items = InventoryService.get_inventory_list()
    return jsonify({"success": True, "count": len(items), "inventory": items})

@bp_inventory.route('/<sku>', methods=['GET'])
def get_product(sku):
    product = InventoryService.get_product_details(sku)
    if not product:
        return jsonify({"success": False, "error": f"Product {sku} not found"}), 404
    return jsonify({"success": True, "product": product})

@bp_inventory.route('/bins', methods=['GET'])
def get_bins():
    bins = InventoryService.get_all_bins()
    return jsonify({"success": True, "count": len(bins), "bins": bins})

@bp_inventory.route('/adjust', methods=['POST'])
def adjust_stock():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    bin_id = data.get('bin_id')
    quantity = data.get('quantity_on_hand')

    if not product_id or not bin_id or quantity is None:
        return jsonify({"success": False, "error": "product_id, bin_id, and quantity_on_hand are required"}), 400

    try:
        InventoryService.adjust_stock(product_id, bin_id, int(quantity))
        return jsonify({"success": True, "message": f"Stock adjusted for {product_id} in {bin_id} to {quantity} units."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
