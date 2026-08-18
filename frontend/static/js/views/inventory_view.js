// Inventory View Controller

const InventoryView = {
  async render() {
    try {
      const res = await API.getInventory();
      if (!res.success) throw new Error("Failed to load inventory");
      const items = res.inventory;

      const tbody = document.getElementById('inventory-table-body');
      tbody.innerHTML = '';

      if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:2rem;">No inventory records found.</td></tr>`;
        return;
      }

      items.forEach(p => {
        const tr = document.createElement('tr');

        let statusBadge = 'badge-instock';
        let statusLabel = 'IN STOCK';
        if (p.stock_status === 'OUT_OF_STOCK') {
          statusBadge = 'badge-outofstock';
          statusLabel = 'OUT OF STOCK';
        } else if (p.stock_status === 'LOW_STOCK') {
          statusBadge = 'badge-lowstock';
          statusLabel = 'LOW STOCK';
        }

        tr.innerHTML = `
          <td>
            <div style="font-family:var(--font-mono); font-weight:700; color:#93C5FD;">${p.sku}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">${p.barcode}</div>
          </td>
          <td>
            <div style="font-weight:600;">${p.name}</div>
            <span class="badge badge-normal">${p.category}</span>
          </td>
          <td>
            <span style="font-size:1.1rem; font-weight:800; color:${p.total_available > 0 ? '#34D399' : '#F87171'};">
              ${p.total_available}
            </span>
          </td>
          <td>
            <span style="font-weight:600; color:#FBBF24;">${p.total_reserved}</span>
          </td>
          <td>
            <span style="font-weight:600; color:${p.total_damaged > 0 ? '#F87171' : 'var(--text-muted)'};">${p.total_damaged}</span>
          </td>
          <td>
            <span style="font-family:var(--font-mono); color:var(--text-secondary);">${p.reorder_point}</span>
          </td>
          <td>
            <span class="badge ${statusBadge}">${statusLabel}</span>
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="InventoryView.openAdjustModal('${p.sku}', '${p.name.replace(/'/g, "\\'")}')">
              ⚙️ Adjust
            </button>
          </td>
        `;

        tbody.appendChild(tr);
      });

    } catch (e) {
      console.error(e);
      Toast.danger("Error loading inventory: " + e.message);
    }
  },

  openAdjustModal(sku, name) {
    document.getElementById('adjust-sku').value = sku;
    document.getElementById('adjust-sku-display').textContent = `${name} (${sku})`;
    
    // Load bins for selection
    API.getBins().then(res => {
      if (res.success) {
        const select = document.getElementById('adjust-bin-select');
        select.innerHTML = '';
        res.bins.forEach(b => {
          const opt = document.createElement('option');
          opt.value = b.id;
          opt.textContent = `${b.id} (${b.zone} - ${b.total_units} units)`;
          select.appendChild(opt);
        });
      }
    });

    const modal = document.getElementById('adjust-stock-modal-backdrop');
    if (modal) modal.classList.add('open');
  },

  closeAdjustModal() {
    const modal = document.getElementById('adjust-stock-modal-backdrop');
    if (modal) modal.classList.remove('open');
  },

  async submitAdjustStock(e) {
    e.preventDefault();
    const sku = document.getElementById('adjust-sku').value;
    const bin = document.getElementById('adjust-bin-select').value;
    const qty = parseInt(document.getElementById('adjust-qty').value) || 0;

    try {
      const res = await API.adjustStock({
        product_id: sku,
        bin_id: bin,
        quantity_on_hand: qty
      });

      if (res.success) {
        Toast.success(res.message);
        this.closeAdjustModal();
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
      } else {
        Toast.danger("Failed to adjust stock: " + res.error);
      }
    } catch (err) {
      Toast.danger("Error: " + err.message);
    }
  }
};

window.InventoryView = InventoryView;
