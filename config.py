import os
from dotenv import load_dotenv

load_dotenv()

# Zerodha Kite Connect API credentials
API_KEY = os.getenv("KITE_API_KEY", "")
API_SECRET = os.getenv("KITE_API_SECRET", "")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "")

# Timezone
TIMEZONE = "Asia/Kolkata"

# Market hours (IST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

# Strategy parameters
SMA_PERIOD = 20
DEFAULT_TARGET_PCT = 2.0   # 2% target profit
DEFAULT_STOPLOSS_PCT = 1.0  # 1% stop-loss

# Order defaults
EXCHANGE = "NSE"
DEFAULT_QUANTITY = 1
PRODUCT_TYPE = "CNC"  # CNC for delivery, MIS for intraday

# Logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Polling interval in seconds for the main loop
POLL_INTERVAL = 60
