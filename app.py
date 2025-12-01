import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import twstock
import altair as alt # 用來畫更漂亮的圖，解決顏色報錯問題

# --- 設定網頁 ---
st.set_page_config(page_title="阿姨的樂退寶", page_icon="👵", layout="wide")

# --- 側邊欄：使用者設定 ---
with st.sidebar:
    st.header("👵 阿姨的個人檔案")
    name = st.text_input("暱稱", "宜蘭阿姨")
    st.divider()
    st.info("💡 這裡的資料會影響所有試算結果喔！")

# --- 主標題 ---
st.title(f"👋 早安，{name}！")

# 建立三個主要功能分頁
tab1, tab2, tab3 = st.tabs(["🌳 財富花園 (成長)", "🧮 缺口試算 (現實)", "🤖 AI 投資管家 (行動)"])

# ========================================================
# 分頁 1: 財富花園 (視覺化成長)
# ========================================================
with tab1:
    st.subheader("我的存錢桶長大計畫")
    col_tree, col_msg = st.columns([1, 2])
    
    # 模擬達成率 (這裡之後可以連動分頁2的缺口計算)
    progress = st.slider("目前退休金準備進度 (%)", 0, 100, 30)
    
    with col_tree:
        if progress < 20:
            st.markdown("# 🌱")
            st.caption("剛播種，要耐心灌溉")
        elif progress < 50:
            st.markdown("# 🌿")
            st.caption("長出葉子了，不能停！")
        elif progress < 80:
            st.markdown("# 🌳")
            st.caption("大樹成蔭，快達標了")
        else:
            st.markdown("# 🍎🌳🍎")
            st.caption("財富自由，準備採收！")
            if progress == 100:
                st.balloons()
    
    with col_msg:
        st.write("### 複利的威力")
        st.write("假設妳每個月多存 5,000 元，投入年化報酬率 6% 的標的...")
        
        # 畫一個簡單的複利成長圖
        years = np.arange(1, 21)
        # 本金投入
        principal = years * 5000 * 12
        # 複利成長
        compound = [5000 * 12 * (((1 + 0.06)**y - 1) / 0.06) for y in years]
        
        chart_data = pd.DataFrame({
            "年分": years,
            "只存銀行 (本金)": principal,
            "樂退投資 (複利)": compound
        })
        
        st.line_chart(chart_data, x="年分", color=["#aaaaaa", "#ff0000"])
        st.caption("紅色線是投資的效果，灰色線是死存錢。時間越久差越多！")

# ========================================================
# 分頁 2: 缺口試算 (包含宜蘭、通膨、壽命、勞保打折)
# ========================================================
with tab2:
    st.subheader("🧮 退休金缺口精算機 (含通膨與風險)")
    
    col_input, col_result = st.columns([1, 1.2])

    # --- 左側：輸入資料 ---
    with col_input:
        st.markdown("#### 1️⃣ 生涯規劃")
        age = st.number_input("目前年齡", 25, 70, 50)
        retire_age = st.number_input("預計退休年齡", 55, 75, 65)
        life_expectancy = st.number_input("預計活到幾歲 (長壽風險)", 70, 100, 85, help="這決定退休金要花多少年")
        
        st.markdown("#### 2️⃣ 財務現況")
        salary = st.number_input("目前月薪 (投保薪資)", 27470, 150000, 42000, step=1000)
        work_years = st.number_input("已累積勞保年資", 0, 40, 20)
        lao_tui_saved = st.number_input("勞退帳戶目前金額", 0, 10000000, 600000, step=10000)

        st.markdown("#### 3️⃣ 風險參數設定 (關鍵！)")
        inflation_rate = st.slider("預估每年通膨率", 0.0, 5.0, 2.0, 0.1, format="%f%%", help="建議設 2%，錢會變薄")
        lao_bao_discount = st.slider("勞保年金打折預估", 50, 100, 80, 5, help="預設 80% 代表政府改革後可能少領 2 成") / 100

        st.markdown("#### 4️⃣ 生活品質")
        # 新增宜蘭選項
        city_cost_db = {
            "台北市": [32000, 55000, 90000],
            "新北市": [26000, 42000, 70000],
            "桃園/新竹": [25000, 40000, 65000],
            "台中市": [24000, 38000, 60000],
            "台南/高雄": [23000, 35000, 55000],
            "宜蘭縣": [22000, 32000, 50000], # 宜蘭行情
            "其他縣市": [20000, 30000, 50000]
        }
        city = st.selectbox("居住地點", list(city_cost_db.keys()), index=5) # 預設選到宜蘭
        life_style = st.select_slider("退休生活等級", options=["基礎(生存)", "舒適(生活)", "富裕(享受)"], value="舒適(生活)")

    # --- 後端計算 ---
    # 1. 計算退休後的生活費 (考慮通膨)
    style_idx = 0 if "基礎" in life_style else (1 if "舒適" in life_style else 2)
    current_cost = city_cost_db[city][style_idx]
    
    years_to_retire = retire_age - age
    retirement_duration = life_expectancy - retire_age # 退休後要活幾年
    
    # 未來每個月需要的錢 (複利公式)
    future_monthly_cost = current_cost * ((1 + inflation_rate/100) ** years_to_retire)

    # 2. 計算政府給的錢
    # 勞保：年資 x 薪資 x 1.55% x 打折係數
    total_work_years = work_years + years_to_retire
    lao_bao_monthly = min(salary, 45800) * total_work_years * 0.0155 * lao_bao_discount
    
    # 勞退：(已存 + 未來存) / 退休餘命月數
    future_save = salary * 0.06 * 12 * years_to_retire
    total_lao_tui = lao_tui_saved + future_save
    lao_tui_monthly = total_lao_tui / (retirement_duration * 12)

    govt_total = lao_bao_monthly + lao_tui_monthly
    
    # 3. 缺口
    gap = future_monthly_cost - govt_total

    # --- 右側：結果顯示 ---
    with col_result:
        st.write("### 📊 殘酷大對決")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.metric("退休時每月開銷 (含通膨)", f"${int(future_monthly_cost):,}", f"現在幣值: ${current_cost:,}")
        with col_c2:
            st.metric("政府給付預估 (含打折)", f"${int(govt_total):,}", f"勞保打 {int(lao_bao_discount*100)} 折")

        st.divider()
        
        if gap > 0:
            st.error(f"😱 每月缺口：${int(gap):,}")
            total_gap_asset = gap * 12 * retirement_duration
            st.markdown(f"""
            阿姨，因為通膨和勞保縮水，
            妳需要準備 **${int(total_gap_asset/10000):,} 萬元** 的老本才夠花 **{retirement_duration}** 年！
            """)
        else:
            st.success("🎉 恭喜！妳的退休金非常充裕！")

        # --- 解決圖表報錯，改用 Altair ---
        st.write("#### 資金來源組成")
        chart_data = pd.DataFrame({
            '來源': ['① 勞保年金', '② 勞退月領', '③ 資金缺口'],
            '金額': [lao_bao_monthly, lao_tui_monthly, max(0, gap)],
            'Color': ['#4CAF50', '#8BC34A', '#FF5252'] # 指定顏色
        })
        
        # 使用 Altair 繪圖 (不會報錯)
        c = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('來源', sort=None),
            y='金額',
            color=alt.Color('來源', scale=alt.Scale(
                domain=['① 勞保年金', '② 勞退月領', '③ 資金缺口'],
                range=['#4CAF50', '#8BC34A', '#FF5252']
            )),
            tooltip=['來源', '金額']
        )
        st.altair_chart(c, use_container_width=True)

