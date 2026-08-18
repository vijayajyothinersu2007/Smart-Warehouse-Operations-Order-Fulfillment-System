// Exceptions View Controller

const ExceptionsView = {
  async render() {
    try {
      const res = await API.getExceptions();
      if (!res.success) throw new Error("Failed to load exceptions");
      const exceptions = res.exceptions;

      const tbody = document.getElementById('exceptions-table-body');
      tbody.innerHTML = '';

      if (exceptions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:2rem;">No operational exceptions logged. System healthy!</td></tr>`;
        return;
      }

      exceptions.forEach(ex => {
        const tr = document.createElement('tr');

        let sevBadge = 'badge-warning';
        if (ex.severity === 'CRITICAL' || ex.severity === 'HIGH') sevBadge = 'badge-danger';
        else if (ex.severity === 'LOW') sevBadge = 'badge-normal';

        let statusBadge = ex.status === 'OPEN' ? 'badge-danger' : (ex.status === 'AUTO_RESOLVED' ? 'badge-passed' : 'badge-instock');

        tr.innerHTML = `
          <td>
            <div style="font-family:var(--font-mono); font-weight:700; color:#93C5FD;">#EXC-${ex.id}</div>
            <div style="font-size:0.75rem; color:var(--text-muted);">${ex.created_at}</div>
          </td>
          <td>
            <div style="font-weight:700; color:#FCA5A5;">${ex.exception_type}</div>
            <span class="badge ${sevBadge}">${ex.severity}</span>
          </td>
          <td>
            <div style="font-weight:600;">${ex.product_name || ex.product_id || 'N/A'}</div>
            <div style="font-size:0.75rem; color:var(--text-secondary); font-family:var(--font-mono);">${ex.bin_id || 'Zone Multi'}</div>
          </td>
          <td>
            <div style="font-size:0.85rem;">${ex.description}</div>
            <div style="font-size:0.78rem; color:#60A5FA; margin-top:4px;">
              <strong>Resolution:</strong> ${ex.applied_resolution || ex.proposed_resolution || 'Pending review'}
            </div>
          </td>
          <td>
            <span class="badge ${statusBadge}">${ex.status}</span>
          </td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-secondary btn-sm" onclick="DecisionModal.showByEntity('${ex.order_id || ex.product_id || ex.bin_id}')">
                🔍 Explain
              </button>
              ${ex.status === 'OPEN' ? `
                <button class="btn btn-success btn-sm" onclick="ExceptionsView.resolve(${ex.id})">
                  ✅ Resolve
                </button>
              ` : ''}
            </div>
          </td>
        `;

        tbody.appendChild(tr);
      });

    } catch (e) {
      console.error(e);
      Toast.danger("Error loading exceptions: " + e.message);
    }
  },

  async resolve(id) {
    try {
      const res = await API.resolveException(id, {
        applied_resolution: "Supervisor approved corrective adjustment.",
        resolved_by: "Supervisor Lead"
      });
      if (res.success) {
        Toast.success(res.message);
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
      }
    } catch (e) {
      Toast.danger("Error resolving exception: " + e.message);
    }
  },

  openDamagedModal() {
    this.populateProductAndBinsSelect('damaged-sku-select', 'damaged-bin-select');
    const modal = document.getElementById('report-damaged-modal-backdrop');
    if (modal) modal.classList.add('open');
  },

  closeDamagedModal() {
    const modal = document.getElementById('report-damaged-modal-backdrop');
    if (modal) modal.classList.remove('open');
  },

  openMissingModal() {
    this.populateProductAndBinsSelect('missing-sku-select', 'missing-bin-select');
    const modal = document.getElementById('report-missing-modal-backdrop');
    if (modal) modal.classList.add('open');
  },

  closeMissingModal() {
    const modal = document.getElementById('report-missing-modal-backdrop');
    if (modal) modal.classList.remove('open');
  },

  async populateProductAndBinsSelect(skuSelectId, binSelectId) {
    const pRes = await API.getInventory();
    const bRes = await API.getBins();
    
    if (pRes.success) {
      const pSel = document.getElementById(skuSelectId);
      if (pSel) {
        pSel.innerHTML = '';
        pRes.inventory.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.sku;
          opt.textContent = `${p.name} (${p.sku})`;
          pSel.appendChild(opt);
        });
      }
    }

    if (bRes.success) {
      const bSel = document.getElementById(binSelectId);
      if (bSel) {
        bSel.innerHTML = '';
        bRes.bins.forEach(b => {
          const opt = document.createElement('option');
          opt.value = b.id;
          opt.textContent = `${b.id} (${b.zone})`;
          bSel.appendChild(opt);
        });
      }
    }
  },

  async submitDamaged(e) {
    e.preventDefault();
    const sku = document.getElementById('damaged-sku-select').value;
    const bin = document.getElementById('damaged-bin-select').value;
    const qty = parseInt(document.getElementById('damaged-qty').value) || 1;

    try {
      const res = await API.reportDamaged({
        product_id: sku,
        bin_id: bin,
        damaged_qty: qty,
        reported_by: "Floor Operator"
      });

      if (res.success) {
        Toast.warning(`Reported ${qty} damaged unit(s). Engine decision: ${res.result.resolution}`);
        this.closeDamagedModal();
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
        if (window.InventoryView) window.InventoryView.render();
      } else {
        Toast.danger("Failed to report damaged item: " + res.error);
      }
    } catch (err) {
      Toast.danger("Error: " + err.message);
    }
  },

  async submitMissing(e) {
    e.preventDefault();
    const sku = document.getElementById('missing-sku-select').value;
    const bin = document.getElementById('missing-bin-select').value;

    try {
      const res = await API.reportMissing({
        product_id: sku,
        bin_id: bin,
        reported_by: "Floor Operator"
      });

      if (res.success) {
        Toast.danger(`Reported missing item in ${bin}. Bin inventory zeroed out.`);
        this.closeMissingModal();
        await this.render();
        if (window.DashboardView) window.DashboardView.render();
        if (window.InventoryView) window.InventoryView.render();
      } else {
        Toast.danger("Failed to report missing item: " + res.error);
      }
    } catch (err) {
      Toast.danger("Error: " + err.message);
    }
  }
};

window.ExceptionsView = ExceptionsView;
