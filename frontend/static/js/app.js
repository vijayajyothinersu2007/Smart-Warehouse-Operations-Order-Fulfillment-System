// WarehouseIQ Main Application Orchestrator

const App = {
  currentTab: 'dashboard',

  init() {
    console.log("WarehouseIQ Initializing...");

    // Setup navigation tabs
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.getAttribute('data-tab');
        if (tab) this.switchTab(tab);
      });
    });

    // Initialize Components
    if (window.Toast) Toast.init();
    if (window.DecisionModal) DecisionModal.init();

    // Bind Modals & Form Events
    this.bindEvents();

    // Initial render
    this.switchTab('dashboard');

    // Polling auto-refresh every 12 seconds
    setInterval(() => {
      this.refreshCurrentTab(true);
    }, 12000);
  },

  switchTab(tabName) {
    this.currentTab = tabName;

    // Update Sidebar Active state
    document.querySelectorAll('.nav-item').forEach(item => {
      if (item.getAttribute('data-tab') === tabName) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    // Update Views
    document.querySelectorAll('.view-panel').forEach(panel => {
      panel.classList.remove('active');
    });

    const activePanel = document.getElementById(`view-${tabName}`);
    if (activePanel) {
      activePanel.classList.add('active');
    }

    // Update Topbar Title
    const titleEl = document.getElementById('topbar-title');
    const descEl = document.getElementById('topbar-desc');

    const headers = {
      'dashboard': { title: 'Operational Command Center', desc: 'Real-time throughput, fulfillment health, and explainable autonomous decisions.' },
      'orders': { title: 'Order Queue & Allocation Console', desc: 'Dynamic SLA prioritization, stock contention detection, and allocation.' },
      'inventory': { title: 'Inventory & Bin Monitor', desc: 'SKU stock levels, reserved locks, and physical bin locations.' },
      'fulfillment': { title: 'Fulfillment & Dispatch Pipeline', desc: 'Stage-by-stage picking, packing, quality inspection, and carrier handover.' },
      'exceptions': { title: 'Exception Triage & Discrepancies', desc: 'Damaged item auto-rerouting, missing bin zeroing, and resolution audit.' },
      'analytics': { title: 'Analytics & Bottleneck Insights', desc: 'Fulfillment rates, station cycle times, and operational performance.' }
    };

    if (headers[tabName]) {
      titleEl.textContent = headers[tabName].title;
      descEl.textContent = headers[tabName].desc;
    }

    this.refreshCurrentTab();
  },

  refreshCurrentTab(silent = false) {
    if (this.currentTab === 'dashboard' && window.DashboardView) DashboardView.render();
    if (this.currentTab === 'orders' && window.OrdersView) OrdersView.render();
    if (this.currentTab === 'inventory' && window.InventoryView) InventoryView.render();
    if (this.currentTab === 'fulfillment' && window.FulfillmentView) FulfillmentView.render();
    if (this.currentTab === 'exceptions' && window.ExceptionsView) ExceptionsView.render();
    if (this.currentTab === 'analytics' && window.AnalyticsView) AnalyticsView.render();
  },

  bindEvents() {
    // New Order Form
    const newOrderForm = document.getElementById('new-order-form');
    if (newOrderForm) {
      newOrderForm.onsubmit = (e) => OrdersView.submitNewOrder(e);
    }

    // Adjust Stock Form
    const adjustForm = document.getElementById('adjust-stock-form');
    if (adjustForm) {
      adjustForm.onsubmit = (e) => InventoryView.submitAdjustStock(e);
    }

    // Damaged Item Form
    const damagedForm = document.getElementById('report-damaged-form');
    if (damagedForm) {
      damagedForm.onsubmit = (e) => ExceptionsView.submitDamaged(e);
    }

    // Missing Item Form
    const missingForm = document.getElementById('report-missing-form');
    if (missingForm) {
      missingForm.onsubmit = (e) => ExceptionsView.submitMissing(e);
    }
  },

  async resetDemoData() {
    if (!confirm("Reset database to the initial hackathon demo state with the Contention Scenario?")) return;
    Toast.info("Resetting & reseeding WarehouseIQ database...");
    try {
      const res = await API.resetDemo();
      if (res.success) {
        Toast.success(res.message);
        this.refreshCurrentTab();
      } else {
        Toast.danger("Reset failed: " + res.error);
      }
    } catch (e) {
      Toast.danger("Error during reset: " + e.message);
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

window.App = App;
