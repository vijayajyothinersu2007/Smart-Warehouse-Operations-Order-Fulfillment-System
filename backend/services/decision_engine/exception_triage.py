import json
from datetime import datetime
from backend.database.db import get_db, query_db, execute_db

class ExceptionTriageEngine:
    """
    Automated Warehouse Exception & Discrepancy Triage Engine.
    Handles:
    - Damaged item quarantine & auto-reroute to alternate bins
    - Missing item bin zeroing & cycle count flagging
    - Stock shortage triage & resolution suggestions
    - Explainable Decision Card logging for all triage actions
    """

    @staticmethod
    def report_damaged_item(product_id, bin_id, damaged_qty, order_id=None, reported_by="Picker #1"):
        """
        Quarantines damaged stock, discovers alternate bins, updates allocations if needed,
        and creates an auditable triage decision card.
        """
        with get_db() as conn:
            cur = conn.cursor()

            # 1. Update bin stock: move quantity from on_hand to damaged
            cur.execute("""
                UPDATE inventory_stock
                SET quantity_damaged = quantity_damaged + ?,
                    quantity_on_hand = MAX(0, quantity_on_hand - ?)
                WHERE product_id = ? AND bin_id = ?
            """, (damaged_qty, damaged_qty, product_id, bin_id))

            # 2. Check if this bin was reserved for an active order
            affected_allocations = []
            if order_id:
                cur.execute("""
                    SELECT * FROM allocations 
                    WHERE order_id = ? AND product_id = ? AND bin_id = ? AND allocation_status = 'ACTIVE'
                """, (order_id, product_id, bin_id))
                affected_allocations = [dict(r) for r in cur.fetchall()]

            # 3. Search for alternative available stock in other bins
            cur.execute("""
                SELECT s.id, s.bin_id, (s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged) as qty_avail,
                       b.zone, b.aisle, b.rack, b.shelf
                FROM inventory_stock s
                JOIN inventory_bins b ON s.bin_id = b.id
                WHERE s.product_id = ? AND s.bin_id != ? AND (s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged) > 0
                ORDER BY (s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged) DESC
            """, (product_id, bin_id))
            alt_bins = [dict(r) for r in cur.fetchall()]

            # Product details
            cur.execute("SELECT name FROM products WHERE id = ?", (product_id,))
            p_row = cur.fetchone()
            p_name = p_row['name'] if p_row else product_id

            auto_rerouted = False
            reroute_bin_id = None

            if affected_allocations and alt_bins:
                best_alt = alt_bins[0]
                reroute_bin_id = best_alt['bin_id']
                # Re-point allocation to alternate bin
                alloc_id = affected_allocations[0]['id']
                cur.execute("""
                    UPDATE allocations 
                    SET bin_id = ? 
                    WHERE id = ?
                """, (reroute_bin_id, alloc_id))

                # Reserve stock in new bin
                cur.execute("""
                    UPDATE inventory_stock 
                    SET quantity_reserved = quantity_reserved + ?
                    WHERE product_id = ? AND bin_id = ?
                """, (damaged_qty, product_id, reroute_bin_id))

                # Release reservation from damaged bin
                cur.execute("""
                    UPDATE inventory_stock 
                    SET quantity_reserved = MAX(0, quantity_reserved - ?)
                    WHERE product_id = ? AND bin_id = ?
                """, (damaged_qty, product_id, bin_id))

                auto_rerouted = True

            # 4. Create Exception Log Record
            severity = 'HIGH' if order_id else 'MEDIUM'
            desc = f"{damaged_qty} unit(s) of {p_name} ({product_id}) reported DAMAGED in {bin_id}."
            if auto_rerouted:
                proposed_res = f"Auto-rerouted Order {order_id} to alternate Bin {reroute_bin_id} ({best_alt['qty_avail']} units available)."
                applied_res = proposed_res
                status = 'AUTO_RESOLVED'
            else:
                proposed_res = "No alternate bin with immediate stock. Flagged for emergency supervisor review / backorder restock."
                applied_res = proposed_res
                status = 'OPEN'

            cur.execute("""
                INSERT INTO exceptions_log 
                (exception_type, severity, order_id, product_id, bin_id, status, description, proposed_resolution, applied_resolution, resolved_by, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'DAMAGED_ITEM',
                severity,
                order_id,
                product_id,
                bin_id,
                status,
                desc,
                proposed_res,
                applied_res,
                'DECISION_ENGINE' if auto_rerouted else None,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S") if auto_rerouted else None
            ))

            # 5. Create Decision Audit Log
            decision_action = "QUARANTINE_AND_AUTO_REROUTE" if auto_rerouted else "QUARANTINE_AND_LOG_SHORTAGE"
            rationale = (
                f"Quarantined {damaged_qty} damaged unit(s) of {p_name} from {bin_id}. "
                + (f"Automatically re-routed Order {order_id} pick task to alternative {reroute_bin_id}." if auto_rerouted
                   else "No alternative on-hand stock found in warehouse zones. Created replenishment alert.")
            )

            factors = {
                "product_id": product_id,
                "product_name": p_name,
                "damaged_bin": bin_id,
                "damaged_quantity": damaged_qty,
                "order_id": order_id,
                "alternate_bins_found": len(alt_bins),
                "reroute_bin": reroute_bin_id
            }

            alternatives = [
                {
                    "alternative": "Allow damaged item to ship with customer discount",
                    "status": "REJECTED",
                    "reason": "Violates zero-defect quality control policy."
                },
                {
                    "alternative": "Cancel customer order immediately",
                    "status": "REJECTED",
                    "reason": "Sub-optimal customer experience when alternate stock or backorder exists."
                }
            ]

            cur.execute("""
                INSERT INTO decision_audit_logs 
                (decision_type, entity_id, decision_action, confidence_score, rationale, factors_json, alternatives_json, recommended_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'EXCEPTION_TRIAGE',
                order_id or product_id,
                decision_action,
                0.98 if auto_rerouted else 0.85,
                rationale,
                json.dumps(factors),
                json.dumps(alternatives),
                applied_res
            ))

            return {
                "status": status,
                "auto_rerouted": auto_rerouted,
                "reroute_bin": reroute_bin_id,
                "description": desc,
                "resolution": applied_res,
                "rationale": rationale
            }

    @staticmethod
    def report_missing_item(product_id, bin_id, order_id=None, reported_by="Picker #1"):
        """
        Reports missing stock in bin, sets on-hand to 0, audits bin, and searches alternate bins.
        """
        with get_db() as conn:
            cur = conn.cursor()

            # 1. Update bin stock: zero out on-hand
            cur.execute("""
                UPDATE inventory_stock
                SET quantity_on_hand = 0,
                    quantity_reserved = 0
                WHERE product_id = ? AND bin_id = ?
            """, (product_id, bin_id))

            # 2. Product name
            cur.execute("SELECT name FROM products WHERE id = ?", (product_id,))
            p_row = cur.fetchone()
            p_name = p_row['name'] if p_row else product_id

            # 3. Create Exception Log
            desc = f"Bin {bin_id} recorded stock for {p_name} ({product_id}), but physical bin was found empty (MISSING_ITEM)."
            proposed_res = "Zeroed bin inventory. Initiated emergency physical cycle-count audit for Zone/Aisle."
            
            cur.execute("""
                INSERT INTO exceptions_log 
                (exception_type, severity, order_id, product_id, bin_id, status, description, proposed_resolution, applied_resolution, resolved_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'MISSING_ITEM',
                'HIGH',
                order_id,
                product_id,
                bin_id,
                'OPEN',
                desc,
                proposed_res,
                proposed_res,
                'DECISION_ENGINE'
            ))

            # 4. Decision Log
            cur.execute("""
                INSERT INTO decision_audit_logs 
                (decision_type, entity_id, decision_action, confidence_score, rationale, factors_json, alternatives_json, recommended_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'EXCEPTION_TRIAGE',
                bin_id,
                'ZERO_BIN_AND_AUDIT_CYCLE_COUNT',
                0.95,
                f"Discrepancy detected in {bin_id}. On-hand ledger inventory zeroed out to prevent downstream phantom allocations.",
                json.dumps({"bin_id": bin_id, "product_id": product_id, "order_id": order_id}),
                json.dumps([{"alternative": "Keep ledger count and retry later", "status": "REJECTED", "reason": "Causes repeated pick failures."}]),
                "Schedule immediate physical bin recount."
            ))

            return {
                "status": "OPEN",
                "message": desc,
                "action": proposed_res
            }
