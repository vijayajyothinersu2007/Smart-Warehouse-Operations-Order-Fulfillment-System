import json
from datetime import datetime, timedelta
from backend.database.db import query_db, execute_db, get_db
from backend.services.decision_engine.priority_scorer import PriorityScorer

class OrderService:
    @staticmethod
    def get_orders(status_filter=None):
        """
        Retrieves orders with their line items, priority, and SLA countdown.
        """
        query = """
            SELECT o.*, 
                   COUNT(oi.id) as item_count,
                   COALESCE(SUM(oi.quantity_requested), 0) as total_units_demanded,
                   COALESCE(SUM(oi.quantity_allocated), 0) as total_units_allocated,
                   f.current_stage,
                   f.qc_status,
                   d.tracking_number,
                   d.carrier_name
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN fulfillment_status f ON o.id = f.order_id
            LEFT JOIN dispatches d ON o.id = d.order_id
        """
        params = []
        if status_filter:
            query += " WHERE o.status = ?"
            params.append(status_filter)

        query += " GROUP BY o.id ORDER BY o.priority_score DESC, o.target_sla_cutoff ASC"
        orders = query_db(query, params)

        # Attach item details and human SLA time remaining
        now = datetime.now()
        for o in orders:
            # Fetch line items
            items = query_db("""
                SELECT oi.*, p.name as product_name, p.category, p.unit_price, p.weight_kg
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ?
            """, (o['id'],))
            o['items'] = items

            # Calculate human-friendly SLA
            try:
                target_str = o['target_sla_cutoff']
                if 'T' in target_str:
                    target_dt = datetime.fromisoformat(target_str)
                else:
                    target_dt = datetime.strptime(target_str, "%Y-%m-%d %H:%M:%S")
                diff = (target_dt - now).total_seconds() / 3600.0
                o['sla_hours_remaining'] = round(diff, 1)
                o['is_overdue'] = diff <= 0
            except Exception:
                o['sla_hours_remaining'] = 12.0
                o['is_overdue'] = False

        return orders

    @staticmethod
    def get_order_details(order_id):
        order = query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)
        if not order:
            return None

        order['items'] = query_db("""
            SELECT oi.*, p.name as product_name, p.category, p.unit_price, p.weight_kg
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))

        order['allocations'] = query_db("""
            SELECT a.*, b.zone, b.aisle, b.rack, b.shelf, b.bin_number, p.name as product_name
            FROM allocations a
            JOIN inventory_bins b ON a.bin_id = b.id
            JOIN products p ON a.product_id = p.id
            WHERE a.order_id = ?
        """, (order_id,))

        order['fulfillment'] = query_db("SELECT * FROM fulfillment_status WHERE order_id = ?", (order_id,), one=True)
        order['dispatch'] = query_db("SELECT * FROM dispatches WHERE order_id = ?", (order_id,), one=True)
        
        # Get decision logs related to this order
        order['decisions'] = query_db("""
            SELECT * FROM decision_audit_logs 
            WHERE entity_id = ? OR rationale LIKE ?
            ORDER BY executed_at DESC
        """, (order_id, f"%{order_id}%"))

        return order

    @staticmethod
    def create_order(data):
        """
        Creates a new customer order, scores its priority, and registers order items.
        """
        order_id = data.get('id') or f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        customer_name = data.get('customer_name', 'Acme Logistics Client')
        customer_tier = (data.get('customer_tier') or 'NORMAL').upper()
        destination_city = data.get('destination_city', 'Metro Distribution Hub')
        
        # SLA cutoff
        sla_hours = float(data.get('sla_hours', 8))
        target_sla = datetime.now() + timedelta(hours=sla_hours)
        target_sla_str = target_sla.strftime("%Y-%m-%d %H:%M:%S")

        items_input = data.get('items', [])
        
        # Calculate total price & weight
        total_amount = 0.0
        total_weight = 0.0
        for item in items_input:
            p = query_db("SELECT unit_price, weight_kg FROM products WHERE id = ?", (item['product_id'],), one=True)
            if p:
                qty = int(item.get('quantity', 1))
                total_amount += p['unit_price'] * qty
                total_weight += p['weight_kg'] * qty

        # Compute dynamic priority score
        order_payload_for_score = {
            "customer_tier": customer_tier,
            "is_urgent": 1 if customer_tier in ['URGENT', 'VIP'] else 0,
            "target_sla_cutoff": target_sla_str,
            "total_amount": total_amount
        }
        score_result = PriorityScorer.calculate_score(order_payload_for_score)

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO orders (id, customer_name, customer_tier, destination_city, status, priority_score, is_urgent, target_sla_cutoff, total_amount, total_weight_kg, allocation_status)
                VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, 'UNALLOCATED')
            """, (
                order_id,
                customer_name,
                customer_tier,
                destination_city,
                score_result['priority_score'],
                score_result['is_urgent'],
                target_sla_str,
                total_amount,
                total_weight
            ))

            for item in items_input:
                cur.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity_requested, quantity_allocated, status)
                    VALUES (?, ?, ?, 0, 'PENDING')
                """, (order_id, item['product_id'], int(item.get('quantity', 1))))

            # Register initial fulfillment entry
            cur.execute("""
                INSERT INTO fulfillment_status (order_id, current_stage, target_weight_kg)
                VALUES (?, 'PENDING', ?)
            """, (order_id, total_weight))

            # Record Priority Decision in Audit Log
            cur.execute("""
                INSERT INTO decision_audit_logs 
                (decision_type, entity_id, decision_action, confidence_score, rationale, factors_json, alternatives_json, recommended_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'PRIORITY_SCORING',
                order_id,
                'ASSIGN_DYNAMIC_PRIORITY',
                0.99,
                score_result['rationale'],
                json.dumps(score_result['factors']),
                json.dumps([]),
                "Queue order for stock allocation in priority sequence."
            ))

        return OrderService.get_order_details(order_id)

    @staticmethod
    def recalculate_all_priorities():
        """
        Recalculates dynamic priority scores for all non-dispatched orders.
        """
        orders = query_db("SELECT * FROM orders WHERE status NOT IN ('DISPATCHED', 'CANCELLED')")
        updated_count = 0
        with get_db() as conn:
            cur = conn.cursor()
            for o in orders:
                score_res = PriorityScorer.calculate_score(o)
                cur.execute("""
                    UPDATE orders 
                    SET priority_score = ?, is_urgent = ?
                    WHERE id = ?
                """, (score_res['priority_score'], score_res['is_urgent'], o['id']))
                updated_count += 1
        return {"message": f"Updated priorities for {updated_count} active orders.", "updated_count": updated_count}
