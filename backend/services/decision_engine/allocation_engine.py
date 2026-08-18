import json
from datetime import datetime
from backend.database.db import get_db, query_db, execute_db
from backend.services.decision_engine.priority_scorer import PriorityScorer

class AllocationEngine:
    """
    Intelligent Stock Allocation & Contention Resolution Engine.
    Handles:
    - Available stock discovery across warehouse bins
    - Multi-order stock contention detection
    - Priority-based allocation & partial fulfillment
    - Automated backorder recommendations
    - Explainable Decision Card generation
    """

    @staticmethod
    def get_sku_available_stock(product_id, conn=None):
        """
        Returns list of bins holding available (unreserved) stock for a given product.
        """
        query = """
            SELECT s.id as stock_id, s.product_id, s.bin_id, s.quantity_on_hand, s.quantity_reserved,
                   s.quantity_damaged, (s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged) as quantity_available,
                   b.zone, b.aisle, b.rack, b.shelf, b.bin_number
            FROM inventory_stock s
            JOIN inventory_bins b ON s.bin_id = b.id
            WHERE s.product_id = ? AND (s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged) > 0
            ORDER BY (s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged) DESC
        """
        if conn:
            cur = conn.cursor()
            cur.execute(query, (product_id,))
            return [dict(r) for r in cur.fetchall()]
        return query_db(query, (product_id,))

    @staticmethod
    def run_allocation_for_all_pending():
        """
        Processes all pending unallocated orders and resolves allocations and contentions.
        """
        with get_db() as conn:
            # 1. Fetch all pending unallocated or contention orders
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM orders 
                WHERE status = 'PENDING' OR allocation_status IN ('UNALLOCATED', 'CONTENTION_HOLD')
                ORDER BY priority_score DESC, created_at ASC
            """)
            orders = [dict(r) for r in cur.fetchall()]

            if not orders:
                return {"message": "No pending orders to allocate", "allocations_made": 0, "decisions": []}

            # 2. Check for contention by aggregating SKU demand across pending orders
            sku_demand = {}
            order_items_map = {}

            for order in orders:
                cur.execute("""
                    SELECT oi.*, p.name as product_name, p.unit_price, p.weight_kg
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = ?
                """, (order['id'],))
                items = [dict(r) for r in cur.fetchall()]
                order_items_map[order['id']] = items

                for item in items:
                    pid = item['product_id']
                    needed = item['quantity_requested'] - item['quantity_allocated']
                    if needed > 0:
                        if pid not in sku_demand:
                            sku_demand[pid] = []
                        sku_demand[pid].append({
                            "order_id": order['id'],
                            "order_item_id": item['id'],
                            "priority_score": order['priority_score'],
                            "customer_tier": order['customer_tier'],
                            "customer_name": order['customer_name'],
                            "quantity_needed": needed
                        })

            decisions_generated = []
            allocations_count = 0

            # 3. For each contested/requested SKU, evaluate available stock vs demand
            for pid, demand_list in sku_demand.items():
                total_needed = sum(d['quantity_needed'] for d in demand_list)
                available_bins = AllocationEngine.get_sku_available_stock(pid, conn)
                total_available = sum(b['quantity_available'] for b in available_bins)

                # Check if stock contention exists (multiple orders competing for scarce units)
                is_contention = len(demand_list) > 1 and total_available < total_needed

                if is_contention:
                    decision = AllocationEngine._resolve_contention(
                        pid=pid,
                        demand_list=demand_list,
                        available_bins=available_bins,
                        total_available=total_available,
                        total_needed=total_needed,
                        conn=conn
                    )
                    decisions_generated.append(decision)
                    allocations_count += 1
                else:
                    # Standard priority-ordered allocation
                    for req in demand_list:
                        needed = req['quantity_needed']
                        allocated_for_this_req = 0

                        for b in available_bins:
                            if b['quantity_available'] <= 0 or allocated_for_this_req >= needed:
                                continue
                            
                            alloc_qty = min(needed - allocated_for_this_req, b['quantity_available'])
                            if alloc_qty > 0:
                                # Reserve in stock
                                cur.execute("""
                                    UPDATE inventory_stock 
                                    SET quantity_reserved = quantity_reserved + ?
                                    WHERE product_id = ? AND bin_id = ?
                                """, (alloc_qty, pid, b['bin_id']))

                                # Record allocation
                                cur.execute("""
                                    INSERT INTO allocations (order_id, order_item_id, product_id, bin_id, quantity_allocated, allocation_status)
                                    VALUES (?, ?, ?, ?, ?, 'ACTIVE')
                                """, (req['order_id'], req['order_item_id'], pid, b['bin_id'], alloc_qty))

                                b['quantity_available'] -= alloc_qty
                                allocated_for_this_req += alloc_qty
                                allocations_count += 1

                        # Update Order Item Status
                        item_status = 'ALLOCATED_FULL' if allocated_for_this_req >= needed else (
                            'ALLOCATED_PARTIAL' if allocated_for_this_req > 0 else 'BACKORDERED'
                        )
                        cur.execute("""
                            UPDATE order_items 
                            SET quantity_allocated = quantity_allocated + ?, status = ?
                            WHERE id = ?
                        """, (allocated_for_this_req, item_status, req['order_item_id']))

            # 4. Refresh order overall statuses
            for order in orders:
                cur.execute("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
                items = [dict(r) for r in cur.fetchall()]
                all_full = all(i['quantity_allocated'] >= i['quantity_requested'] for i in items)
                any_alloc = any(i['quantity_allocated'] > 0 for i in items)

                if all_full:
                    order_status = 'ALLOCATED'
                    alloc_status = 'ALLOCATED_FULL'
                elif any_alloc:
                    order_status = 'ALLOCATED'
                    alloc_status = 'ALLOCATED_PARTIAL'
                else:
                    order_status = 'PENDING'
                    alloc_status = 'BACKORDERED'

                cur.execute("""
                    UPDATE orders 
                    SET status = ?, allocation_status = ?
                    WHERE id = ?
                """, (order_status, alloc_status, order['id']))

                # Ensure fulfillment record exists
                cur.execute("""
                    INSERT OR IGNORE INTO fulfillment_status (order_id, current_stage)
                    VALUES (?, ?)
                """, (order['id'], 'ALLOCATED' if any_alloc else 'PENDING'))

            return {
                "message": f"Allocation completed. Made {allocations_count} bin reservations.",
                "allocations_count": allocations_count,
                "decisions": decisions_generated
            }

    @staticmethod
    def _resolve_contention(pid, demand_list, available_bins, total_available, total_needed, conn):
        """
        Resolves stock contention when Demand > Available stock using Priority Decision Matrix.
        """
        cur = conn.cursor()
        
        # Sort competing orders by priority score descending
        sorted_demands = sorted(demand_list, key=lambda x: x['priority_score'], reverse=True)
        primary = sorted_demands[0]
        secondary = sorted_demands[1] if len(sorted_demands) > 1 else None

        # Fetch product name
        cur.execute("SELECT name FROM products WHERE id = ?", (pid,))
        prod_row = cur.fetchone()
        prod_name = prod_row['name'] if prod_row else pid

        remaining_stock = total_available
        allocations_summary = []

        # Fulfill highest priority first
        for req in sorted_demands:
            alloc_for_order = min(req['quantity_needed'], remaining_stock)
            remaining_stock -= alloc_for_order

            if alloc_for_order > 0:
                # Deduct from bins
                qty_to_distribute = alloc_for_order
                for b in available_bins:
                    if b['quantity_available'] <= 0 or qty_to_distribute <= 0:
                        continue
                    take = min(qty_to_distribute, b['quantity_available'])
                    
                    cur.execute("""
                        UPDATE inventory_stock 
                        SET quantity_reserved = quantity_reserved + ?
                        WHERE product_id = ? AND bin_id = ?
                    """, (take, pid, b['bin_id']))

                    cur.execute("""
                        INSERT INTO allocations (order_id, order_item_id, product_id, bin_id, quantity_allocated, allocation_status)
                        VALUES (?, ?, ?, ?, ?, 'ACTIVE')
                    """, (req['order_id'], req['order_item_id'], pid, b['bin_id'], take))

                    b['quantity_available'] -= take
                    qty_to_distribute -= take

                item_status = 'ALLOCATED_FULL' if alloc_for_order >= req['quantity_needed'] else 'ALLOCATED_PARTIAL'
                cur.execute("""
                    UPDATE order_items 
                    SET quantity_allocated = quantity_allocated + ?, status = ?
                    WHERE id = ?
                """, (alloc_for_order, item_status, req['order_item_id']))
                
                allocations_summary.append({
                    "order_id": req['order_id'],
                    "priority_score": req['priority_score'],
                    "customer_tier": req['customer_tier'],
                    "allocated": alloc_for_order,
                    "requested": req['quantity_needed'],
                    "status": item_status
                })
            else:
                cur.execute("""
                    UPDATE order_items 
                    SET status = 'BACKORDERED'
                    WHERE id = ?
                """, (req['order_item_id'],))
                
                allocations_summary.append({
                    "order_id": req['order_id'],
                    "priority_score": req['priority_score'],
                    "customer_tier": req['customer_tier'],
                    "allocated": 0,
                    "requested": req['quantity_needed'],
                    "status": "BACKORDERED"
                })

        # Construct Explainable Decision Card Data
        decision_action = "PRIORITY_CONTENTION_PARTIAL_ALLOCATION"
        confidence_score = 0.96

        rationale = (
            f"Stock Contention Detected for {prod_name} ({pid}). Total requested: {total_needed} units across "
            f"{len(demand_list)} orders, but only {total_available} units available on-hand. "
            f"Evaluated Order {primary['order_id']} (Priority: {primary['priority_score']}, Tier: {primary['customer_tier']}) "
            f"vs Order {secondary['order_id'] if secondary else 'Other'} (Priority: {secondary['priority_score'] if secondary else 'N/A'}, Tier: {secondary['customer_tier'] if secondary else 'N/A'}). "
            f"Allocated {allocations_summary[0]['allocated']}/{primary['quantity_needed']} available units to higher-priority Order {primary['order_id']} to prevent SLA breach. "
            f"Queued remaining unfilled demand for priority replenishment backorder."
        )

        recommended_action = (
            f"1. Immediately proceed with picking wave for Order {primary['order_id']} ({allocations_summary[0]['allocated']} units). "
            f"2. Expedite emergency purchase order for {total_needed - total_available} units to fulfill backorders."
        )

        alternatives = [
            {
                "alternative": f"Split stock proportionally / equally between orders",
                "status": "REJECTED",
                "reason": f"Equal split would leave both orders incomplete and cause guaranteed SLA breach for critical VIP Order {primary['order_id']}."
            },
            {
                "alternative": f"Fulfill lower-priority Order {secondary['order_id'] if secondary else 'Order B'} completely first",
                "status": "REJECTED",
                "reason": f"Violates warehouse SLA policy by prioritizing lower tier ({secondary['customer_tier'] if secondary else 'Standard'}, Score: {secondary['priority_score'] if secondary else 0}) over urgent deadline."
            },
            {
                "alternative": "Hold all allocations until replenishment arrives",
                "status": "REJECTED",
                "reason": "Causes inventory bottleneck and delays fulfillment for orders that could be partially shipped."
            }
        ]

        factors = {
            "sku": pid,
            "product_name": prod_name,
            "total_demanded": total_needed,
            "total_available": total_available,
            "shortage_gap": total_needed - total_available,
            "competing_orders": demand_list,
            "allocations_result": allocations_summary
        }

        # Store Decision in Audit Log
        cur.execute("""
            INSERT INTO decision_audit_logs 
            (decision_type, entity_id, decision_action, confidence_score, rationale, factors_json, alternatives_json, recommended_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'CONTENTION_RESOLUTION',
            primary['order_id'],
            decision_action,
            confidence_score,
            rationale,
            json.dumps(factors),
            json.dumps(alternatives),
            recommended_action
        ))

        return {
            "decision_type": "CONTENTION_RESOLUTION",
            "decision_action": decision_action,
            "confidence_score": confidence_score,
            "rationale": rationale,
            "factors": factors,
            "alternatives": alternatives,
            "recommended_action": recommended_action
        }
