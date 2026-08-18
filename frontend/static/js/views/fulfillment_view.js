// Fulfillment Pipeline View Controller

const FulfillmentView = {
  async render() {
    try {
      const res = await API.getFulfillmentBoard();
      if (!res.success) throw new Error("Failed to load fulfillment pipeline");
      const board = res.board;

      const stages = ['ALLOCATED', 'PICKING', 'PACKED', 'QC_PASSED', 'DISPATCHED'];

      stages.forEach(stage => {
        const container = document.getElementById(`kanban-${stage.toLowerCase()}`);
        const countBadge = document.getElementById(`kanban-count-${stage.toLowerCase()}`);
        if (!container) return;

        const list = board[stage] || [];
        if (countBadge) countBadge.textContent = list.length;
        container.innerHTML = '';

        if (list.length === 0) {
          container.innerHTML = `<div style="font-size:0.78rem; color:var(--text-muted); text-align:center; padding:1.5rem 0;">No active orders</div>`;
          return;
        }

        list.forEach(o => {
          const card = document.createElement('div');
          card.className = 'order-card';

          let actionBtn = '';
          if (stage === 'ALLOCATED') {
            actionBtn = `<button class="btn btn-primary btn-sm" onclick="FulfillmentView.advance('${o.id}', 'PICKING')">📦 Start Picking</button>`;
          } else if (stage === 'PICKING') {
            actionBtn = `<button class="btn btn-primary btn-sm" onclick="FulfillmentView.advance('${o.id}', 'PACKED')">📦 Mark Packed</button>`;
          } else if (stage === 'PACKED') {
            actionBtn = `<button class="btn btn-success btn-sm" onclick="FulfillmentView.advance('${o.id}', 'QC_PASSED')">✅ Pass QC</button>`;
          } else if (stage === 'QC_PASSED') {
            actionBtn = `<button class="btn btn-decision btn-sm" onclick="FulfillmentView.advance('${o.id}', 'DISPATCHED')">🚚 Dispatch</button>`;
          } else if (stage === 'DISPATCHED') {
            actionBtn = `
              <div style="font-size:0.72rem; color:#60A5FA; font-family:var(--font-mono);">
                ${o.carrier_name || 'Carrier'}: ${o.tracking_number || 'TRK-OK'}
              </div>
            `;
          }

          card.innerHTML = `
            <div class="order-card-header">
              <span class="order-card-id">${o.id}</span>
              <span class="priority-pill ${o.priority_score >= 80 ? 'priority-high' : 'priority-mid'}">${o.priority_score}</span>
            </div>
            <div class="order-card-customer">${o.customer_name}</div>
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted);">
              <span>Tier: <strong>${o.customer_tier}</strong></span>
              <span>Weight: ${o.total_weight_kg || 1.2} kg</span>
            </div>
            <div style="margin-top:4px; display:flex; gap:6px; align-items:center; justify-content:space-between;">
              <button class="btn btn-secondary btn-sm" onclick="DecisionModal.showByEntity('${o.id}')" title="Explain Decision">🔍</button>
              ${actionBtn}
            </div>
          `;

          container.appendChild(card);
        });
      });

    } catch (e) {
      console.error(e);
      Toast.danger("Error loading fulfillment board: " + e.message);
    }
  },

  async advance(orderId, nextStage) {
    try {
      const res = await API.advanceFulfillment(orderId, nextStage);
      if (res.success) {
        Toast.success(res.message);
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
        if (window.OrdersView) window.OrdersView.render();
        if (window.InventoryView) window.InventoryView.render();
      } else {
        Toast.warning(res.error || res.message);
      }
    } catch (e) {
      Toast.danger("Error advancing order: " + e.message);
    }
  }
};

window.FulfillmentView = FulfillmentView;
