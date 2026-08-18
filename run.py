import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app import create_app

app = create_app()

if __name__ == '__main__':
    print("=" * 70)
    print(" 🚀 WarehouseIQ: Smart Warehouse Operations & Decision Engine")
    print(" 🌐 Running on http://127.0.0.1:5000")
    print(" ⚡ Phase 1: Core Operations & Stock Contention Engine Loaded")
    print("=" * 70)
    app.run(host='127.0.0.1', port=5000, debug=True)
