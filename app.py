import streamlit as st
import pandas as pd
import numpy as np
import time
import yfinance as yf
import twstock 

# --- 設定網頁標題與圖示 ---
st.set_page_config(page_title="阿姨的樂退寶", page_icon="👵")

# === 新增：抓資料專用的函數 (含快取與偽裝) ===
@st.cache_data(ttl=3600) # 設定快取 1 小時 (3600秒)，不要一直去煩 Yahoo
# === 修正版：抓資料函數 (移除 Session，保留快取) ===
@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    # 直接呼叫，不加任何偽裝，讓 yfinance 內部自己處理
    stock = yf.Ticker(ticker)
    
    # 這裡加一個小小的延遲，避免瞬間請求太快被擋
    time.sleep(0.1)
    
    # 抓取歷史資料
    hist = stock.history(period="6mo")
    
    # 抓取基本資料 (容錯處理)
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


# === 分頁 3: AI 選股 (防接刀安全版) ===
with tab3:
    st.subheader("🤖 AI 投資管家 (含防接刀機制)")
    st.caption("策略：季線撿便宜 + 年線當保險")
    
    stock_input = st.text_input("請輸入台股代號", "2330", help="輸入數字即可")
    
    if st.button("AI 診斷"):
        ticker_code = stock_input.strip()
        if not ticker_code.endswith(".TW"):
            ticker_code = ticker_code + ".TW"

        try:
            with st.spinner(f"正在深入分析 {ticker_code} 的長線趨勢..."):
                # 1. 改成抓「一年」資料，這樣才算得出年線 (240MA)
                stock = yf.Ticker(ticker_code)
                hist = stock.history(period="1y")
                
                if hist.empty:
                    st.error("❌ 找不到資料，請確認代號。")
                else:
                    # 2. 提取現價
                    current_price = hist['Close'].iloc[-1]
                    
                    # 3. 計算關鍵均線
                    ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]  # 季線 (中期保護)
                    ma240 = hist['Close'].rolling(window=240).mean().iloc[-1] # 年線 (長期生命線)
                    
                    # 4. 定義「便宜價」 (季線 95 折)
                    safe_price = ma60 * 0.95
                    
                    # 5. 顯示數據看板
                    st.divider()
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("目前股價", f"${current_price:.2f}")
                    with col2:
                        st.metric("季線 (60MA)", f"${ma60:.2f}")
                    with col3:
                        # 這裡多顯示一個年線給阿姨參考
                        st.metric("年線 (240MA)", f"${ma240:.2f}", "跌破很危險")

                    # 6. AI 邏輯核心 (加入防接刀判斷)
                    st.write("### 🤖 深度分析報告")

                    # === 判斷邏輯開始 ===
                    
                    # 狀況一：股價真的很便宜 (低於建議價)
                    if current_price < safe_price:
                        # 【關鍵修正】這裡加入第二道檢查：有沒有跌破年線？
                        if current_price > ma240:
                            # 在年線之上 -> 這是「回檔」，可以買！
                            st.markdown(f"""
                            <div style="padding:15px; background:#e8f5e9; border-left:5px solid green;">
                                <h3>🟢 黃金坑：強力買進</h3>
                                <p>股價跌破季線，出現便宜價 <b>${current_price:.2f}</b>。</p>
                                <p>✅ <b>關鍵訊號：</b> 股價仍守在年線 (<b>${ma240:.2f}</b>) 之上，代表長期趨勢沒壞，這只是短期修正，是最好的進場點！</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # 跌破年線 -> 這是「崩盤」，快逃！
                            st.markdown(f"""
                            <div style="padding:15px; background:#ffebee; border-left:5px solid red;">
                                <h3>🔴 接刀警報：千萬別買！</h3>
                                <p>雖然股價看起來很便宜，但它已經<b>跌破年線 (${ma240:.2f})</b>！</p>
                                <p>⚠️ <b>危險訊號：</b> 連長期趨勢都轉弱了，這可能是公司出問題或空頭開始，股價可能會繼續跌，阿姨請忍住手，不要接刀。</p>
                            </div>
                            """, unsafe_allow_html=True)

                    # 狀況二：股價在合理區間
                    elif current_price < ma60:
                        st.markdown(f"""
                        <div style="padding:15px; background:#f1f8e9; border-left:5px solid #8bc34a;">
                            <h3>🟢 分批佈局 (合理區)</h3>
                            <p>股價在季線附近，屬於合理範圍。如果有閒錢可以買一點。</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    # 狀況三：股價太貴
                    else:
                        st.markdown(f"""
                        <div style="padding:15px; background:#fffde7; border-left:5px solid orange;">
                            <h3>🟡 暫時觀望 (偏貴)</h3>
                            <p>目前股價強勢，但成本較高，建議不要追高。</p>
                        </div>
                        """, unsafe_allow_html=True)

                    # 畫圖：把年線也畫出來讓阿姨看
                    st.write("### 股價 vs 年線 (紅色是年線)")
                    chart_data = pd.DataFrame({
                        '股價': hist['Close'],
                        '年線(240MA)': hist['Close'].rolling(window=240).mean()
                    })
                    st.line_chart(chart_data)

        except Exception as e:
            st.error(f"分析失敗: {e}")
