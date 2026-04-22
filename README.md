# Indian Stock Market Trading App 📈

An automated trading application for the Indian stock market (NSE/BSE) built with Python and Streamlit. It uses a 20-period SMA crossover strategy and provides a real-time visual dashboard.

## ✨ Features
- **Live Dashboard**: Visualise active positions, trade history, and strategy charts.
- **Real-time Prices**: Accurate stock prices fetched via `yfinance` (.NS for NSE, .BO for BSE).
- **Stock Search**: Search and add any symbol to your watchlist instantly.
- **IST Precision**: Synced to Indian Standard Time (Asia/Kolkata) with NSE/BSE market hours (9:15 AM - 3:30 PM).
- **Risk Management**: Automated Stop-loss (1%) and Target Profit (2%) calculation.
- **Broker Ready**: Built-in support for Zerodha Kite Connect API.

## 🚀 Getting Started

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in the root directory and add your Kite API credentials:
```env
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=your_access_token
```

### 3. Run the App
Launch the visual dashboard:
```bash
streamlit run dashboard.py
```

Start the automated trading engine (runs in background):
```bash
python main.py
```

## 📊 Strategy
- **Entry**: BUY when the latest close crosses ABOVE the 20-period SMA.
- **Exit**: SELL when the latest close crosses BELOW the 20-period SMA.
- **Stop-loss**: Automated at 1% below entry.
- **Target**: Automated at 2% above entry.

## ⚠️ Disclaimer
Trading in the stock market involves risk. This software is provided for educational and informational purposes. Use it at your own risk.
