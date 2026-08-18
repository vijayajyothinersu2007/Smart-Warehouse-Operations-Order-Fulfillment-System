import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.seeder import seed_database
from backend.services.order_service import OrderService
from backend.services.decision_engine.allocation_engine import AllocationEngine
from backend.services.fulfillment_service import FulfillmentService
from backend.database.db import query_db

def test_complete_fulfillment_lifecycle():
    """
    Tests full gate-by-gate workflow:
    Created -> Priority -> Allocated -> Picking -> Packed -> QC Passed -> Dispatched -> Stock Deducted
    """
    seed_database()

    # 1. Create Order
    new_order = OrderService.create_order({
        "customer_name": "Test Labs Inc",
        "customer_tier": "EXPRESS",
        "sla_hours": 4.0,
        "items": [
            {"product_id": "SKU-ELEC-02", "quantity": 2}
        ]
    })
    order_id = new_order['id']
    assert new_order['status'] == 'PENDING'
    assert new_order['priority_score'] > 0

    # Check stock before
    stock_before = query_db("""
        SELECT SUM(quantity_on_hand) as on_hand, SUM(quantity_reserved) as reserved 
        FROM inventory_stock WHERE product_id = 'SKU-ELEC-02'
    """, one=True)
    initial_on_hand = stock_before['on_hand']

    # 2. Stock Allocation
    alloc_res = AllocationEngine.run_allocation_for_all_pending()
    order_allocated = OrderService.get_order_details(order_id)
    assert order_allocated['status'] == 'ALLOCATED'
    assert order_allocated['allocation_status'] == 'ALLOCATED_FULL'

    # 3. Floor Picking
    pick_res = FulfillmentService.advance_order_stage(order_id, target_stage='PICKING')
    assert pick_res['current_stage'] == 'PICKING'

    # 4. Packing
    pack_res = FulfillmentService.advance_order_stage(order_id, target_stage='PACKED')
    assert pack_res['current_stage'] == 'PACKED'

    # 5. Quality Check
    qc_res = FulfillmentService.advance_order_stage(order_id, target_stage='QC_PASSED', extra_data={"measured_weight_kg": 0.8})
    assert qc_res['current_stage'] == 'QC_PASSED'

    # 6. Dispatch (Should deduct physical inventory)
    disp_res = FulfillmentService.advance_order_stage(order_id, target_stage='DISPATCHED')
    assert disp_res['current_stage'] == 'DISPATCHED'

    # 7. Verify Inventory Depletion
    stock_after = query_db("""
        SELECT SUM(quantity_on_hand) as on_hand, SUM(quantity_reserved) as reserved 
        FROM inventory_stock WHERE product_id = 'SKU-ELEC-02'
    """, one=True)
    
    assert stock_after['on_hand'] == initial_on_hand - 2

    # Verify Dispatch Record
    disp_record = query_db("SELECT * FROM dispatches WHERE order_id = ?", (order_id,), one=True)
    assert disp_record is not None
    assert disp_record['tracking_number'].startswith('TRK-')

    print("\n[PASS] End-to-End Fulfillment Lifecycle Test Passed!")

if __name__ == '__main__':
    test_complete_fulfillment_lifecycle()
