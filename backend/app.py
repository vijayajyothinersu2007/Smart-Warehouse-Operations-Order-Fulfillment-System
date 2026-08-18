import os
from flask import Flask
from backend.config import Config, DATABASE_PATH
from backend.routes import (
    bp_views,
    bp_orders,
    bp_inventory,
    bp_allocation,
    bp_fulfillment,
    bp_exceptions,
    bp_analytics,
    bp_decisions
)
from backend.database.seeder import seed_database

def create_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_dir = os.path.join(base_dir, 'frontend', 'templates')
    static_dir = os.path.join(base_dir, 'frontend', 'static')

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )
    app.config.from_object(Config)

    # Register Blueprints
    app.register_blueprint(bp_views)
    app.register_blueprint(bp_orders)
    app.register_blueprint(bp_inventory)
    app.register_blueprint(bp_allocation)
    app.register_blueprint(bp_fulfillment)
    app.register_blueprint(bp_exceptions)
    app.register_blueprint(bp_analytics)
    app.register_blueprint(bp_decisions)

    # Ensure database exists and is seeded on startup if not present
    if not os.path.exists(DATABASE_PATH):
        print(f"Initializing and seeding SQLite database at {DATABASE_PATH}...")
        seed_database()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
