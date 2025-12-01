import streamlit as st
import pandas as pd
import numpy as np
import time
import yfinance as yf

# --- 設定網頁標題與圖示 ---
st.set_page_config(page_title="阿姨的樂退寶", page_icon="👵")

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
with tab3:
    st.subheader("🤖 AI 投資管家 (即時連線)")
    st.caption("我們會分析：趨勢(均線)、價值(本益比)、風險(波動度)")
    
    # 輸入框
    stock_input = st.text_input("請輸入台股代號", "2330", help="不用打.TW，直接打數字即可")
    
    if st.button("開始 AI 診斷"):
        # 1. 處理代碼格式 (自動加上 .TW)
        ticker = stock_input.strip()
        if not ticker.endswith(".TW"):
            ticker = ticker + ".TW"
            
        # 2. 抓取資料 (使用 yfinance)
        try:
            with st.spinner(f"正在連線證交所抓取 {ticker} 資料..."):
                stock = yf.Ticker(ticker)
                # 抓歷史股價 (過去半年)
                hist = stock.history(period="6mo")
                # 抓基本資料
                info = stock.info
            
            if hist.empty:
                st.error("❌ 找不到這檔股票，請檢查代號是否正確。")
            else:
                # 3. 提取關鍵數據
                current_price = hist['Close'].iloc[-1] # 最新收盤價
                ma60 = hist['Close'].rolling(window=60).mean().iloc[-1] # 季線 (60日均線)
                
                # 為了避免新股沒有本益比資料，做個防呆
                pe_ratio = info.get('trailingPE', '無資料') 
                div_yield = info.get('dividendYield', 0)
                if div_yield is None: div_yield = 0
                
                # 4. AI 簡單判斷邏輯 (可以自己修改標準)
                score = 60 # 基礎分
                reasons = [] # 評語清單
                
                # 判斷 A: 趨勢 (在季線上面嗎？)
                if current_price > ma60:
                    score += 20
                    reasons.append("✅ 股價在季線之上，趨勢向上")
                    trend_color = "red" # 台股漲是紅色
                else:
                    score -= 20
                    reasons.append("⚠️ 股價跌破季線，趨勢偏弱")
                    trend_color = "green" # 台股跌是綠色

                # 判斷 B: 殖利率 (有沒有超過 4%)
                if div_yield > 0.04:
                    score += 10
                    reasons.append(f"✅ 殖利率 {div_yield*100:.2f}% 相當不錯")
                elif div_yield < 0.01:
                    reasons.append("⚠️ 殖利率偏低 (可能是成長股)")

                # 5. 顯示結果
                st.divider()
                st.metric("目前股價", f"${current_price:.2f}", 
                          f"{(current_price - hist['Close'].iloc[-2]):.2f} (漲跌)", 
                          delta_color="inverse") # inverse 讓漲變紅色
                
                # 顯示 AI 評分卡
                if score >= 80:
                    bg_color = "#e8f5e9" # 淺綠底
                    border_color = "green"
                    title = "🟢 AI 建議：買進/持有"
                elif score >= 60:
                    bg_color = "#fffde7" # 淺黃底
                    border_color = "#fbc02d"
                    title = "🟡 AI 建議：觀望"
                else:
                    bg_color = "#ffebee" # 淺紅底
                    border_color = "red"
                    title = "🔴 AI 建議：小心/賣出"

                # 這裡用 HTML 畫出漂亮的卡片
                st.markdown(f"""
                <div style="padding:20px; border:2px solid {border_color}; border-radius:10px; background-color:{bg_color}; color:black;">
                    <h3 style="margin:0;">{title}</h3>
                    <p style="font-size:24px; font-weight:bold;">樂退分：{score} 分</p>
                    <hr>
                    <p><b>🔍 分析報告：</b></p>
                    <ul>
                        {''.join([f'<li>{r}</li>' for r in reasons])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # 畫出簡單的走勢圖
                st.write("### 近半年走勢圖")
                st.line_chart(hist['Close'])

        except Exception as e:
            st.error(f"連線發生錯誤，請稍後再試。(錯誤代碼: {e})")
