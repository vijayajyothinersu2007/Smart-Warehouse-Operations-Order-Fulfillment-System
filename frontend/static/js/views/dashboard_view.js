// Dashboard View Controller

const DashboardView = {
  async render() {
    try {
      const res = await API.getDashboardSummary();
      if (!res.success) throw new Error("Failed to load dashboard metrics");
      const data = res.summary;

      // Update KPI Elements
      document.getElementById('kpi-total-orders').textContent = data.total_orders;
      document.getElementById('kpi-pending-orders').textContent = data.pending_orders;
      document.getElementById('kpi-picking-orders').textContent = data.picking_orders;
      document.getElementById('kpi-dispatch-orders').textContent = data.ready_for_dispatch;
      document.getElementById('kpi-low-stock').textContent = data.low_stock_count;
      document.getElementById('kpi-out-stock').textContent = data.out_of_stock_count;
      document.getElementById('kpi-open-exceptions').textContent = data.open_exceptions_count;
      document.getElementById('kpi-fulfillment-rate').textContent = `${data.fulfillment_rate}%`;

      // Render Recent Decisions Feed
      const feedContainer = document.getElementById('dashboard-decision-feed');
      feedContainer.innerHTML = '';

      if (data.recent_decisions && data.recent_decisions.length > 0) {
        data.recent_decisions.forEach(d => {
          const item = document.createElement('div');
          item.className = 'decision-card-item';
          
          item.innerHTML = `
            <div class="decision-left">
              <div class="decision-action-title">
                <span>⚡ ${d.decision_action.replace(/_/g, ' ')}</span>
                <span class="badge ${d.decision_type === 'CONTENTION_RESOLUTION' ? 'badge-urgent' : 'badge-info'}">${d.decision_type}</span>
              </div>
              <div class="decision-rationale-text">${d.rationale}</div>
              <div class="decision-timestamp">Executed: ${d.executed_at} • Entity: ${d.entity_id}</div>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="DecisionModal.showById(${d.id})">
              🔍 Explain Decision
            </button>
          `;
          feedContainer.appendChild(item);
        });
      } else {
        feedContainer.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">No recent autonomous decisions recorded yet.</div>';
      }

    } catch (e) {
      console.error(e);
      Toast.danger("Error loading dashboard data: " + e.message);
    }
  },

  async triggerContentionDemo() {
    Toast.info("Simulating Stock Contention: Urgent Order A (10) vs Normal Order B (5) on 7 Units Stock...");
    try {
      const res = await API.simulateContention();
      if (res.success) {
        Toast.success("Stock Contention Resolved! Generated Explainable Decision Card.");
        
        // Refresh dashboard
        await this.render();

        // Automatically open the generated decision card modal
        const decisions = res.allocation_result.decisions;
        if (decisions && decisions.length > 0) {
          DecisionModal.show(decisions[0]);
        }
      } else {
        Toast.danger("Contention simulation failed: " + res.error);
      }
    } catch (e) {
      Toast.danger("Error running simulation: " + e.message);
    }
  }
};

window.DashboardView = DashboardView;
