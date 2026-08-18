// WarehouseIQ API Client

const API = {
  // Orders
  getOrders: (status = '') => fetch(`/api/orders${status ? '?status=' + status : ''}`).then(r => r.json()),
  getOrder: (id) => fetch(`/api/orders/${id}`).then(r => r.json()),
  createOrder: (data) => fetch('/api/orders', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  recalculatePriorities: () => fetch('/api/orders/recalculate-priorities', { method: 'POST' }).then(r => r.json()),

  // Inventory
  getInventory: () => fetch('/api/inventory').then(r => r.json()),
  getBins: () => fetch('/api/inventory/bins').then(r => r.json()),
  adjustStock: (data) => fetch('/api/inventory/adjust', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),

  // Allocation & Contention
  runAllocation: () => fetch('/api/allocation/run', { method: 'POST' }).then(r => r.json()),
  simulateContention: () => fetch('/api/allocation/simulate-contention', { method: 'POST' }).then(r => r.json()),

  // Fulfillment Lifecycle
  getFulfillmentBoard: () => fetch('/api/fulfillment/board').then(r => r.json()),
  advanceFulfillment: (orderId, targetStage = null, extraData = {}) => fetch('/api/fulfillment/advance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order_id: orderId, target_stage: targetStage, extra_data: extraData })
  }).then(r => r.json()),

  // Exceptions
  getExceptions: (status = '') => fetch(`/api/exceptions${status ? '?status=' + status : ''}`).then(r => r.json()),
  reportDamaged: (data) => fetch('/api/exceptions/report-damaged', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  reportMissing: (data) => fetch('/api/exceptions/report-missing', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  resolveException: (id, data) => fetch(`/api/exceptions/${id}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),

  // Analytics & Decisions
  getDashboardSummary: () => fetch('/api/analytics/dashboard').then(r => r.json()),
  getAnalyticsMetrics: () => fetch('/api/analytics/metrics').then(r => r.json()),
  getDecisions: (entityId = '', limit = 20) => fetch(`/api/decisions?limit=${limit}${entityId ? '&entity_id=' + entityId : ''}`).then(r => r.json()),
  getDecision: (id) => fetch(`/api/decisions/${id}`).then(r => r.json()),

  // System Demo Reset
  resetDemo: () => fetch('/api/system/reset-demo', { method: 'POST' }).then(r => r.json())
};

window.API = API;
