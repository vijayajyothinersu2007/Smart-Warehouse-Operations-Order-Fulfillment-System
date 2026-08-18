-- Database Schema for WarehouseIQ (SQLite)

DROP TABLE IF EXISTS decision_audit_logs;
DROP TABLE IF EXISTS exceptions_log;
DROP TABLE IF EXISTS dispatches;
DROP TABLE IF EXISTS fulfillment_status;
DROP TABLE IF EXISTS allocations;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS inventory_stock;
DROP TABLE IF EXISTS inventory_bins;
DROP TABLE IF EXISTS products;

-- 1. Products Master
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL,
    weight_kg REAL NOT NULL,
    barcode TEXT UNIQUE NOT NULL,
    min_safety_stock INTEGER NOT NULL DEFAULT 10,
    reorder_point INTEGER NOT NULL DEFAULT 25,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Warehouse Bin Locations
CREATE TABLE inventory_bins (
    id TEXT PRIMARY KEY,
    zone TEXT NOT NULL,
    aisle INTEGER NOT NULL,
    rack INTEGER NOT NULL,
    shelf INTEGER NOT NULL,
    bin_number INTEGER NOT NULL,
    coord_x REAL NOT NULL DEFAULT 0.0,
    coord_y REAL NOT NULL DEFAULT 0.0,
    max_capacity_units INTEGER DEFAULT 100,
    is_active INTEGER DEFAULT 1
);

-- 3. Inventory Stock
CREATE TABLE inventory_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    bin_id TEXT NOT NULL,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    quantity_damaged INTEGER NOT NULL DEFAULT 0,
    last_audited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (bin_id) REFERENCES inventory_bins(id),
    CONSTRAINT unq_product_bin UNIQUE (product_id, bin_id)
);

-- 4. Customer Orders
CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_tier TEXT NOT NULL,       -- 'URGENT', 'VIP', 'EXPRESS', 'NORMAL', 'STANDARD', 'BULK'
    destination_city TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',  -- 'PENDING', 'ALLOCATED', 'PICKING', 'PACKED', 'DISPATCHED', 'EXCEPTION', 'CANCELLED'
    priority_score REAL DEFAULT 0.0,
    is_urgent INTEGER DEFAULT 0,
    target_sla_cutoff DATETIME NOT NULL,
    total_amount REAL NOT NULL DEFAULT 0.0,
    total_weight_kg REAL DEFAULT 0.0,
    allocation_status TEXT DEFAULT 'UNALLOCATED', -- 'UNALLOCATED', 'ALLOCATED_FULL', 'ALLOCATED_PARTIAL', 'BACKORDERED', 'CONTENTION_HOLD'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    dispatched_at DATETIME
);

-- 5. Order Line Items
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity_requested INTEGER NOT NULL,
    quantity_allocated INTEGER NOT NULL DEFAULT 0,
    quantity_picked INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'ALLOCATED_FULL', 'ALLOCATED_PARTIAL', 'BACKORDERED', 'PICKED'
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 6. Inventory Allocations (Tracking which bin reserves for which order)
CREATE TABLE allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    bin_id TEXT NOT NULL,
    quantity_allocated INTEGER NOT NULL,
    allocation_status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'RELEASED', 'FULFILLED'
    allocated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (bin_id) REFERENCES inventory_bins(id)
);

-- 7. Fulfillment Tracking (Picking, Packing, Quality Check)
CREATE TABLE fulfillment_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL UNIQUE,
    current_stage TEXT NOT NULL DEFAULT 'ALLOCATED', -- 'ALLOCATED', 'PICKING', 'PACKED', 'QC_PASSED', 'DISPATCHED'
    picker_name TEXT,
    packer_name TEXT,
    qc_inspector TEXT,
    target_weight_kg REAL DEFAULT 0.0,
    measured_weight_kg REAL,
    qc_status TEXT DEFAULT 'PENDING', -- 'PENDING', 'PASSED', 'FAILED_WEIGHT', 'FAILED_DISCREPANCY'
    notes TEXT,
    started_picking_at DATETIME,
    completed_picking_at DATETIME,
    completed_packing_at DATETIME,
    completed_qc_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- 8. Dispatches
CREATE TABLE dispatches (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL UNIQUE,
    carrier_name TEXT NOT NULL,
    tracking_number TEXT UNIQUE NOT NULL,
    dock_door TEXT NOT NULL,
    dispatched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- 9. Exceptions & Triage Log
CREATE TABLE exceptions_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_type TEXT NOT NULL,      -- 'STOCK_SHORTAGE', 'DAMAGED_ITEM', 'MISSING_ITEM', 'WEIGHT_MISMATCH', 'SLA_RISK'
    severity TEXT NOT NULL DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    order_id TEXT,
    product_id TEXT,
    bin_id TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',     -- 'OPEN', 'AUTO_RESOLVED', 'RESOLVED'
    description TEXT NOT NULL,
    proposed_resolution TEXT,
    applied_resolution TEXT,
    resolved_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (bin_id) REFERENCES inventory_bins(id)
);

-- 10. Explainable Decision Audit Trail
CREATE TABLE decision_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_type TEXT NOT NULL,       -- 'PRIORITY_SCORING', 'STOCK_ALLOCATION', 'CONTENTION_RESOLUTION', 'EXCEPTION_TRIAGE', 'FULFILLMENT_ADVANCE'
    entity_id TEXT NOT NULL,           -- Order ID, Product ID, etc.
    decision_action TEXT NOT NULL,
    confidence_score REAL NOT NULL DEFAULT 1.0,
    rationale TEXT NOT NULL,
    factors_json TEXT NOT NULL DEFAULT '{}',
    alternatives_json TEXT NOT NULL DEFAULT '[]',
    recommended_action TEXT,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for optimal lookup performance
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_priority ON orders(priority_score DESC);
CREATE INDEX idx_stock_prod_bin ON inventory_stock(product_id, bin_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_allocations_order ON allocations(order_id);