# ========================================================
# 分頁 3: AI 投資管家 (含推薦與資產配置)
# ========================================================
with tab3:
    st.subheader("🤖 AI 投資管家")
    
    # 搜尋框
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        stock_input = st.text_input("輸入代號搜尋", "00878", help="例如 2330, 0050, 6217")
    with col_s2:
        st.write("") 
        st.write("") 
        btn = st.button("AI 診斷", use_container_width=True)

    if btn:
        code = stock_input.strip()
        # 取得中文名稱
        if code in twstock.codes:
            stock_info = twstock.codes[code]
            ch_name = stock_info.name
        else:
            ch_name = code

        try:
            with st.spinner(f"正在分析 {ch_name} ..."):
                # 雙軌偵測
                ticker = f"{code}.TW"
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2y")
                
                if hist.empty:
                    ticker = f"{code}.TWO"
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="2y")

                if hist.empty:
                    st.error("❌ 找不到資料。")
                else:
                    # 數據提取
                    current_price = hist['Close'].iloc[-1]
                    ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
                    ma240 = hist['Close'].rolling(window=240).mean().iloc[-1]
                    safe_price = ma60 * 0.95
                    
                    # 顯示數據
                    st.markdown(f"### 📊 {ch_name} ({code})")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("股價", f"${current_price:.2f}")
                    c2.metric("建議價", f"${safe_price:.2f}")
                    c3.metric("季線", f"${ma60:.2f}")
                    c4.metric("年線", f"${ma240:.2f}")

                    # AI 判斷
                    st.write("#### 🤖 投資建議")
                    score = 0
                    if current_price < safe_price and current_price > ma240:
                        score = 90
                        st.success("🟢 **強力買進** (便宜且多頭)")
                    elif current_price < ma60:
                        score = 75
                        st.success("🟢 **分批買進** (價格合理)")
                    elif current_price < ma240:
                        score = 40
                        st.error("🔴 **勿接刀** (已跌破年線)")
                    else:
                        score = 60
                        st.warning("🟡 **觀望** (股價偏高)")
                        
                    # 圖表
                    chart_df = pd.DataFrame({'Price': hist['Close'], 'MA240': hist['Close'].rolling(window=240).mean()}).tail(250)
                    st.line_chart(chart_df, color=["#888888", "#ff0000"])

                    # === 新增功能：資金分配與推薦 (Requirement ⑦) ===
                    st.divider()
                    st.subheader("💰 資金分配建議")
                    
                    # 依據分數給建議
                    if score >= 75:
                        st.info(f"💡 這檔股票評分 **{score}分**，體質不錯！")
                        st.markdown("""
                        **建議本月閒錢分配：**
                        *   **40% 買這檔股票** (把握機會)
                        *   **60% 買 ETF** (如 00878, 0050) 保持穩健
                        """)
                    elif score <= 50:
                        st.warning(f"💡 這檔股票評分 **{score}分**，風險高！")
                        st.markdown("""
                        **建議本月分配：**
                        *   ❌ **不要買這檔**
                        *   **100% 存入核心 ETF** 或保留現金等待
                        """)
                    else:
                        st.markdown("""
                        **建議分配：**
                        *   **20% 少量試單**
                        *   **80% 買 ETF**
                        """)

                    # 投資風格推薦
                    with st.expander("📌 查看適合我的長期投資清單"):
                        st.write("根據阿姨穩健退休的需求，我們推薦：")
                        st.table(pd.DataFrame({
                            "代號": ["00878", "0056", "0050", "2412"],
                            "名稱": ["國泰永續高股息", "元大高股息", "元大台灣50", "中華電"],
                            "類型": ["領息首選", "領息老牌", "跟著大盤漲", "防禦型個股"]
                        }))
                    
                    st.caption("🔔 每月健檢：建議每月 1 號回來這裡，看看手中持股有沒有跌破年線喔！")

        except Exception as e:
            st.error(f"分析錯誤: {e}")
