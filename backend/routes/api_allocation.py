from flask import Blueprint, jsonify, request
from backend.services.decision_engine.allocation_engine import AllocationEngine
from backend.database.seeder import seed_database

bp_allocation = Blueprint('allocation', __name__, url_prefix='/api/allocation')

@bp_allocation.route('/run', methods=['POST'])
def run_allocation():
    try:
        result = AllocationEngine.run_allocation_for_all_pending()
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp_allocation.route('/simulate-contention', methods=['POST'])
def simulate_contention():
    """
    Ensures the Stock Contention Scenario (Order A: Urgent 10 units, Order B: Normal 5 units, Available: 7 units)
    is loaded and executes the Decision Engine allocation to generate and return the explainable Decision Card.
    """
    try:
        # Re-seed to ensure baseline state if needed
        seed_database()
        
        # Run allocation engine
        result = AllocationEngine.run_allocation_for_all_pending()
        
        return jsonify({
            "success": True,
            "scenario": {
                "sku": "SKU-DRONE-4K",
                "product_name": "Industrial Inspection Drone 4K",
                "order_a": {
                    "id": "ORD-URGENT-001",
                    "priority": "URGENT",
                    "tier": "VIP",
                    "demanded": 10,
                    "allocated": 7,
                    "status": "ALLOCATED_PARTIAL"
                },
                "order_b": {
                    "id": "ORD-NORM-002",
                    "priority": "NORMAL",
                    "tier": "NORMAL",
                    "demanded": 5,
                    "allocated": 0,
                    "status": "BACKORDERED"
                },
                "available_stock": 7
            },
            "allocation_result": result
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
