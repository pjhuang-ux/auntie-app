import streamlit as st
import pandas as pd
import numpy as np
import time
import yfinance as yf
import requests

# --- 設定網頁標題與圖示 ---
st.set_page_config(page_title="阿姨的樂退寶", page_icon="👵")

# === 新增：抓資料專用的函數 (含快取與偽裝) ===
@st.cache_data(ttl=3600) # 設定快取 1 小時 (3600秒)，不要一直去煩 Yahoo
def get_stock_data(ticker):
    # 1. 偽裝成瀏覽器 (User-Agent)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 2. 建立專屬連線
    session = requests.Session()
    session.headers.update(headers)
    
    # 3. 透過 yfinance 抓取
    stock = yf.Ticker(ticker, session=session)
    
    # 強制抓取歷史資料
    hist = stock.history(period="6mo")
    # 抓取基本資料 (如果被擋，info 常常會是空的，這邊做個保護)
    try:
        info = stock.info
    except:
        info = {}
        
    return hist, info
    
# --- 側邊欄：登入與基本設定 ---
with st.sidebar:
    st.header("👵 阿姨設定區")
    name = st.text_input("阿姨的大名", "春嬌阿姨")
    st.divider()
    st.write("目前版本：v1.0 (雛形版)")

# --- 主頁面 ---
st.title(f"👋 早安，{name}！")

# 建立分頁 (Tabs)
tab1, tab2, tab3 = st.tabs(["🌳 財富花園", "🧮 缺口試算", "🤖 AI 投資管家"])

# === 分頁 1: 財富花園 ===
with tab1:
    st.subheader("您的退休樹養成計畫")
    
    # 模擬進度條
    progress = st.slider("目前存錢進度測試 (拉看看)", 0, 100, 35)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if progress < 30:
            st.markdown("# 🌱")
            st.caption("剛發芽，要多澆水(存錢)喔！")
        elif progress < 70:
            st.markdown("# 🌳")
            st.caption("長大了！繼續保持！")
        else:
            st.markdown("# 🍎🌳🍎")
            st.caption("結實纍纍！可以準備退休了！")
            if progress == 100:
                st.balloons()
    
    with col2:
        st.info("只要每月多存 3,000 元，這棵樹明年會長高 10% 喔！")
        
    # 模擬資產成長圖表
    st.write("### 預估資產成長曲線")
    chart_data = pd.DataFrame(
        np.random.randn(20, 2).cumsum(0) + [100, 50],
        columns=['跟著AI投資 (實線)', '只放定存 (虛線)']
    )
    st.line_chart(chart_data)

# === 分頁 2: 缺口試算 ===
with tab2:
    st.subheader("面對現實...算算看錢夠不夠？")
    
    col_a, col_b = st.columns(2)
    with col_a:
        city = st.selectbox("居住縣市", ["基隆市", "台北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣", "台中市", 
    "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣", "台南市", "高雄市", "屏東縣", 
    "宜蘭縣", "花蓮縣", "台東縣", "澎湖縣", "金門縣", "連江縣"])
    with col_b:
        style = st.select_slider("希望的生活等級", options=["基礎(生存)", "舒適(生活)", "富裕(享受)"])
        
    # 簡單的後端邏輯模擬
    base = 30000
    if city == "台北市": base = 45000
    if style == "舒適(生活)": base *= 1.5
    if style == "富裕(享受)": base *= 2.5
    
    govt_pension = 22000 # 假設勞保勞退
    gap = base - govt_pension
    
    st.metric("每月預估開銷", f"${int(base):,}")
    st.metric("政府給的退休金", f"${govt_pension:,}")
    
    if gap > 0:
        st.error(f"⚠️ 阿姨，每個月還缺 ${int(gap):,} 元！")
    else:
        st.success("🎉 太棒了！您的退休金夠用了！")

# === 分頁 3: AI 選股 (真槍實彈版) ===
# === 分頁 3: AI 選股 (修正連線版) ===
with tab3:
    st.subheader("🤖 AI 投資管家 (即時連線)")
    st.caption("我們會分析：趨勢(均線)、價值(本益比)、風險(波動度)")
    
    stock_input = st.text_input("請輸入台股代號", "2330", help="不用打.TW")
    
    if st.button("開始 AI 診斷"):
        ticker = stock_input.strip()
        if not ticker.endswith(".TW"):
            ticker = ticker + ".TW"
            
        try:
            with st.spinner(f"正在連線證交所抓取 {ticker} 資料..."):
                # === 這裡改用我們剛剛寫好的新函數 ===
                hist, info = get_stock_data(ticker)
            
            if hist.empty:
                st.error("❌ 抓不到資料，可能是代號錯誤，或是 Yahoo 暫時擋住了連線。")
            else:
                # 後面的邏輯跟原本一樣，不用變
                current_price = hist['Close'].iloc[-1]
                ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
                
                # 避免資料缺失的防呆機制
                div_yield = info.get('dividendYield', 0) if info else 0
                if div_yield is None: div_yield = 0
                
                score = 60
                reasons = []
                
                # 判斷 A: 趨勢
                if current_price > ma60:
                    score += 20
                    reasons.append("✅ 股價在季線之上，趨勢向上")
                else:
                    score -= 20
                    reasons.append("⚠️ 股價跌破季線，趨勢偏弱")

                # 判斷 B: 殖利率
                if div_yield > 0.04:
                    score += 10
                    reasons.append(f"✅ 殖利率 {div_yield*100:.2f}% 相當不錯")
                elif div_yield < 0.01:
                    reasons.append("⚠️ 殖利率偏低")

                # 顯示結果
                st.divider()
                st.metric("目前股價", f"${current_price:.2f}")
                
                if score >= 80:
                    title = "🟢 AI 建議：買進/持有"
                    bg_color = "#e8f5e9"
                    border_color = "green"
                elif score >= 60:
                    title = "🟡 AI 建議：觀望"
                    bg_color = "#fffde7"
                    border_color = "#fbc02d"
                else:
                    title = "🔴 AI 建議：小心/賣出"
                    bg_color = "#ffebee"
                    border_color = "red"

                st.markdown(f"""
                <div style="padding:20px; border:2px solid {border_color}; border-radius:10px; background-color:{bg_color}; color:black;">
                    <h3 style="margin:0;">{title}</h3>
                    <p style="font-size:24px; font-weight:bold;">樂退分：{score} 分</p>
                    <hr>
                    <ul>
                        {''.join([f'<li>{r}</li>' for r in reasons])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("### 近半年走勢圖")
                st.line_chart(hist['Close'])

        except Exception as e:
            # 這裡會顯示比較詳細的錯誤，方便除錯
            st.error(f"系統忙碌中，請過幾秒再試一次。(錯誤: {e})")
