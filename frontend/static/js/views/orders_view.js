// Orders View Controller

const OrdersView = {
  async render() {
    try {
      const res = await API.getOrders();
      if (!res.success) throw new Error("Failed to load orders");
      const orders = res.orders;

      const tbody = document.getElementById('orders-table-body');
      tbody.innerHTML = '';

      if (orders.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:2rem;">No orders found.</td></tr>`;
        return;
      }

      orders.forEach(o => {
        const tr = document.createElement('tr');
        
        // Priority pill class
        let pClass = 'priority-low';
        if (o.priority_score >= 80) pClass = 'priority-high';
        else if (o.priority_score >= 50) pClass = 'priority-mid';

        // Customer Tier badge
        let tierBadgeClass = 'badge-normal';
        if (o.customer_tier === 'URGENT') tierBadgeClass = 'badge-urgent';
        else if (o.customer_tier === 'VIP') tierBadgeClass = 'badge-vip';
        else if (o.customer_tier === 'EXPRESS') tierBadgeClass = 'badge-info';

        // Items summary string
        const itemsSummary = o.items.map(i => `
          <div style="font-size:0.8rem;">
            <strong>${i.product_id}</strong>: 
            <span style="color:${i.quantity_allocated >= i.quantity_requested ? '#34D399' : (i.quantity_allocated > 0 ? '#FBBF24' : '#F87171')};">
              ${i.quantity_allocated}/${i.quantity_requested} units
            </span>
          </div>
        `).join('');

        // Allocation status badge
        let allocBadgeClass = 'badge-normal';
        if (o.allocation_status === 'ALLOCATED_FULL') allocBadgeClass = 'badge-allocated-full';
        else if (o.allocation_status === 'ALLOCATED_PARTIAL') allocBadgeClass = 'badge-allocated-partial';
        else if (o.allocation_status === 'BACKORDERED') allocBadgeClass = 'badge-backordered';

        // SLA display
        const slaDisplay = o.is_overdue 
          ? `<span style="color:var(--status-danger); font-weight:700;">⚠️ OVERDUE</span>`
          : `<span style="font-size:0.8rem; color:${o.sla_hours_remaining <= 2 ? '#F87171' : 'var(--text-secondary)'}; font-weight:${o.sla_hours_remaining <= 2 ? '700' : '500'};">⏱️ ${o.sla_hours_remaining} hrs left</span>`;

        tr.innerHTML = `
          <td>
            <div style="font-family:var(--font-mono); font-weight:700; color:#93C5FD;">${o.id}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">$${o.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
          </td>
          <td>
            <span class="priority-pill ${pClass}">${o.priority_score}</span>
          </td>
          <td>
            <div style="font-weight:600;">${o.customer_name}</div>
            <span class="badge ${tierBadgeClass}">${o.customer_tier}</span>
          </td>
          <td>
            ${itemsSummary}
          </td>
          <td>
            <span class="badge badge-${o.status.toLowerCase()}">${o.status}</span>
          </td>
          <td>
            ${slaDisplay}
          </td>
          <td>
            <span class="badge ${allocBadgeClass}">${o.allocation_status || 'UNALLOCATED'}</span>
          </td>
          <td>
            <div style="display:flex; gap:6px; flex-wrap:wrap;">
              <button class="btn btn-secondary btn-sm" onclick="DecisionModal.showByEntity('${o.id}')" title="Explain Decision Rationale">
                🔍 Explain
              </button>
              ${o.status !== 'DISPATCHED' ? `
                <button class="btn btn-primary btn-sm" onclick="OrdersView.advanceOrder('${o.id}')" title="Advance Fulfillment Stage">
                  ⏩ Advance
                </button>
              ` : `<span style="color:var(--status-success); font-size:0.75rem; font-weight:700;">✅ Done</span>`}
            </div>
          </td>
        `;

        tbody.appendChild(tr);
      });

    } catch (e) {
      console.error(e);
      Toast.danger("Error loading orders: " + e.message);
    }
  },

  async runAllocationAll() {
    Toast.info("Executing Autonomous Stock Allocation Engine...");
    try {
      const res = await API.runAllocation();
      if (res.success) {
        Toast.success(res.message);
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
        if (res.decisions && res.decisions.length > 0) {
          DecisionModal.show(res.decisions[0]);
        }
      } else {
        Toast.danger("Allocation failed: " + res.error);
      }
    } catch (e) {
      Toast.danger("Error during allocation: " + e.message);
    }
  },

  async recalculatePriorities() {
    Toast.info("Recalculating Dynamic Order Priority Scores based on SLA countdowns...");
    try {
      const res = await API.recalculatePriorities();
      if (res.success) {
        Toast.success(res.message);
        await this.render();
      }
    } catch (e) {
      Toast.danger("Error recalculating priorities: " + e.message);
    }
  },

  async advanceOrder(orderId) {
    try {
      const res = await API.advanceFulfillment(orderId);
      if (res.success) {
        Toast.success(res.message);
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
        if (window.FulfillmentView) window.FulfillmentView.render();
      } else {
        Toast.warning(res.error || res.message);
      }
    } catch (e) {
      Toast.danger("Error advancing order: " + e.message);
    }
  },

  openNewOrderModal() {
    const modal = document.getElementById('new-order-modal-backdrop');
    if (modal) modal.classList.add('open');
  },

  closeNewOrderModal() {
    const modal = document.getElementById('new-order-modal-backdrop');
    if (modal) modal.classList.remove('open');
  },

  async submitNewOrder(e) {
    e.preventDefault();
    const customer = document.getElementById('new-order-customer').value;
    const tier = document.getElementById('new-order-tier').value;
    const sku = document.getElementById('new-order-sku').value;
    const qty = parseInt(document.getElementById('new-order-qty').value) || 1;
    const sla = parseFloat(document.getElementById('new-order-sla').value) || 8;

    try {
      const res = await API.createOrder({
        customer_name: customer,
        customer_tier: tier,
        sla_hours: sla,
        items: [{ product_id: sku, quantity: qty }]
      });

      if (res.success) {
        Toast.success(`Order ${res.order.id} created! Priority score: ${res.order.priority_score}`);
        this.closeNewOrderModal();
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
      } else {
        Toast.danger("Failed to create order: " + res.error);
      }
    } catch (err) {
      Toast.danger("Error creating order: " + err.message);
    }
  }
};

window.OrdersView = OrdersView;
