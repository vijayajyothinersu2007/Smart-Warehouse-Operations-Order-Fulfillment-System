// Explainable Decision Card Modal Component

const DecisionModal = {
  backdrop: null,

  init() {
    this.backdrop = document.getElementById('decision-modal-backdrop');
    const closeBtn = document.getElementById('decision-modal-close');
    const okBtn = document.getElementById('decision-modal-ok');
    
    if (closeBtn) closeBtn.onclick = () => this.close();
    if (okBtn) okBtn.onclick = () => this.close();
    if (this.backdrop) {
      this.backdrop.onclick = (e) => {
        if (e.target === this.backdrop) this.close();
      };
    }
  },

  show(decision) {
    this.init();
    if (!this.backdrop || !decision) return;

    const titleEl = document.getElementById('modal-decision-title');
    const actionBadgeEl = document.getElementById('modal-decision-action');
    const confidenceEl = document.getElementById('modal-decision-confidence');
    const rationaleEl = document.getElementById('modal-decision-rationale');
    const factorsContainer = document.getElementById('modal-decision-factors');
    const recommendationEl = document.getElementById('modal-decision-recommendation');
    const alternativesContainer = document.getElementById('modal-decision-alternatives');

    // Title & Badges
    titleEl.textContent = `Autonomous Decision: ${decision.decision_type || 'SYSTEM_DECISION'}`;
    actionBadgeEl.textContent = decision.decision_action || 'ACTION_EXECUTED';
    
    const confidence = decision.confidence_score ? Math.round(decision.confidence_score * 100) : 95;
    confidenceEl.textContent = `${confidence}% Confidence`;
    confidenceEl.className = `badge ${confidence >= 90 ? 'badge-passed' : 'badge-warning'}`;

    // Rationale
    rationaleEl.textContent = decision.rationale || 'No detailed rationale recorded.';

    // Factors Grid
    factorsContainer.innerHTML = '';
    const factors = typeof decision.factors === 'string' ? JSON.parse(decision.factors) : (decision.factors || {});
    
    for (const [key, value] of Object.entries(factors)) {
      if (typeof value === 'object' && value !== null) continue; // skip nested for high-level chips
      const chip = document.createElement('div');
      chip.className = 'factor-chip';
      chip.innerHTML = `
        <div class="factor-chip-label">${key.replace(/_/g, ' ')}</div>
        <div class="factor-chip-val">${value}</div>
      `;
      factorsContainer.appendChild(chip);
    }

    // Recommendation
    if (recommendationEl) {
      recommendationEl.textContent = decision.recommended_action || 'Execute recommended workflow step.';
    }

    // Alternatives Considered
    alternativesContainer.innerHTML = '';
    const alternatives = typeof decision.alternatives === 'string' ? JSON.parse(decision.alternatives) : (decision.alternatives || []);
    
    if (alternatives && alternatives.length > 0) {
      alternatives.forEach(alt => {
        const item = document.createElement('div');
        item.className = 'alt-item';
        item.innerHTML = `
          <div class="alt-item-header">
            <span>⛔ REJECTED:</span> ${alt.alternative || 'Alternative Option'}
          </div>
          <div class="alt-item-reason"><strong>Why Rejected:</strong> ${alt.reason || 'Sub-optimal operational trade-off.'}</div>
        `;
        alternativesContainer.appendChild(item);
      });
    } else {
      alternativesContainer.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-muted);">No competing alternatives required rejection.</div>';
    }

    this.backdrop.classList.add('open');
  },

  close() {
    if (this.backdrop) {
      this.backdrop.classList.remove('open');
    }
  },

  async showByEntity(entityId) {
    try {
      const res = await API.getDecisions(entityId, 1);
      if (res.success && res.decisions && res.decisions.length > 0) {
        this.show(res.decisions[0]);
      } else {
        Toast.warning(`No specific decision log found for ${entityId}`);
      }
    } catch (e) {
      Toast.danger('Failed to load decision details: ' + e.message);
    }
  },

  async showById(id) {
    try {
      const res = await API.getDecision(id);
      if (res.success && res.decision) {
        this.show(res.decision);
      } else {
        Toast.warning(`Decision #${id} not found.`);
      }
    } catch (e) {
      Toast.danger('Failed to load decision: ' + e.message);
    }
  }
};

window.DecisionModal = DecisionModal;
