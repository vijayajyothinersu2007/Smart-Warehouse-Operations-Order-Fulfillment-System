import os
import sys
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.seeder import seed_database
from backend.services.decision_engine.priority_scorer import PriorityScorer
from backend.services.decision_engine.exception_triage import ExceptionTriageEngine
from backend.database.db import query_db

def test_priority_scorer_calculation():
    now = datetime.now()
    urgent_sla = (now + timedelta(hours=1.0)).strftime("%Y-%m-%d %H:%M:%S")
    normal_sla = (now + timedelta(hours=24.0)).strftime("%Y-%m-%d %H:%M:%S")

    score_urgent = PriorityScorer.calculate_score({
        "customer_tier": "URGENT",
        "is_urgent": 1,
        "target_sla_cutoff": urgent_sla,
        "total_amount": 5000.00
    })

    score_normal = PriorityScorer.calculate_score({
        "customer_tier": "NORMAL",
        "is_urgent": 0,
        "target_sla_cutoff": normal_sla,
        "total_amount": 250.00
    })

    assert score_urgent['priority_score'] > score_normal['priority_score']
    assert score_urgent['priority_score'] >= 85.0
    assert score_normal['priority_score'] <= 60.0
    assert score_urgent['factors']['is_critical_escalated'] is True
    print("\n[PASS] Priority Scorer Test Passed!")

def test_exception_damaged_item_quarantine():
    seed_database()

    # Report 2 damaged units in BIN-A-01-01-2 for SKU-ELEC-01
    res = ExceptionTriageEngine.report_damaged_item(
        product_id='SKU-ELEC-01',
        bin_id='BIN-A-01-01-2',
        damaged_qty=2,
        reported_by='Test Runner'
    )

    assert res is not None
    assert 'DAMAGED' in res['description']

    # Verify inventory was updated
    stock = query_db("""
        SELECT * FROM inventory_stock 
        WHERE product_id = 'SKU-ELEC-01' AND bin_id = 'BIN-A-01-01-2'
    """, one=True)
    assert stock['quantity_damaged'] == 2

    print("\n[PASS] Damaged Item Triage & Quarantine Test Passed!")

if __name__ == '__main__':
    test_priority_scorer_calculation()
    test_exception_damaged_item_quarantine()
