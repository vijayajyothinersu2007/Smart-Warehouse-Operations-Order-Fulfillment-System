from backend.database.db import query_db, execute_db, get_db

class InventoryService:
    @staticmethod
    def get_inventory_list():
        """
        Fetches all products with aggregated stock counts and status.
        """
        query = """
            SELECT 
                p.id as sku,
                p.name,
                p.category,
                p.unit_price,
                p.weight_kg,
                p.barcode,
                p.min_safety_stock,
                p.reorder_point,
                COALESCE(SUM(s.quantity_on_hand), 0) as total_on_hand,
                COALESCE(SUM(s.quantity_reserved), 0) as total_reserved,
                COALESCE(SUM(s.quantity_damaged), 0) as total_damaged,
                COALESCE(SUM(s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged), 0) as total_available,
                COUNT(s.bin_id) as bin_count
            FROM products p
            LEFT JOIN inventory_stock s ON p.id = s.product_id
            GROUP BY p.id
            ORDER BY 
                CASE 
                    WHEN COALESCE(SUM(s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged), 0) = 0 THEN 1
                    WHEN COALESCE(SUM(s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged), 0) <= p.reorder_point THEN 2
                    ELSE 3
                END,
                p.id ASC
        """
        items = query_db(query)
        for item in items:
            avail = item['total_available']
            rop = item['reorder_point']
            if avail <= 0:
                item['stock_status'] = 'OUT_OF_STOCK'
            elif avail <= rop:
                item['stock_status'] = 'LOW_STOCK'
            else:
                item['stock_status'] = 'IN_STOCK'
        return items

    @staticmethod
    def get_product_details(sku):
        prod = query_db("SELECT * FROM products WHERE id = ?", (sku,), one=True)
        if not prod:
            return None
        bins = query_db("""
            SELECT s.*, (s.quantity_on_hand - s.quantity_reserved - s.quantity_damaged) as quantity_available,
                   b.zone, b.aisle, b.rack, b.shelf, b.bin_number
            FROM inventory_stock s
            JOIN inventory_bins b ON s.bin_id = b.id
            WHERE s.product_id = ?
        """, (sku,))
        prod['bins'] = bins
        return prod

    @staticmethod
    def adjust_stock(product_id, bin_id, quantity_on_hand):
        """
        Sets physical on-hand stock for a specific product and bin.
        """
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO inventory_stock (product_id, bin_id, quantity_on_hand, quantity_reserved, quantity_damaged)
                VALUES (?, ?, ?, 0, 0)
                ON CONFLICT(product_id, bin_id) DO UPDATE SET
                    quantity_on_hand = excluded.quantity_on_hand,
                    last_audited_at = CURRENT_TIMESTAMP
            """, (product_id, bin_id, int(quantity_on_hand)))
        return True

    @staticmethod
    def get_all_bins():
        return query_db("""
            SELECT b.*, 
                   COUNT(s.product_id) as assigned_skus,
                   COALESCE(SUM(s.quantity_on_hand), 0) as total_units
            FROM inventory_bins b
            LEFT JOIN inventory_stock s ON b.id = s.bin_id
            GROUP BY b.id
            ORDER BY b.zone, b.aisle, b.rack, b.shelf
        """)
