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


# === 分頁 3: AI 選股 (中文名 + 上市上櫃通吃版) ===
with tab3:
    st.subheader("🤖 AI 投資管家")
    st.caption("策略：季線撿便宜 + 年線當保險")
    
    # 搜尋框
    stock_input = st.text_input("請輸入台股代號", "6217", help="輸入數字即可，例如 2330 或 6217")
    
    if st.button("AI 診斷"):
        code = stock_input.strip()
        
        # --- 步驟 1: 取得中文名稱 (離線查詢，不會報錯) ---
        # 使用 twstock 的內建清單查中文名
        if code in twstock.codes:
            stock_info = twstock.codes[code]
            ch_name = stock_info.name # 例如：中探針
            market_type = stock_info.market # 例如：上市 或 上櫃
        else:
            ch_name = code # 查不到就顯示代號
            market_type = "未知"

        st.info(f"正在搜尋：{code} {ch_name} ({market_type})...")

        try:
            with st.spinner("正在連線 Yahoo Finance 分析歷史數據..."):
                # --- 步驟 2: 雙軌偵測 (上市.TW vs 上櫃.TWO) ---
                # 策略：先試試看上市 (.TW)
                ticker_key = f"{code}.TW"
                stock = yf.Ticker(ticker_key)
                hist = stock.history(period="2y")
                
                # 如果上市抓不到資料 (empty)，就改試試看上櫃 (.TWO)
                if hist.empty:
                    ticker_key = f"{code}.TWO" # 改成上櫃後綴
                    stock = yf.Ticker(ticker_key)
                    hist = stock.history(period="2y")
                
                # 如果還是空的，那就真的沒救了
                if hist.empty:
                    st.error(f"❌ 找不到 {code} 的資料。")
                    st.caption("可能原因：1.代號錯誤 2.剛上市不滿一年 3.Yahoo 資料庫暫時缺失")
                else:
                    # --- 步驟 3: 數據分析 (跟之前一樣) ---
                    # 提取現價
                    current_price = hist['Close'].iloc[-1]
                    
                    # 計算關鍵均線
                    ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]   # 季線
                    ma240 = hist['Close'].rolling(window=240).mean().iloc[-1] # 年線
                    
                    # 定義「便宜價」
                    safe_price = ma60 * 0.95
                    
                    # === 介面優化區 ===
                    st.divider()
                    
                    # 標題：現在顯示中文了！
                    st.markdown(f"## 📊 {ch_name} ({code})")
                    st.caption(f"市場別：{market_type} | 資料來源：Yahoo Finance")
                    
                    # 數據看板
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("目前股價", f"${current_price:.2f}")
                    with col2:
                        st.metric("🎯 建議買入價", f"${safe_price:.2f}", "季線95折")
                    with col3:
                        st.metric("季線 (60MA)", f"${ma60:.2f}")
                    with col4:
                        st.metric("年線 (240MA)", f"${ma240:.2f}")

                    # === AI 判斷邏輯 ===
                    st.write("### 🤖 AI 診斷報告")

                    # 狀況一：出現便宜價
                    if current_price < safe_price:
                        if current_price > ma240:
                            st.success(f"🟢 黃金坑：強力買進 ({ch_name} 特價中)")
                            st.info(f"股價 ${current_price:.2f} 低於建議價，且守住年線，長線看好！")
                        else:
                            st.error(f"🔴 接刀警報：{ch_name} 已跌破年線！")
                            st.warning(f"雖然便宜，但長期趨勢轉空 (跌破 ${ma240:.2f})，建議避開。")

                    # 狀況二：合理區間
                    elif current_price < ma60:
                        st.success("🟢 合理區間：分批買")
                        st.info("股價在季線附近，成本合理。")
                        
                    # 狀況三：太貴
                    else:
                        st.warning("🟡 過熱區間：觀望")
                        st.info("目前股價較高，建議等待回檔。")

                    # === 圖表區 ===
                    st.write(f"### 📈 {ch_name} 股價 vs 年線走勢")
                    
                    chart_data = pd.DataFrame({
                        '股價': hist['Close'],
                        '年線(240MA)': hist['Close'].rolling(window=240).mean()
                    }).tail(250) 
                    
                    st.line_chart(chart_data, color=["#888888", "#FF0000"])
                    st.caption("灰色線：每日股價 / 紅色線：年線 (生命線)")

        except Exception as e:
            st.error("分析時發生錯誤: " + str(e))
