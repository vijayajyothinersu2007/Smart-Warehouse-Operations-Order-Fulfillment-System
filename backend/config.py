import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DATA_DIR, 'warehouse.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'warehouseiq-secret-key-2026')
    DATABASE = DATABASE_PATH
    DEBUG = True
    
    # Priority Scorer Weights
    WEIGHT_SLA = 0.45
    WEIGHT_TIER = 0.25
    WEIGHT_VALUE = 0.15
    WEIGHT_READINESS = 0.15

    # Customer Tier Base Scores
    TIER_SCORES = {
        'URGENT': 100,
        'VIP': 95,
        'EXPRESS': 75,
        'NORMAL': 45,
        'STANDARD': 40,
        'BULK': 25
    }
