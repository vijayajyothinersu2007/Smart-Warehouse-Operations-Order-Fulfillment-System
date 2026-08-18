import os
import sys
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.db import query_db
from backend.database.seeder import seed_database
from backend.services.decision_engine.allocation_engine import AllocationEngine
from backend.services.order_service import OrderService

def test_mandatory_stock_contention_scenario():
    """
    Validates the core hackathon requirement:
    - Order A: URGENT, demands 10 units of SKU-DRONE-4K
    - Order B: NORMAL, demands 5 units of SKU-DRONE-4K
    - Available: 7 units
    - Expected decision:
      - All 7 units allocated to Order A (partial 7/10)
      - Order B queued as BACKORDERED (0/5)
      - Decision Card generated with detailed factors and rejected alternatives
    """
    # 1. Seed baseline state
    seed_database()

    # 2. Verify pre-allocation state
    stock_before = query_db("""
        SELECT (quantity_on_hand - quantity_reserved - quantity_damaged) as available 
        FROM inventory_stock WHERE product_id = 'SKU-DRONE-4K'
    """, one=True)
    assert stock_before['available'] == 7, f"Expected 7 available units, got {stock_before['available']}"

    order_a = OrderService.get_order_details('ORD-URGENT-001')
    order_b = OrderService.get_order_details('ORD-NORM-002')
    
    assert order_a['customer_tier'] == 'URGENT'
    assert order_a['items'][0]['quantity_requested'] == 10
    assert order_a['items'][0]['quantity_allocated'] == 0

    assert order_b['customer_tier'] == 'NORMAL'
    assert order_b['items'][0]['quantity_requested'] == 5
    assert order_b['items'][0]['quantity_allocated'] == 0

    # 3. Execute Autonomous Stock Allocation Engine
    res = AllocationEngine.run_allocation_for_all_pending()
    assert res['allocations_count'] > 0
    assert len(res['decisions']) > 0

    # 4. Verify post-allocation state of Order A (VIP/Urgent)
    order_a_post = OrderService.get_order_details('ORD-URGENT-001')
    assert order_a_post['allocation_status'] == 'ALLOCATED_PARTIAL'
    assert order_a_post['items'][0]['quantity_allocated'] == 7
    assert order_a_post['items'][0]['status'] == 'ALLOCATED_PARTIAL'

    # 5. Verify post-allocation state of Order B (Normal)
    order_b_post = OrderService.get_order_details('ORD-NORM-002')
    assert order_b_post['allocation_status'] == 'BACKORDERED'
    assert order_b_post['items'][0]['quantity_allocated'] == 0
    assert order_b_post['items'][0]['status'] == 'BACKORDERED'

    # 6. Verify Explainable Decision Card Log
    decision_log = query_db("""
        SELECT * FROM decision_audit_logs 
        WHERE decision_type = 'CONTENTION_RESOLUTION'
        ORDER BY executed_at DESC
    """, one=True)

    assert decision_log is not None
    assert decision_log['confidence_score'] >= 0.90
    assert 'ORD-URGENT-001' in decision_log['rationale']
    assert 'SKU-DRONE-4K' in decision_log['rationale']

    factors = json.loads(decision_log['factors_json'])
    assert factors['total_demanded'] == 15
    assert factors['total_available'] == 7
    assert factors['shortage_gap'] == 8

    alternatives = json.loads(decision_log['alternatives_json'])
    assert len(alternatives) > 0
    assert any("equal" in a['alternative'].lower() or "split" in a['alternative'].lower() for a in alternatives)
    assert any(a['status'] == 'REJECTED' for a in alternatives)

    print("\n[PASS] Stock Contention Scenario Test Passed Perfectly!")
    print(f"Decision Action: {decision_log['decision_action']}")
    print(f"Rationale: {decision_log['rationale']}")

if __name__ == '__main__':
    test_mandatory_stock_contention_scenario()
