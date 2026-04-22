#!/usr/bin/env python3
"""
Streamlit dashboard for the Indian Stock Market Trading App.

Modules:
  1. Market Status — real-time open/closed indicator with IST clock.
  2. Search Bar — search and select any NSE/BSE stock symbol.
  3. Positions — live table of current holdings with P&L.
  4. Strategy Chart — Buy / Target / Stop-loss visualisation per symbol.
  5. Credentials sidebar — input fields for Kite API creds.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import pytz
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from data_store import STORE_PATH, StoreState, load, save
from demo_data import seed_demo_data
from market_data import (
    DEFAULT_NSE_SYMBOLS,
    fetch_historical_closes,
    fetch_current_price,
    fetch_watchlist_data,
    search_symbols,
)
from market_hours import MARKET_CLOSE, MARKET_OPEN, is_market_open, now_ist
from strategy import calculate_stoploss, calculate_target, compute_sma

IST = pytz.timezone(config.TIMEZONE)

# ── Page config ──────────────────────────────────────
st.set_page_config(
    page_title="NSE/BSE Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────
st.markdown("""
<style>
    /* Global theme tweaks */
    .main .block-container { padding-top: 1.5rem; }
    
    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #0e1117 0%, #1a1f2e 100%);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label {
        color: #a0aec0 !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    
    /* Status badges */
    .status-open {
        background: linear-gradient(135deg, #22543d, #276749);
        color: #9ae6b4;
        padding: 8px 20px;
        border-radius: 24px;
        font-weight: 700;
        font-size: 1rem;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #48bb78;
        box-shadow: 0 0 12px rgba(72, 187, 120, 0.3);
    }
    .status-closed {
        background: linear-gradient(135deg, #742a2a, #9b2c2c);
        color: #feb2b2;
        padding: 8px 20px;
        border-radius: 24px;
        font-weight: 700;
        font-size: 1rem;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #fc8181;
        box-shadow: 0 0 12px rgba(252, 129, 129, 0.2);
    }
    
    /* Signal badges */
    .signal-buy {
        background: #22543d; color: #9ae6b4;
        padding: 4px 14px; border-radius: 16px; font-weight: 700;
        border: 1px solid #48bb78; font-size: 0.85rem;
    }
    .signal-sell {
        background: #742a2a; color: #feb2b2;
        padding: 4px 14px; border-radius: 16px; font-weight: 700;
        border: 1px solid #fc8181; font-size: 0.85rem;
    }
    .signal-hold {
        background: #2d3748; color: #e2e8f0;
        padding: 4px 14px; border-radius: 16px; font-weight: 700;
        border: 1px solid #4a5568; font-size: 0.85rem;
    }
    
    /* Engine heartbeat */
    .engine-alive {
        background: #1a365d; color: #90cdf4;
        padding: 6px 16px; border-radius: 20px; font-size: 0.8rem;
        border: 1px solid #2b6cb0;
        display: inline-flex; align-items: center; gap: 6px;
    }
    .engine-dead {
        background: #3c1f1f; color: #fca5a5;
        padding: 6px 16px; border-radius: 20px; font-size: 0.8rem;
        border: 1px solid #991b1b;
        display: inline-flex; align-items: center; gap: 6px;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.15rem;
        font-weight: 700;
        color: #e2e8f0;
        padding-bottom: 4px;
        margin-bottom: 12px;
        border-bottom: 2px solid #2d3748;
    }

    /* Table styling */
    .dataframe { font-size: 0.9rem !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1117 0%, #151922 100%);
    }
    [data-testid="stSidebar"] .stMarkdown h1 { font-size: 1.3rem; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar — Credentials & Settings ────────────────────────────────
with st.sidebar:
    st.markdown("# ⚙️ Configuration")
    st.markdown("---")

    st.markdown("### 🔑 API Credentials")
    st.caption("Provide Zerodha Kite Connect credentials. Values entered here override environment / .env settings for this session only.")

    api_key = st.text_input(
        "API Key",
        value=config.API_KEY,
        type="password",
        help="Your Kite Connect API key",
    )
    api_secret = st.text_input(
        "API Secret",
        value=config.API_SECRET,
        type="password",
        help="Your Kite Connect API secret",
    )
    access_token = st.text_input(
        "Access Token",
        value=config.ACCESS_TOKEN,
        type="password",
        help="Session access token (generated daily)",
    )

    creds_ok = all([api_key, api_secret, access_token])
    if creds_ok:
        st.success("✅ Credentials provided")
    else:
        st.warning("⚠️ Credentials incomplete — using yfinance data")

    st.markdown("---")
    st.markdown("### 📊 Strategy Parameters")
    sma_period = st.number_input("SMA Period", min_value=2, max_value=200, value=config.SMA_PERIOD)
    target_pct = st.number_input("Target Profit %", min_value=0.1, max_value=50.0, value=config.DEFAULT_TARGET_PCT, step=0.1)
    stoploss_pct = st.number_input("Stop-loss %", min_value=0.1, max_value=50.0, value=config.DEFAULT_STOPLOSS_PCT, step=0.1)

    st.markdown("---")
    st.markdown("### 🏛️ Exchange")
    exchange = st.selectbox("Default Exchange", ["NSE", "BSE"], index=0, help="NSE appends .NS, BSE appends .BO for yfinance")

    st.markdown("---")
    st.markdown("### 🔄 Data")
    if st.button("🔄 Refresh Data (yfinance)", use_container_width=True):
        seed_demo_data()
        st.rerun()

    st.markdown("---")
    st.caption(f"📁 Data store: `{STORE_PATH}`")
    st.caption(f"🕐 TZ: {config.TIMEZONE}")
    st.caption("📡 Prices: yfinance (real-time)")


# ── Ensure demo data exists ────────────────────────────────️
if not os.path.exists(STORE_PATH):
    seed_demo_data()

state: StoreState = load()

# ── Header ──────────────────────────────────────️
now = now_ist()

st.markdown("# 📈 Indian Stock Market — Trading Dashboard")
st.caption("NSE / BSE • Real-time prices via yfinance • SMA Crossover Strategy")

# ── Section 1: Market Status ────────────────────────️
st.markdown('<div class="section-header">🏛️ Market Status</div>', unsafe_allow_html=True)

col_status, col_time, col_session, col_engine = st.columns([1.5, 1.5, 1.5, 1.5])

market_open = is_market_open(now)

with col_status:
    if market_open:
        st.markdown('<span class="status-open">🟢 MARKET OPEN</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-closed">🔴 MARKET CLOSED</span>', unsafe_allow_html=True)

with col_time:
    st.metric("🕐 IST Time", now.strftime("%I:%M:%S %p"))

with col_session:
    st.metric("📅 Session", now.strftime("%a, %d %b %Y"))

with col_engine:
    hb = state.last_engine_heartbeat
    if state.engine_running and hb:
        try:
            hb_dt = datetime.fromisoformat(hb)
            age = (now - hb_dt).total_seconds()
            hb_label = f"{int(age)}s ago" if age < 120 else f"{int(age/60)}m ago"
            st.markdown(f'<span class="engine-alive">⚡ Engine active • heartbeat {hb_label}</span>', unsafe_allow_html=True)
        except ValueError:
            st.markdown('<span class="engine-dead">⚠️ Engine heartbeat error</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="engine-dead">💤 Engine stopped</span>', unsafe_allow_html=True)

# Market hours progress bar
if market_open:
    mkt_open_dt = now.replace(hour=config.MARKET_OPEN_HOUR, minute=config.MARKET_OPEN_MINUTE, second=0, microsecond=0)
    mkt_close_dt = now.replace(hour=config.MARKET_CLOSE_HOUR, minute=config.MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    total = (mkt_close_dt - mkt_open_dt).total_seconds()
    elapsed = (now - mkt_open_dt).total_seconds()
    progress = min(max(elapsed / total, 0), 1.0)
    remaining_min = max(0, int((mkt_close_dt - now).total_seconds() / 60))
    st.progress(progress, text=f"Session progress: {progress*100:.0f}% — {remaining_min} min remaining until 3:30 PM")
else:
    st.info(f"🕐 Market hours: **{MARKET_OPEN.strftime('%I:%M %p')}** – **{MARKET_CLOSE.strftime('%I:%M %p')}** IST, Mon–Fri")

st.markdown("")

# ── Section 2: Stock Search Bar ────────────────────────️
st.markdown('<div class="section-header">🔍 Stock Search</div>', unsafe_allow_html=True)

search_col, action_col = st.columns([3, 1])

with search_col:
    search_query = st.text_input(
        "Search NSE/BSE Symbol",
        value="",
        placeholder="Type symbol name (e.g. RELIANCE, TCS, SBIN...)",
        help="Search for any NSE/BSE stock. Prices fetched from yfinance in real-time.",
    )

matching_symbols = search_symbols(search_query) if search_query else []

with action_col:
    if search_query and matching_symbols:
        add_symbol = st.selectbox(
            "Matching Symbols",
            matching_symbols,
            index=0,
            help="Select a symbol from matches",
        )
        if st.button("➕ Add to Watchlist", use_container_width=True):
            with st.spinner(f"Fetching real-time data for {add_symbol}..."):
                new_data = fetch_watchlist_data(
                    [add_symbol],
                    exchange=exchange,
                    sma_period=sma_period,
                    target_pct=target_pct,
                    stoploss_pct=stoploss_pct,
                )
                if new_data:
                    for sym, sig_data in new_data.items():
                        state.watchlist_signals[sym] = sig_data
                    save(state)
                    st.success(f"✅ Added {add_symbol} with real-time data")
                    st.rerun()
                else:
                    st.error(f"❌ Could not fetch data for {add_symbol}. Check symbol and try again.")
    elif search_query:
        st.info("No matching symbols found. Try typing a valid NSE/BSE symbol.")

# Show search results preview
if search_query and matching_symbols:
    with st.expander(f"🔎 {len(matching_symbols)} symbols matching '{search_query}'", expanded=False):
        st.write(", ".join(matching_symbols))

st.markdown("")

# ── Section 3: Positions / Active Trades ────────────────────────️
st.markdown('<div class="section-header">💼 Current Positions & Active Trades</div>', unsafe_allow_html=True)

tab_positions, tab_trades = st.tabs(["📊 Positions", "📜 Trade History"])

with tab_positions:
    if state.positions:
        df_pos = pd.DataFrame(state.positions)
        display_cols = {
            "tradingsymbol": "Symbol",
            "exchange": "Exchange",
            "quantity": "Qty",
            "average_price": "Avg Price ₹",
            "last_price": "LTP ₹",
            "pnl": "P&L ₹",
            "product": "Product",
        }
        df_display = df_pos.rename(columns=display_cols)
        cols_to_show = [v for v in display_cols.values() if v in df_display.columns]
        df_display = df_display[cols_to_show]

        total_pnl = df_display["P&L ₹"].sum()

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Active Positions", len(df_display))
        with kpi2:
            st.metric("Total P&L", f"₹{total_pnl:,.2f}", delta=f"{total_pnl:+,.2f}")
        with kpi3:
            winners = len(df_display[df_display["P&L ₹"] > 0])
            st.metric("Win Rate", f"{winners}/{len(df_display)}")

        def color_pnl(val):
            if isinstance(val, (int, float)):
                color = "#48bb78" if val > 0 else "#fc8181" if val < 0 else "#e2e8f0"
                return f"color: {color}; font-weight: 700"
            return ""

        styled = df_display.style.applymap(color_pnl, subset=["P&L ₹"])
        styled = styled.format({"Avg Price ₹": "₹{:,.2f}", "LTP ₹": "₹{:,.2f}", "P&L ₹": "₹{:+,.2f}"})
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.info("No open positions.")

with tab_trades:
    if state.trades:
        df_trades = pd.DataFrame(state.trades)
        display_trade_cols = {
            "symbol": "Symbol",
            "signal": "Signal",
            "entry_price": "Entry ₹",
            "target": "Target ₹",
            "stoploss": "Stop-loss ₹",
            "quantity": "Qty",
            "order_id": "Order ID",
            "timestamp": "Time (IST)",
            "status": "Status",
        }
        df_t = df_trades.rename(columns=display_trade_cols)
        cols_show = [v for v in display_trade_cols.values() if v in df_t.columns]
        df_t = df_t[cols_show]

        def style_status(val):
            if val == "ACTIVE":
                return "color: #48bb78; font-weight: 700"
            if val == "CLOSED":
                return "color: #a0aec0; font-weight: 700"
            return ""

        styled_t = df_t.style.applymap(style_status, subset=["Status"])
        styled_t = styled_t.format({"Entry ₹": "₹{:,.2f}", "Target ₹": "₹{:,.2f}", "Stop-loss ₹": "₹{:,.2f}"})
        st.dataframe(styled_t, use_container_width=True, hide_index=True)
    else:
        st.info("No trade history yet.")

st.markdown("")

# ── Section 4: Strategy Visualization ──────────────────────️
st.markdown('<div class="section-header">📉 Strategy Visualisation — Buy / Target / Stop-loss</div>', unsafe_allow_html=True)

symbols = list(state.watchlist_signals.keys())
if not symbols:
    st.info("No watchlist data available. Use the search bar above to add stocks, or refresh data from the sidebar.")
else:
    selected_symbol = st.selectbox(
        "Select Symbol for Chart",
        symbols,
        index=0,
        help="Pick a stock to visualise strategy levels. Add more via the search bar above.",
    )

    sig_data = state.watchlist_signals[selected_symbol]
    closes = sig_data.get("closes", [])
    current_price = sig_data["price"]
    sma_value = sig_data["sma"]
    target_val = sig_data["target"]
    stoploss_val = sig_data["stoploss"]
    signal_str = sig_data["signal"]

    # Recompute target/stoploss with current sidebar params
    if signal_str == "BUY":
        target_val = calculate_target(current_price, target_pct)
        stoploss_val = calculate_stoploss(current_price, stoploss_pct)

    # Recompute SMA with sidebar period
    sma_value_display = compute_sma(closes, sma_period) if closes else 0.0
    if sma_value_display is None:
        sma_value_display = 0.0
    else:
        sma_value_display = round(sma_value_display, 2)

    # Signal badge
    badge_cls = {"BUY": "signal-buy", "SELL": "signal-sell"}.get(signal_str, "signal-hold")
    badge_emoji = {"BUY": "🟢", "SELL": "🔴"}.get(signal_str, "⚪")

    info_cols = st.columns(5)
    with info_cols[0]:
        st.markdown(f'<span class="{badge_cls}">{badge_emoji} {signal_str}</span>', unsafe_allow_html=True)
    with info_cols[1]:
        st.metric("Price", f"₹{current_price:,.2f}")
    with info_cols[2]:
        st.metric(f"SMA ({sma_period})", f"₹{sma_value_display:,.2f}")
    with info_cols[3]:
        st.metric("Target", f"₹{target_val:,.2f}" if target_val else "—")
    with info_cols[4]:
        st.metric("Stop-loss", f"₹{stoploss_val:,.2f}" if stoploss_val else "—")

    if closes and len(closes) > 1:
        x_axis = list(range(1, len(closes) + 1))

        # Compute rolling SMA for the chart
        sma_line = []
        for i in range(len(closes)):
            if i + 1 >= sma_period:
                sma_line.append(round(sum(closes[i + 1 - sma_period:i + 1]) / sma_period, 2))
            else:
                sma_line.append(None)

        fig = go.Figure()

        # Price line
        fig.add_trace(go.Scatter(
            x=x_axis, y=closes,
            mode="lines+markers",
            name="Close",
            line=dict(color="#63b3ed", width=2.5),
            marker=dict(size=4),
        ))

        # SMA line
        sma_x = [x for x, v in zip(x_axis, sma_line) if v is not None]
        sma_y = [v for v in sma_line if v is not None]
        fig.add_trace(go.Scatter(
            x=sma_x, y=sma_y,
            mode="lines",
            name=f"SMA ({sma_period})",
            line=dict(color="#fbd38d", width=2, dash="dot"),
        ))

        # Current price marker
        fig.add_trace(go.Scatter(
            x=[x_axis[-1]], y=[current_price],
            mode="markers",
            name=f"Current ₹{current_price:,.2f}",
            marker=dict(color="#63b3ed", size=14, symbol="diamond",
                        line=dict(width=2, color="white")),
            showlegend=True,
        ))

        # Target / SL horizontal lines (only if BUY signal)
        if target_val > 0:
            fig.add_hline(
                y=target_val, line_dash="dash", line_color="#48bb78", line_width=2,
                annotation_text=f"Target ₹{target_val:,.2f}",
                annotation_position="top left",
                annotation_font=dict(color="#48bb78", size=12),
            )
        if stoploss_val > 0:
            fig.add_hline(
                y=stoploss_val, line_dash="dash", line_color="#fc8181", line_width=2,
                annotation_text=f"SL ₹{stoploss_val:,.2f}",
                annotation_position="bottom left",
                annotation_font=dict(color="#fc8181", size=12),
            )

        # Buy / Sell annotation
        if signal_str == "BUY":
            fig.add_annotation(
                x=x_axis[-1], y=current_price,
                text="▲ BUY", showarrow=True, arrowhead=2,
                arrowcolor="#48bb78", font=dict(color="#48bb78", size=14, family="Arial Black"),
                ax=0, ay=-40,
            )
            # Shade target-SL band
            fig.add_hrect(
                y0=stoploss_val, y1=target_val,
                fillcolor="rgba(72,187,120,0.08)", line_width=0,
                annotation_text="Risk/Reward Zone", annotation_position="top right",
                annotation_font=dict(color="#a0aec0", size=10),
            )
        elif signal_str == "SELL":
            fig.add_annotation(
                x=x_axis[-1], y=current_price,
                text="▼ SELL", showarrow=True, arrowhead=2,
                arrowcolor="#fc8181", font=dict(color="#fc8181", size=14, family="Arial Black"),
                ax=0, ay=40,
            )

        fig.update_layout(
            title=dict(text=f"{selected_symbol} — Price & SMA Strategy (Real Data)", font=dict(size=18)),
            xaxis_title="Trading Day",
            yaxis_title="Price (₹)",
            template="plotly_dark",
            height=520,
            margin=dict(l=60, r=30, t=60, b=40),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                bgcolor="rgba(0,0,0,0)",
            ),
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

    # ── Multi-symbol overview grid ────────────────────️
    st.markdown('<div class="section-header">🗂️ Watchlist Overview</div>', unsafe_allow_html=True)

    overview_data = []
    for sym, data in state.watchlist_signals.items():
        sig = data["signal"]
        badge = {"BUY": "🟢 BUY", "SELL": "🔴 SELL"}.get(sig, "⚪ HOLD")
        overview_data.append({
            "Symbol": sym,
            "Signal": badge,
            "Price ₹": data["price"],
            f"SMA ({sma_period}) ₹": data["sma"],
            "Target ₹": data["target"] if data["target"] else "—",
            "SL ₹": data["stoploss"] if data["stoploss" ] else "—",
        })

    df_overview = pd.DataFrame(overview_data)
    st.dataframe(df_overview, use_container_width=True, hide_index=True)


# ── Footer ─────────────────────────️
st.markdown("---")
fcol1, fcol2, fcol3 = st.columns(3)
with fcol1:
    st.caption("📡 Prices from yfinance (NSE .NS / BSE .BO). Connect Kite credentials for live trading.")
with fcol2:
    st.caption(f"⏱️ Last refresh: {now.strftime('%I:%M:%S %p IST')}")
with fcol3:
    st.caption("Built with Streamlit • Plotly • yfinance")
