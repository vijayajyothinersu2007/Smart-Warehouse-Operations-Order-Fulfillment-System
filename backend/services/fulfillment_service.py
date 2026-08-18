import random
import json
from datetime import datetime
from backend.database.db import query_db, execute_db, get_db

class FulfillmentService:
    """
    Manages stage-by-stage physical fulfillment lifecycle:
    ALLOCATED -> PICKING -> PACKED -> QC_PASSED -> DISPATCHED (Stock Depleted)
    """

    STAGES_ORDER = ['PENDING', 'ALLOCATED', 'PICKING', 'PACKED', 'QC_PASSED', 'DISPATCHED']

    @staticmethod
    def get_fulfillment_board():
        """
        Returns categorized orders across all active fulfillment stages.
        """
        orders = query_db("""
            SELECT o.id, o.customer_name, o.customer_tier, o.status, o.priority_score, 
                   o.allocation_status, o.total_amount, o.total_weight_kg,
                   f.current_stage, f.qc_status, f.picker_name, f.packer_name,
                   d.tracking_number, d.carrier_name, d.dock_door
            FROM orders o
            LEFT JOIN fulfillment_status f ON o.id = f.order_id
            LEFT JOIN dispatches d ON o.id = d.order_id
            ORDER BY o.priority_score DESC
        """)
        board = {
            "ALLOCATED": [],
            "PICKING": [],
            "PACKED": [],
            "QC_PASSED": [],
            "DISPATCHED": []
        }
        for o in orders:
            stage = o['current_stage'] or o['status']
            if stage in board:
                board[stage].append(o)
            elif o['status'] == 'PENDING':
                board['ALLOCATED'].append(o)
        return board

    @staticmethod
    def advance_order_stage(order_id, target_stage=None, extra_data=None):
        """
        Advances an order to its next logical fulfillment stage or specified target stage.
        Deducts physical inventory upon final dispatch.
        """
        extra_data = extra_data or {}
        order = query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        if not order:
            return {"error": f"Order {order_id} not found."}

        fulfillment = query_db("SELECT * FROM fulfillment_status WHERE order_id = ?", (order_id,), one=True)
        current_stage = fulfillment['current_stage'] if fulfillment else (order['status'] or 'PENDING')

        # Determine next stage if not explicit
        if not target_stage:
            if current_stage in ['PENDING', 'UNALLOCATED']:
                target_stage = 'ALLOCATED'
            elif current_stage == 'ALLOCATED':
                target_stage = 'PICKING'
            elif current_stage == 'PICKING':
                target_stage = 'PACKED'
            elif current_stage == 'PACKED':
                target_stage = 'QC_PASSED'
            elif current_stage == 'QC_PASSED':
                target_stage = 'DISPATCHED'
            else:
                return {"message": f"Order is already at final stage {current_stage}."}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db() as conn:
            cur = conn.cursor()

            if target_stage == 'PICKING':
                picker_name = extra_data.get('picker_name', 'Picker Alpha (Station 1)')
                cur.execute("""
                    UPDATE fulfillment_status 
                    SET current_stage = 'PICKING', picker_name = ?, started_picking_at = ?, updated_at = ?
                    WHERE order_id = ?
                """, (picker_name, now_str, now_str, order_id))
                cur.execute("UPDATE orders SET status = 'PICKING' WHERE id = ?", (order_id,))
                
                # Mark line items as picked
                cur.execute("""
                    UPDATE order_items 
                    SET quantity_picked = quantity_allocated, status = 'PICKED'
                    WHERE order_id = ? AND quantity_allocated > 0
                """, (order_id,))

            elif target_stage == 'PACKED':
                packer_name = extra_data.get('packer_name', 'Packer Station #2')
                cur.execute("""
                    UPDATE fulfillment_status 
                    SET current_stage = 'PACKED', packer_name = ?, completed_picking_at = ?, completed_packing_at = ?, updated_at = ?
                    WHERE order_id = ?
                """, (packer_name, now_str, now_str, now_str, order_id))
                cur.execute("UPDATE orders SET status = 'PACKED' WHERE id = ?", (order_id,))

            elif target_stage == 'QC_PASSED':
                inspector = extra_data.get('qc_inspector', 'QC Lead Inspector')
                measured_weight = float(extra_data.get('measured_weight_kg', order['total_weight_kg'] or 1.2))
                cur.execute("""
                    UPDATE fulfillment_status 
                    SET current_stage = 'QC_PASSED', qc_inspector = ?, measured_weight_kg = ?, qc_status = 'PASSED', completed_qc_at = ?, updated_at = ?
                    WHERE order_id = ?
                """, (inspector, measured_weight, now_str, now_str, order_id))
                cur.execute("UPDATE orders SET status = 'PACKED' WHERE id = ?", (order_id,))

            elif target_stage == 'DISPATCHED':
                # Final gate: Deduct physical on-hand and reserved inventory from stock
                cur.execute("SELECT * FROM allocations WHERE order_id = ? AND allocation_status = 'ACTIVE'", (order_id,))
                active_allocations = [dict(r) for r in cur.fetchall()]

                for alloc in active_allocations:
                    qty = alloc['quantity_allocated']
                    pid = alloc['product_id']
                    bin_id = alloc['bin_id']

                    # Deduct physical stock
                    cur.execute("""
                        UPDATE inventory_stock 
                        SET quantity_on_hand = MAX(0, quantity_on_hand - ?),
                            quantity_reserved = MAX(0, quantity_reserved - ?),
                            last_audited_at = CURRENT_TIMESTAMP
                        WHERE product_id = ? AND bin_id = ?
                    """, (qty, qty, pid, bin_id))

                    # Mark allocation fulfilled
                    cur.execute("UPDATE allocations SET allocation_status = 'FULFILLED' WHERE id = ?", (alloc['id'],))

                # Register Dispatch Manifest
                carrier = extra_data.get('carrier_name', random.choice(['FedEx Express', 'DHL Supply Chain', 'UPS Ground']))
                tracking_num = f"TRK-{random.randint(10000000, 99999999)}"
                dock = random.choice(['Dock Door #01', 'Dock Door #02', 'Dock Door #03'])
                dispatch_id = f"DISP-{random.randint(1000, 9999)}"

                cur.execute("""
                    INSERT OR REPLACE INTO dispatches (id, order_id, carrier_name, tracking_number, dock_door, dispatched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (dispatch_id, order_id, carrier, tracking_num, dock, now_str))

                cur.execute("""
                    UPDATE fulfillment_status 
                    SET current_stage = 'DISPATCHED', updated_at = ?
                    WHERE order_id = ?
                """, (now_str, order_id))

                cur.execute("""
                    UPDATE orders 
                    SET status = 'DISPATCHED', dispatched_at = ?
                    WHERE id = ?
                """, (now_str, order_id))

            # Record Decision Audit Trail
            cur.execute("""
                INSERT INTO decision_audit_logs 
                (decision_type, entity_id, decision_action, confidence_score, rationale, factors_json, alternatives_json, recommended_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'FULFILLMENT_ADVANCE',
                order_id,
                f"ADVANCE_TO_{target_stage}",
                1.0,
                f"Order {order_id} verified and advanced to '{target_stage}'. " + 
                ("Physical inventory deducted from on-hand bin stock upon carrier handover." if target_stage == 'DISPATCHED' else "Stage requirements satisfied."),
                json.dumps({"order_id": order_id, "previous_stage": current_stage, "target_stage": target_stage}),
                json.dumps([]),
                f"Proceed to next operational gate: {target_stage}."
            ))

        return {
            "order_id": order_id,
            "previous_stage": current_stage,
            "current_stage": target_stage,
            "message": f"Order {order_id} successfully advanced to {target_stage}."
        }
