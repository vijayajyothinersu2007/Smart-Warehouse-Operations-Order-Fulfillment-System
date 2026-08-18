from backend.routes.views import bp_views
from backend.routes.api_orders import bp_orders
from backend.routes.api_inventory import bp_inventory
from backend.routes.api_allocation import bp_allocation
from backend.routes.api_fulfillment import bp_fulfillment
from backend.routes.api_exceptions import bp_exceptions
from backend.routes.api_analytics import bp_analytics
from backend.routes.api_decisions import bp_decisions

__all__ = [
    'bp_views',
    'bp_orders',
    'bp_inventory',
    'bp_allocation',
    'bp_fulfillment',
    'bp_exceptions',
    'bp_analytics',
    'bp_decisions'
]
