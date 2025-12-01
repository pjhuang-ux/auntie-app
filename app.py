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

# === 分頁 3: AI 選股 (穩健回歸版) ===
with tab3:
    st.subheader("🤖 AI 投資管家")
    st.caption("數據來源：Yahoo Finance (延遲報價)")
    
    stock_input = st.text_input("請輸入台股代號", "2330", help="輸入數字即可")
    
    if st.button("AI 診斷"):
        ticker_code = stock_input.strip()
        if not ticker_code.endswith(".TW"):
            ticker_code = ticker_code + ".TW"

        try:
            with st.spinner(f"正在分析 {ticker_code}..."):
                # 1. 使用 yfinance 抓取歷史資料 (半年)
                # 這樣做一次連線就能拿到「現在股價」跟「均線數據」，效率最高
                stock = yf.Ticker(ticker_code)
                hist = stock.history(period="6mo")
                
                if hist.empty:
                    st.error("❌ 找不到資料，請確認代號是否正確 (或 Yahoo 暫時忙碌)。")
                else:
                    # 2. 提取數據
                    current_price = hist['Close'].iloc[-1] # 最後一筆就是最近的收盤價
                    prev_close = hist['Close'].iloc[-2]    # 昨天的收盤價
                    change = current_price - prev_close
                    
                    # 3. 計算均線 (阿姨的安全指標)
                    ma60 = hist['Close'].rolling(window=60).mean().iloc[-1] # 季線 (60日)
                    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1] # 月線 (20日)
                    
                    # 4. 計算「便宜價」
                    # 定義：如果比季線便宜 5%，就是特價
                    safe_price = ma60 * 0.95
                    
                    # 5. 顯示結果
                    st.divider()
                    
                    # 第一排：股價卡片
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("參考股價", f"${current_price:.2f}", f"{change:.2f}", delta_color="inverse")
                    with col2:
                        st.metric("季線 (平均成本)", f"${ma60:.2f}", "生命線")
                    with col3:
                        st.metric("🎯 建議買入價", f"${safe_price:.2f}", "季線 95 折")
                    
                    # 第二排：AI 建議
                    st.write("### 🤖 投資建議書")
                    
                    if current_price < safe_price:
                        # 這是您最想要的功能：判斷是否便宜
                        st.markdown(f"""
                        <div style="padding:15px; background:#e8f5e9; border-left:5px solid green;">
                            <h3>🟢 強力買進 (特價中)</h3>
                            <p>現在價格 <b>${current_price:.2f}</b> 低於建議價 <b>${safe_price:.2f}</b>！</p>
                            <p>股價已經跌破季線支撐，是難得的撿便宜機會。</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    elif current_price < ma60:
                        st.markdown(f"""
                        <div style="padding:15px; background:#f1f8e9; border-left:5px solid #8bc34a;">
                            <h3>🟢 分批買進 (合理區)</h3>
                            <p>現在價格在季線 <b>${ma60:.2f}</b> 附近，成本合理。</p>
                            <p>適合阿姨定期定額慢慢買。</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    elif current_price > ma20:
                        st.markdown(f"""
                        <div style="padding:15px; background:#ffebee; border-left:5px solid red;">
                            <h3>🔴 暫不追高 (過熱區)</h3>
                            <p>股價現在很強勢 (<b>${current_price:.2f}</b>)，但也比較貴。</p>
                            <p>建議等它回檔休息，接近 <b>${ma60:.2f}</b> 再考慮進場。</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    else:
                        st.markdown("""
                        <div style="padding:15px; background:#fffde7; border-left:5px solid orange;">
                            <h3>🟡 觀望中 (盤整)</h3>
                            <p>股價不上不下，可以再多觀察幾天。</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 畫圖
                    st.line_chart(hist['Close'])
                    
        except Exception as e:
            st.error(f"分析時發生錯誤: {e}")
