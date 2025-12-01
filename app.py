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

# === 分頁 3: AI 選股 (升級版：即時報價 + 建議價格) ===
with tab3:
    st.subheader("🤖 AI 投資管家")
    st.caption("結合「證交所即時報價」與「技術均線」分析")
    
    stock_input = st.text_input("請輸入台股代號", "2330", help="輸入數字即可")
    
    if st.button("AI 診斷"):
        ticker_code = stock_input.strip()
        
        # --- 階段一：抓即時股價 (使用 twstock，最穩) ---
        try:
            # 這是連線到台灣證交所，通常不會失敗
            realtime_stock = twstock.realtime.get(ticker_code)
            
            if realtime_stock['success']:
                # 抓到了！
                latest_price = float(realtime_stock['realtime']['latest_trade_price'])
                high_price = float(realtime_stock['realtime']['high'])
                low_price = float(realtime_stock['realtime']['low'])
                stock_name = realtime_stock['info']['name']
                
                st.success(f"✅ 成功連線：{ticker_code} {stock_name}")
            else:
                st.error(f"❌ 找不到代號 {ticker_code}，請確認是否輸入正確。")
                st.stop() # 停在這裡，不往下跑
                
        except Exception as e:
            st.error(f"連線證交所失敗: {e}")
            st.stop()

        # --- 階段二：抓歷史趨勢算「便宜價」 (使用 yfinance) ---
        # 為什麼要分開？因為 yfinance 算均線比較方便，但容易被擋
        # 就算這段失敗，至少上面阿姨已經看到現在幾塊錢了
        
        try:
            with st.spinner("正在計算合理價格與均線..."):
                yf_ticker = f"{ticker_code}.TW"
                stock_yf = yf.Ticker(yf_ticker)
                
                # 抓半年資料來算季線
                hist = stock_yf.history(period="6mo")
                
                if not hist.empty:
                    # 1. 計算關鍵指標
                    ma60 = hist['Close'].rolling(window=60).mean().iloc[-1] # 季線 (生命線)
                    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1] # 月線
                    
                    # 2. 定義「阿姨建議買入價」
                    # 邏輯：季線(60MA)是中長期的成本區，接近季線通常是好買點
                    target_price = ma60 
                    safe_price = ma60 * 0.95 # 如果跌破季線 5%，就是超跌便宜價
                    
                    # 3. 判斷現在貴不貴？
                    gap = (latest_price - ma60) / ma60 * 100 # 乖離率
                    
                    # --- 顯示分析結果 ---
                    st.divider()
                    
                    # 第一排：股價與建議
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("目前股價", f"${latest_price}", f"今日高低 {high_price}~{low_price}")
                    with c2:
                        st.metric("季線 (生命線)", f"${int(ma60)}", "長期支撐參考")
                    with c3:
                        # 這是您要的功能：顯示建議買點
                        st.metric("🎯 建議買入價", f"${int(safe_price)}", "季線打95折")

                    # 第二排：AI 講評
                    st.write("### 🤖 AI 投資建議書")
                    
                    if latest_price < safe_price:
                        st.markdown("""
                        <div style="padding:15px; background:#e8f5e9; border-left:5px solid green;">
                            <h3>🟢 強力買進 (超值區)</h3>
                            <p>現在股價已經<b>跌破季線支撐區</b>，是非常難得的便宜價！阿姨可以分批進場撿便宜。</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    elif latest_price < ma60:
                        st.markdown("""
                        <div style="padding:15px; background:#f1f8e9; border-left:5px solid #8bc34a;">
                            <h3>🟢 建議買進 (合理區)</h3>
                            <p>股價回到季線附近，長線來看成本合理，適合存股族慢慢買。</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    elif gap > 10:
                        st.markdown("""
                        <div style="padding:15px; background:#ffebee; border-left:5px solid red;">
                            <h3>🔴 暫停買進 (過熱區)</h3>
                            <p>現在股價漲太多了（離季線太遠），隨時可能回檔。阿姨先不要追高，<b>等到股價回到 ${int(ma60)} 左右再考慮。</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="padding:15px; background:#fffde7; border-left:5px solid orange;">
                            <h3>🟡 續抱/觀望 (盤整區)</h3>
                            <p>股價在合理範圍內波動，如果有錢閒著可以買一點，或是再等等看。</p>
                        </div>
                        """, unsafe_allow_html=True)

                    # 畫圖
                    st.line_chart(hist['Close'])
                    
                else:
                    st.warning("⚠️ 抓得到即時股價，但分析歷史趨勢時連線不穩。請過幾分鐘再試試看詳細圖表。")

        except Exception as e:
            st.warning(f"分析歷史數據時發生小錯誤 (但不影響報價): {e}")
