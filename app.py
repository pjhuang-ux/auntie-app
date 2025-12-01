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

# === 分頁 2: 缺口試算 (專業精算版) ===
with tab2:
    st.subheader("🧮 退休金缺口精算機")
    st.caption("依據「居住地消費水準」與「勞保/勞退公式」推算")

    # --- 1. 資料輸入區 (左邊填資料，右邊看結果) ---
    col_input, col_result = st.columns([1, 1.2])

    with col_input:
        st.markdown("#### 1️⃣ 妳的基本資料")
        age = st.number_input("目前年齡", 30, 64, 50)
        retire_age = st.number_input("預計退休年齡", 60, 75, 65)
        
        st.markdown("#### 2️⃣ 妳的工作與收入")
        salary = st.number_input("目前月薪 (投保薪資)", 27470, 150000, 45000, step=1000, help="這會影響勞保跟勞退的金額")
        work_years = st.number_input("已累積工作年資 (年)", 0, 40, 20, help="去勞保局查的年資")
        lao_tui_saved = st.number_input("勞退專戶目前累積金額", 0, 5000000, 500000, step=10000, help="雇主幫妳提撥的那6%累積了多少")

        st.markdown("#### 3️⃣ 退休生活想像")
        # 內建台灣各地區生活費資料庫 (參考主計處 + 通膨預估)
        # 格式：[基礎生存, 舒適生活, 富裕享受]
        city_cost_db = {
            "台北市": [32000, 55000, 90000],
            "新北市": [26000, 42000, 70000],
            "桃園/新竹": [25000, 40000, 65000],
            "台中市": [24000, 38000, 60000],
            "台南/高雄": [23000, 35000, 55000],
            "其他縣市": [20000, 30000, 50000]
        }
        
        city = st.selectbox("居住地點", list(city_cost_db.keys()))
        life_style = st.select_slider("想要過什麼樣的退休生活？", options=["基礎(生存)", "舒適(生活)", "富裕(享受)"], value="舒適(生活)")

    # --- 2. 後端計算核心 ---
    # A. 算出每月需要多少錢
    style_index = 0 if "基礎" in life_style else (1 if "舒適" in life_style else 2)
    monthly_need = city_cost_db[city][style_index]

    # B. 算出政府給多少錢 (勞保 + 勞退)
    # 邏輯 1: 勞保老年年金 (公式：平均月投保薪資 × 年資 × 1.55%)
    # 這裡做一個保守估計：假設目前薪資接近平均投保薪資 (最高採計 45800)
    lao_bao_cap = min(salary, 45800) 
    total_years = work_years + (retire_age - age) # 假設做到退休
    lao_bao_monthly = lao_bao_cap * total_years * 0.0155
    
    # 邏輯 2: 勞工退休金 (月領概算)
    # 假設未來每年薪資不變，雇主提撥 6%，投資報酬率保守估 2%
    # 這裡用簡易算法：(已累積 + 未來提撥) / (預期餘命 20年 * 12個月)
    future_years = retire_age - age
    future_contribution = salary * 0.06 * 12 * future_years
    total_lao_tui = lao_tui_saved + future_contribution
    lao_tui_monthly = total_lao_tui / (20 * 12) # 假設領 20 年 (65歲~85歲)

    govt_total = lao_bao_monthly + lao_tui_monthly
    
    # C. 算出缺口
    gap = monthly_need - govt_total

    # --- 3. 右側結果顯示區 ---
    with col_result:
        st.markdown("### 📊 試算結果 (月)")
        
        # 顯示天平圖表
        st.write("#### 資金天平")
        col_need, col_have = st.columns(2)
        with col_need:
            st.metric("🔴 每月支出需求", f"${monthly_need:,}", help="依據妳選的地區與生活品質推算")
        with col_have:
            st.metric("🟢 政府退休金預估", f"${int(govt_total):,}", f"涵蓋率 {int(govt_total/monthly_need*100)}%")
        
        st.divider()

        # 顯示缺口
        if gap > 0:
            st.error(f"😱 殘酷現實：每月還缺 ${int(gap):,} 元")
            st.markdown(f"""
            這表示妳退休後，除了勞保勞退，
            **每個月還要自己從存款掏出 {int(gap):,} 元** 才能過妳想要的生活。
            
            如果退休後要活 20 年，妳現在的存錢目標是：
            ### 💰 **${int(gap * 12 * 20 / 10000):,} 萬元**
            """)
        else:
            st.balloons()
            st.success(f"🎉 恭喜！妳的退休金非常充裕！")
            st.markdown(f"每個月還多出 **${int(-gap):,}** 元，可以常常出國玩了！")

        # 顯示詳細組成 (Stacked Bar)
        st.write("#### 退休金組成分析")
        df_chart = pd.DataFrame({
            "金額": [lao_bao_monthly, lao_tui_monthly, max(0, gap)],
            "來源": ["① 勞保年金", "② 勞退月領", "③ 資金缺口 (靠投資)"]
        })
        # 這裡用簡單的長條圖
        st.bar_chart(df_chart, x="來源", y="金額", color=["#4CAF50", "#8BC34A", "#FF5252"])

        # 展開詳細數據
        with st.expander("查看詳細計算數據"):
            st.write(f"**預估工作總年資：** {total_years} 年")
            st.write(f"**勞保計算：** ${lao_bao_cap} × {total_years}年 × 1.55% = ${int(lao_bao_monthly):,}/月")
            st.write(f"**勞退估算：** 總累積約 ${int(total_lao_tui):,} (分20年領) ≈ ${int(lao_tui_monthly):,}/月")
            st.caption("註：此為概算，未計入勞保破產風險與通膨，僅供規劃參考。")


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
