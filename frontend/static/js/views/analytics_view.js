// Analytics View Controller (Chart.js)

const AnalyticsView = {
  statusChart: null,
  zoneChart: null,

  async render() {
    try {
      const res = await API.getAnalyticsMetrics();
      if (!res.success) throw new Error("Failed to load analytics");
      const m = res.metrics;

      // Update KPI numbers
      document.getElementById('analytics-fulfillment-rate').textContent = `${m.summary.fulfillment_rate}%`;
      document.getElementById('analytics-avg-time').textContent = `${m.avg_fulfillment_hours} hrs`;
      document.getElementById('analytics-sla-health').textContent = `${m.sla_on_time_percentage}%`;
      document.getElementById('analytics-total-exceptions').textContent = m.summary.open_exceptions_count;

      // Render Order Status Distribution (Doughnut)
      const statusCanvas = document.getElementById('chart-order-status');
      if (statusCanvas && window.Chart) {
        const labels = m.status_distribution.map(d => d.status);
        const data = m.status_distribution.map(d => d.count);
        
        const colors = {
          'PENDING': '#F59E0B',
          'ALLOCATED': '#3B82F6',
          'PICKING': '#06B6D4',
          'PACKED': '#8B5CF6',
          'DISPATCHED': '#10B981',
          'EXCEPTION': '#EF4444'
        };

        if (this.statusChart) this.statusChart.destroy();
        this.statusChart = new Chart(statusCanvas, {
          type: 'doughnut',
          data: {
            labels: labels,
            datasets: [{
              data: data,
              backgroundColor: labels.map(l => colors[l] || '#6B7280'),
              borderWidth: 0
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom',
                labels: { color: '#9CA3AF', font: { family: 'Inter', size: 11 } }
              }
            },
            cutout: '68%'
          }
        });
      }

      // Render Zone Stock Distribution (Bar Chart)
      const zoneCanvas = document.getElementById('chart-zone-stock');
      if (zoneCanvas && window.Chart) {
        const zoneLabels = m.zone_distribution.map(z => z.zone);
        const onHand = m.zone_distribution.map(z => z.total_units);
        const reserved = m.zone_distribution.map(z => z.reserved_units);
        const damaged = m.zone_distribution.map(z => z.damaged_units);

        if (this.zoneChart) this.zoneChart.destroy();
        this.zoneChart = new Chart(zoneCanvas, {
          type: 'bar',
          data: {
            labels: zoneLabels,
            datasets: [
              {
                label: 'On-Hand Units',
                data: onHand,
                backgroundColor: '#3B82F6',
                borderRadius: 4
              },
              {
                label: 'Reserved Units',
                data: reserved,
                backgroundColor: '#F59E0B',
                borderRadius: 4
              },
              {
                label: 'Damaged Units',
                data: damaged,
                backgroundColor: '#EF4444',
                borderRadius: 4
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                stacked: false,
                grid: { color: '#243042' },
                ticks: { color: '#9CA3AF' }
              },
              y: {
                stacked: false,
                grid: { color: '#243042' },
                ticks: { color: '#9CA3AF' }
              }
            },
            plugins: {
              legend: {
                position: 'bottom',
                labels: { color: '#9CA3AF', font: { family: 'Inter', size: 11 } }
              }
            }
          }
        });
      }

    } catch (e) {
      console.error(e);
      Toast.danger("Error loading analytics charts: " + e.message);
    }
  }
};

window.AnalyticsView = AnalyticsView;
