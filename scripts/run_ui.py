import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.ui.app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
