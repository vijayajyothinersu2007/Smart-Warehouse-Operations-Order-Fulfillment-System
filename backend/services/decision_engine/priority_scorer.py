import json
from datetime import datetime, timezone
from backend.config import Config

class PriorityScorer:
    """
    Computes dynamic priority score (0 - 100) for warehouse orders based on:
    - SLA Urgency (time to deadline)
    - Customer Tier (URGENT, VIP, EXPRESS, NORMAL, etc.)
    - Order Value
    - Stock Readiness
    """

    @staticmethod
    def calculate_score(order_data, stock_readiness=1.0):
        """
        Calculates priority score and returns detailed factors for explainability.
        """
        # 1. Customer Tier Factor (0 - 100)
        tier = (order_data.get('customer_tier') or 'NORMAL').upper()
        tier_score = Config.TIER_SCORES.get(tier, 40)
        if order_data.get('is_urgent'):
            tier_score = max(tier_score, 95)

        # 2. SLA Urgency Factor (0 - 100)
        target_sla_str = order_data.get('target_sla_cutoff')
        hours_remaining = 24.0
        sla_score = 50.0

        if target_sla_str:
            try:
                # Handle SQLite ISO format strings
                if 'T' in target_sla_str:
                    target_dt = datetime.fromisoformat(target_sla_str)
                else:
                    target_dt = datetime.strptime(target_sla_str, "%Y-%m-%d %H:%M:%S")
                
                # Assume local / UTC relative comparison
                now = datetime.now()
                delta = (target_dt - now).total_seconds() / 3600.0
                hours_remaining = round(max(-24.0, delta), 2)

                if hours_remaining <= 0:
                    sla_score = 100.0  # Overdue / Immediate breach
                elif hours_remaining <= 2.0:
                    sla_score = 98.0   # Critical SLA window (< 2 hours)
                elif hours_remaining <= 6.0:
                    sla_score = 85.0
                elif hours_remaining <= 12.0:
                    sla_score = 65.0
                elif hours_remaining <= 24.0:
                    sla_score = 45.0
                else:
                    sla_score = 25.0
            except Exception:
                sla_score = 50.0

        # 3. Order Value Factor (0 - 100)
        total_amount = float(order_data.get('total_amount') or 0.0)
        value_score = min(100.0, (total_amount / 1000.0) * 100.0)

        # 4. Stock Readiness Factor (0 - 100)
        readiness_score = float(stock_readiness) * 100.0

        # Weighted Composite Score
        composite_score = (
            (sla_score * Config.WEIGHT_SLA) +
            (tier_score * Config.WEIGHT_TIER) +
            (value_score * Config.WEIGHT_VALUE) +
            (readiness_score * Config.WEIGHT_READINESS)
        )

        final_score = round(min(100.0, max(0.0, composite_score)), 2)

        # Build factors dictionary for Decision Card explainability
        factors = {
            "tier": tier,
            "tier_score": tier_score,
            "hours_remaining_sla": hours_remaining,
            "sla_score": sla_score,
            "order_value_usd": total_amount,
            "value_score": round(value_score, 2),
            "stock_readiness": round(readiness_score, 2),
            "weights": {
                "sla": Config.WEIGHT_SLA,
                "tier": Config.WEIGHT_TIER,
                "value": Config.WEIGHT_VALUE,
                "readiness": Config.WEIGHT_READINESS
            },
            "is_critical_escalated": (hours_remaining <= 2.0 or tier in ['URGENT', 'VIP'])
        }

        rationale = (
            f"Calculated Priority Score: {final_score}/100. "
            f"Customer Tier '{tier}' (base score {tier_score}), "
            f"SLA deadline in {hours_remaining} hrs (urgency score {sla_score}), "
            f"Order Value ${total_amount:,.2f}."
        )

        return {
            "priority_score": final_score,
            "is_urgent": 1 if (final_score >= 80.0 or tier in ['URGENT', 'VIP']) else 0,
            "factors": factors,
            "rationale": rationale
        }
