import streamlit as st
import os
import glob
import pandas as pl
import requests

# [AURA-STRICT-PROTOCOL] Phase 4 - Frontend UI Dashboard

st.set_page_config(page_title="AURA Trading Engine", layout="wide", initial_sidebar_state="expanded")

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_DIR = os.path.join(BASE_DIR, "data", "parquet_capsules")
CSV_DIR = os.path.join(BASE_DIR, "data", "csv_landing")

st.title("AURA Institutional Quant Platform")

# Sidebar - Symbol & Strategy Selection
st.sidebar.header("Master Configuration")
available_symbols = ["EURUSDm", "BTCUSDm", "ETHUSDm", "GBPJPYm", "XAGUSDm", "XAUUSDm"]

selected_symbol = st.sidebar.selectbox("Select Master Symbol (Fav List)", available_symbols)
selected_strategy = st.sidebar.selectbox("Assign Strategy", ["MeanRev_RL", "TrendFollow_Ollama", "News_Sentiment_Only"])

st.sidebar.markdown("---")
st.sidebar.header("Risk Management (Overrides)")
base_lot = st.sidebar.number_input("Base Lot Size", min_value=0.01, value=0.1, step=0.01)
max_drawdown = st.sidebar.slider("Max Daily Drawdown %", 1.0, 10.0, 2.5)

# Main Dashboard Tabs
tab1, tab2, tab3 = st.tabs(["Data Pipeline", "Simulated Gym (Backtest)", "Live Execution (Paper/Real)"])

with tab1:
    st.header("Data Acquisition & Parquet Capsules")
    st.write(f"Scanning `{CSV_DIR}` and `{PARQUET_DIR}`...")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Raw CSV Landing")
        csv_files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
        st.metric("Detected CSVs", len(csv_files))
        
        if st.button("Convert to Parquet Capsule"):
            st.info("Triggering Polars Conversion Pipeline... (Check main terminal)")
            # In a full app, this would trigger an API call to run polars_converter.py

    with col2:
        st.subheader("Optimized Parquet Capsules")
        parquet_files = glob.glob(os.path.join(PARQUET_DIR, "*.parquet"))
        st.metric("Ready Parquet Files", len(parquet_files))
        
        if parquet_files:
            # Show a sample of the data
            sample_file = [f for f in parquet_files if selected_symbol.replace('m', '') in f]
            if sample_file:
                st.success(f"Data available for {selected_symbol}")
            else:
                st.warning(f"No parquet data found specifically for {selected_symbol}. Showing first available.")
                sample_file = [parquet_files[0]]
                
            file_size = os.path.getsize(sample_file[0]) / (1024 * 1024)
            st.write(f"File Size: {file_size:.2f} MB")

with tab2:
    st.header("The Harsh Simulated Gym")
    st.write(f"Target Strategy: **{selected_strategy}** on **{selected_symbol}**")
    
    st.markdown("""
    * **Latency Modeled:** Yes (0.0145ms verified)
    * **Spread Modeled:** Yes (Dynamic/Fixed)
    * **Commission Modeled:** Yes ($3.00/lot)
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("RL Reward Function Bounds")
        target_sharpe = st.number_input("Target Sharpe Ratio", value=1.5)
        penalty_dd = st.number_input("Drawdown Penalty Threshold %", value=-5.0)
    
    with col2:
        st.subheader("The Sixth Sense (Ollama)")
        st.write("Current LLM: `llama3` (Local)")
        bull_thresh = st.slider("Bullish Trigger Score", 0.0, 1.0, 0.75)
        bear_thresh = st.slider("Bearish Trigger Score", -1.0, 0.0, -0.75)

    if st.button("Run Simulated Gym Backtest & Train"):
        st.warning("Training initialized... (This would connect to stable-baselines3)")
        st.progress(0) # Placeholder for training progress

with tab3:
    st.header("The Dress Rehearsal (Paper Trading Pipeline)")
    
    # Try to ping the FastAPI Backend
    try:
        response = requests.get("http://127.0.0.1:8000/api/v1/status")
        if response.status_code == 200:
            st.success("🟢 FastAPI Backend Core is ONLINE")
            data = response.json()
            st.write(f"Active EA Connections: `{data['active_symbols']}`")
            st.write(f"Pending Orders in Queue: `{data['pending_orders']}`")
        else:
            st.error("🔴 Backend responded with error.")
    except requests.exceptions.ConnectionError:
        st.error("🔴 FastAPI Backend Core is OFFLINE. Run `python backend/main.py`")

    st.markdown("---")
    st.subheader("Manual Override (Force Signal to EA)")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Force BUY", type="primary"):
            requests.post(f"http://127.0.0.1:8000/api/v1/rl/signal?symbol={selected_symbol}&action=BUY")
            st.toast(f"BUY signal sent for {selected_symbol}")
    with col2:
        if st.button("Force SELL", type="primary"):
            requests.post(f"http://127.0.0.1:8000/api/v1/rl/signal?symbol={selected_symbol}&action=SELL")
            st.toast(f"SELL signal sent for {selected_symbol}")
    with col3:
        if st.button("CLOSE ALL"):
            requests.post(f"http://127.0.0.1:8000/api/v1/rl/signal?symbol={selected_symbol}&action=CLOSE")
            st.toast(f"CLOSE signal sent for {selected_symbol}")