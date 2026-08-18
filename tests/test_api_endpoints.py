import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.database.seeder import seed_database

def test_all_api_endpoints():
    app = create_app()
    client = app.test_client()

    print("\n--- Testing API Endpoints ---")

    # 1. Test Home page
    r = client.get('/')
    assert r.status_code == 200
    assert b'WarehouseIQ' in r.data
    print("[PASS] GET / (Dashboard HTML)")

    # 2. Test Reset Demo
    r = client.post('/api/system/reset-demo')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    print("[PASS] POST /api/system/reset-demo")

    # 3. Test Dashboard Summary
    r = client.get('/api/analytics/dashboard')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    assert 'total_orders' in data['summary']
    assert 'fulfillment_rate' in data['summary']
    print(f"[PASS] GET /api/analytics/dashboard -> {data['summary']['total_orders']} orders")

    # 4. Test Analytics Metrics
    r = client.get('/api/analytics/metrics')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    assert 'status_distribution' in data['metrics']
    print("[PASS] GET /api/analytics/metrics")

    # 5. Test Orders List
    r = client.get('/api/orders')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    assert data['count'] > 0
    print(f"[PASS] GET /api/orders -> {data['count']} orders returned")

    # 6. Test Inventory List & Bins
    r = client.get('/api/inventory')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    assert data['count'] > 0
    print(f"[PASS] GET /api/inventory -> {data['count']} SKUs")

    r = client.get('/api/inventory/bins')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    print(f"[PASS] GET /api/inventory/bins -> {data['count']} bins")

    # 7. Test Stock Contention Simulation
    r = client.post('/api/allocation/simulate-contention')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    assert data['scenario']['sku'] == 'SKU-DRONE-4K'
    assert len(data['allocation_result']['decisions']) > 0
    print(f"[PASS] POST /api/allocation/simulate-contention -> Decision: {data['allocation_result']['decisions'][0]['decision_action']}")

    # 8. Test Decisions Feed
    r = client.get('/api/decisions')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    assert data['count'] > 0
    print(f"[PASS] GET /api/decisions -> {data['count']} audit logs")

    # 9. Test Fulfillment Board
    r = client.get('/api/fulfillment/board')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    assert 'ALLOCATED' in data['board']
    print("[PASS] GET /api/fulfillment/board")

    # 10. Test Exceptions List
    r = client.get('/api/exceptions')
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data['success'] is True
    print(f"[PASS] GET /api/exceptions -> {data['count']} exceptions")

    print("\n[ALL API TESTS PASSED SUCCESSFULLY!]")

if __name__ == '__main__':
    test_all_api_endpoints()
