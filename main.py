import logging
import os
from app import app

# Set up logging for easier debugging
logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # ← bunu ekledik
    app.run(host="0.0.0.0", port=port, debug=True)
