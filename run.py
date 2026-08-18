import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app import create_app

app = create_app()

if __name__ == '__main__':
    # Render cloud provider path ki dynamic PORT detection, Local run ki 5000 fallback
    port = int(os.environ.get("PORT", 5000))
    
    print("=" * 70)
    print(" 🚀 WarehouseIQ: Smart Warehouse Operations & Decision Engine")
    print(f" 🌐 Server started on port: {port}")
    print(" ⚡ Phase 1: Core Operations & Stock Contention Engine Loaded")
    print("=" * 70)
    
    # host='0.0.0.0' ivvadam valla Render deploy avthundi & local ga kuda 127.0.0.1:5000 lo same output vasthundi
    app.run(host='0.0.0.0', port=port, debug=False)