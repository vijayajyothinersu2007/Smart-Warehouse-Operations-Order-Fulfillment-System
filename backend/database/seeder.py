import os
import json
from datetime import datetime, timedelta
from backend.database.db import init_db, get_db, execute_db
from backend.services.decision_engine.priority_scorer import PriorityScorer

def seed_database():
    """
    Populates SQLite database with rich realistic warehouse data,
    specifically configuring the mandatory Stock Contention Scenario (Order A vs Order B).
    """
    init_db()

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    with get_db() as conn:
        cur = conn.cursor()

        # ==========================================
        # 1. SEED WAREHOUSE BINS (Zones A, B, C, D)
        # ==========================================
        bins_data = []
        zones = [
            ('Zone A', 'Fast-Mover High-Tech Electronics'),
            ('Zone B', 'Apparel & Safety Gear'),
            ('Zone C', 'Heavy Hardware & Fasteners'),
            ('Zone D', 'Perishables & Cold Chain')
        ]

        for z_idx, (zone_name, desc) in enumerate(zones):
            for aisle in range(1, 4):
                for rack in range(1, 3):
                    for shelf in range(1, 3):
                        bin_id = f"BIN-{zone_name[-1]}-{aisle:02d}-{rack:02d}-{shelf}"
                        coord_x = round((z_idx * 20.0) + (aisle * 5.0) + (rack * 1.5), 1)
                        coord_y = round((shelf * 2.0) + (rack * 3.0), 1)
                        bins_data.append((bin_id, zone_name, aisle, rack, shelf, 1, coord_x, coord_y, 150, 1))

        cur.executemany("""
            INSERT INTO inventory_bins (id, zone, aisle, rack, shelf, bin_number, coord_x, coord_y, max_capacity_units, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, bins_data)

        # ==========================================
        # 2. SEED PRODUCTS MASTER
        # ==========================================
        products = [
            # The Contention SKU
            ('SKU-DRONE-4K', 'Industrial Inspection Drone 4K', 'Electronics', 899.00, 1.8, 'BAR-DRN-001', 5, 12),
            
            # Other SKUs
            ('SKU-ELEC-01', 'Lithium Power Station 500W', 'Electronics', 450.00, 5.2, 'BAR-LIT-002', 4, 10),
            ('SKU-ELEC-02', 'Wireless Rugged Barcode Scanner', 'Electronics', 140.00, 0.4, 'BAR-SCN-003', 10, 20),
            ('SKU-APPR-01', 'Hi-Vis Thermal Warehouse Parka', 'Apparel', 75.00, 0.9, 'BAR-JCK-004', 15, 30),
            ('SKU-APPR-02', 'Reinforced Steel-Toe Boots (Size 10)', 'Apparel', 110.00, 1.6, 'BAR-BOT-005', 8, 18),
            ('SKU-HARD-01', 'Heavy Duty Pallet Strapping Kit', 'Hardware', 45.00, 4.0, 'BAR-STR-006', 12, 25),
            ('SKU-HARD-02', 'Industrial Hydraulic Seal Pack', 'Hardware', 88.00, 0.6, 'BAR-HYD-007', 10, 20),
            ('SKU-PERI-01', 'Cold-Chain Diagnostic Serum Kit', 'Perishables', 320.00, 1.2, 'BAR-MED-008', 6, 15),
            ('SKU-PERI-02', 'High-Protein Nutrient Concentrate', 'Perishables', 38.00, 1.5, 'BAR-NUT-009', 20, 45)
        ]

        cur.executemany("""
            INSERT INTO products (id, name, category, unit_price, weight_kg, barcode, min_safety_stock, reorder_point)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, products)

        # ==========================================
        # 3. SEED INVENTORY STOCK
        # ==========================================
        # CRITICAL CONTENTION SETUP:
        # SKU-DRONE-4K has EXACTLY 7 available units in BIN-A-01-01-1 (0 reserved, 0 damaged).
        stock_entries = [
            # Contention SKU
            ('SKU-DRONE-4K', 'BIN-A-01-01-1', 7, 0, 0),
            
            # Other SKUs with healthy and low stocks
            ('SKU-ELEC-01', 'BIN-A-01-01-2', 15, 3, 0),
            ('SKU-ELEC-02', 'BIN-A-02-01-1', 45, 5, 0),
            ('SKU-APPR-01', 'BIN-B-01-01-1', 50, 8, 2),  # 2 damaged
            ('SKU-APPR-02', 'BIN-B-02-01-1', 22, 4, 0),
            ('SKU-HARD-01', 'BIN-C-01-01-1', 8, 2, 0),   # Low stock
            ('SKU-HARD-02', 'BIN-C-02-01-1', 35, 0, 0),
            ('SKU-PERI-01', 'BIN-D-01-01-1', 14, 4, 0),
            ('SKU-PERI-02', 'BIN-D-02-01-1', 60, 10, 0)
        ]

        cur.executemany("""
            INSERT INTO inventory_stock (product_id, bin_id, quantity_on_hand, quantity_reserved, quantity_damaged)
            VALUES (?, ?, ?, ?, ?)
        """, stock_entries)

        # ==========================================
        # 4. SEED ORDERS INCLUDING CONTENTION SCENARIO
        # ==========================================
        # Mandatory Contention Scenario:
        # Order A: Priority URGENT, Required 10 units of SKU-DRONE-4K
        # Order B: Priority NORMAL, Required 5 units of SKU-DRONE-4K
        # Available: 7 units

        sla_urgent = (now + timedelta(hours=1.5)).strftime("%Y-%m-%d %H:%M:%S")
        sla_normal = (now + timedelta(hours=18.0)).strftime("%Y-%m-%d %H:%M:%S")
        sla_standard = (now + timedelta(hours=8.0)).strftime("%Y-%m-%d %H:%M:%S")

        # Compute priority scores
        score_a = PriorityScorer.calculate_score({
            "customer_tier": "URGENT",
            "is_urgent": 1,
            "target_sla_cutoff": sla_urgent,
            "total_amount": 8990.00
        })

        score_b = PriorityScorer.calculate_score({
            "customer_tier": "NORMAL",
            "is_urgent": 0,
            "target_sla_cutoff": sla_normal,
            "total_amount": 4495.00
        })

        orders = [
            # Order A (Contention Primary - Urgent VIP)
            ('ORD-URGENT-001', 'Apex Aerospace & Defense (VIP)', 'URGENT', 'New York Hub', 'PENDING', score_a['priority_score'], 1, sla_urgent, 8990.00, 18.0, 'UNALLOCATED', now_str),
            
            # Order B (Contention Secondary - Normal)
            ('ORD-NORM-002', 'Metro Commercial Tech Store', 'NORMAL', 'Chicago Depot', 'PENDING', score_b['priority_score'], 0, sla_normal, 4495.00, 9.0, 'UNALLOCATED', now_str),

            # Other pre-existing fulfillment orders
            ('ORD-FULFILL-101', 'Quantum Diagnostics Lab', 'VIP', 'Boston Medical Center', 'ALLOCATED', 88.5, 1, (now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"), 1280.00, 4.8, 'ALLOCATED_FULL', now_str),
            ('ORD-FULFILL-102', 'Summit Outfitters', 'EXPRESS', 'Denver Regional', 'PICKING', 76.2, 0, (now + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"), 495.00, 5.2, 'ALLOCATED_FULL', now_str),
            ('ORD-FULFILL-103', 'Nordic Logistics Supply', 'STANDARD', 'Seattle Port', 'PACKED', 62.0, 0, (now + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"), 850.00, 8.4, 'ALLOCATED_FULL', now_str),
            ('ORD-FULFILL-104', 'Global Infrastructure Corp', 'STANDARD', 'Dallas Distribution', 'DISPATCHED', 58.0, 0, (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), 1780.00, 12.0, 'ALLOCATED_FULL', (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"))
        ]

        cur.executemany("""
            INSERT INTO orders (id, customer_name, customer_tier, destination_city, status, priority_score, is_urgent, target_sla_cutoff, total_amount, total_weight_kg, allocation_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, orders)

        # ==========================================
        # 5. SEED ORDER ITEMS
        # ==========================================
        order_items = [
            # Contention Items
            ('ORD-URGENT-001', 'SKU-DRONE-4K', 10, 0, 0, 'PENDING'),
            ('ORD-NORM-002', 'SKU-DRONE-4K', 5, 0, 0, 'PENDING'),

            # Other Items
            ('ORD-FULFILL-101', 'SKU-PERI-01', 4, 4, 0, 'ALLOCATED_FULL'),
            ('ORD-FULFILL-102', 'SKU-APPR-01', 3, 3, 3, 'PICKED'),
            ('ORD-FULFILL-102', 'SKU-APPR-02', 2, 2, 2, 'PICKED'),
            ('ORD-FULFILL-103', 'SKU-ELEC-02', 5, 5, 5, 'PICKED'),
            ('ORD-FULFILL-104', 'SKU-ELEC-01', 3, 3, 3, 'PICKED')
        ]

        cur.executemany("""
            INSERT INTO order_items (order_id, product_id, quantity_requested, quantity_allocated, quantity_picked, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, order_items)

        # ==========================================
        # 6. SEED ALLOCATIONS & FULFILLMENT RECORDS
        # ==========================================
        # Allocations for ORD-FULFILL-101
        cur.execute("""
            INSERT INTO allocations (order_id, order_item_id, product_id, bin_id, quantity_allocated, allocation_status)
            VALUES ('ORD-FULFILL-101', 3, 'SKU-PERI-01', 'BIN-D-01-01-1', 4, 'ACTIVE')
        """)

        # Allocations for ORD-FULFILL-102
        cur.execute("""
            INSERT INTO allocations (order_id, order_item_id, product_id, bin_id, quantity_allocated, allocation_status)
            VALUES ('ORD-FULFILL-102', 4, 'SKU-APPR-01', 'BIN-B-01-01-1', 3, 'ACTIVE')
        """)
        cur.execute("""
            INSERT INTO allocations (order_id, order_item_id, product_id, bin_id, quantity_allocated, allocation_status)
            VALUES ('ORD-FULFILL-102', 5, 'SKU-APPR-02', 'BIN-B-02-01-1', 2, 'ACTIVE')
        """)

        # Fulfillment stages
        fulfillment_rows = [
            ('ORD-URGENT-001', 'PENDING', None, None, None, 18.0, None, 'PENDING'),
            ('ORD-NORM-002', 'PENDING', None, None, None, 9.0, None, 'PENDING'),
            ('ORD-FULFILL-101', 'ALLOCATED', None, None, None, 4.8, None, 'PENDING'),
            ('ORD-FULFILL-102', 'PICKING', 'Picker Marcus (Zone B)', None, None, 5.2, None, 'PENDING'),
            ('ORD-FULFILL-103', 'PACKED', 'Picker Marcus (Zone A)', 'Packer Station #2', 'QC Inspector Sarah', 8.4, 8.4, 'PASSED'),
            ('ORD-FULFILL-104', 'DISPATCHED', 'Picker Sarah', 'Packer Station #1', 'QC Inspector Sarah', 12.0, 12.0, 'PASSED')
        ]

        cur.executemany("""
            INSERT INTO fulfillment_status (order_id, current_stage, picker_name, packer_name, qc_inspector, target_weight_kg, measured_weight_kg, qc_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, fulfillment_rows)

        # Dispatch for 104
        cur.execute("""
            INSERT INTO dispatches (id, order_id, carrier_name, tracking_number, dock_door, dispatched_at)
            VALUES ('DISP-5012', 'ORD-FULFILL-104', 'FedEx Express Freight', 'TRK-98452109', 'Dock Door #01', ?)
        """, ((now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),))

        # ==========================================
        # 7. SEED INITIAL EXCEPTIONS & DECISION LOGS
        # ==========================================
        cur.execute("""
            INSERT INTO exceptions_log 
            (exception_type, severity, order_id, product_id, bin_id, status, description, proposed_resolution, applied_resolution, resolved_by)
            VALUES ('DAMAGED_ITEM', 'MEDIUM', NULL, 'SKU-APPR-01', 'BIN-B-01-01-1', 'OPEN', 
                    '2 unit(s) of Hi-Vis Thermal Warehouse Parka found with torn stitching in Bin BIN-B-01-01-1.',
                    'Quarantine 2 units and deduct from available pick stock.', NULL, NULL)
        """)

        # Priority Scoring Decision Logs for Order A and B
        cur.execute("""
            INSERT INTO decision_audit_logs 
            (decision_type, entity_id, decision_action, confidence_score, rationale, factors_json, alternatives_json, recommended_action)
            VALUES ('PRIORITY_SCORING', 'ORD-URGENT-001', 'ASSIGN_URGENT_PRIORITY', 0.98,
                    ?, ?, '[]', 'Prioritize immediate stock allocation to protect VIP SLA.')
        """, (score_a['rationale'], json.dumps(score_a['factors'])))

        cur.execute("""
            INSERT INTO decision_audit_logs 
            (decision_type, entity_id, decision_action, confidence_score, rationale, factors_json, alternatives_json, recommended_action)
            VALUES ('PRIORITY_SCORING', 'ORD-NORM-002', 'ASSIGN_STANDARD_PRIORITY', 0.95,
                    ?, ?, '[]', 'Queue for standard allocation sequence.')
        """, (score_b['rationale'], json.dumps(score_b['factors'])))

    print("Database seeded successfully with Contention Scenario and realistic warehouse operational state!")

if __name__ == '__main__':
    seed_database()
