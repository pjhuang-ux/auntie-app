import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import twstock
import altair as alt

# --- 設定網頁 ---
st.set_page_config(page_title="阿姨的樂退寶 (專業版)", page_icon="👵", layout="wide")

# ========================================================
# 🔧 專業計算工具區 (勞保/勞退核心公式)
# ========================================================

# 1. 勞保投保薪資分級表 (2024年部分級距，用於自動校正)
INSURANCE_BRACKETS = [
    27470, 28800, 30300, 31800, 33300, 34800, 36300, 
    38200, 40100, 42000, 43900, 45800
]

def get_insured_salary(real_salary):
    """將實際薪資轉換為勞保投保薪資"""
    if real_salary >= 45800: return 45800
    if real_salary < 27470: return 27470
    for bracket in INSURANCE_BRACKETS:
        if bracket >= real_salary: return bracket
    return 45800

def calculate_labor_insurance(salary, years, age, retire_age):
    """
    計算勞保老年年金 (雙軌制 + 展延/減給)
    法定退休年齡設定為 65 歲 (作為基準)
    """
    # 1. 計算年金係數 (提早或延後)
    # 每一歲增減 4%，最多 20% (5年)
    age_diff = retire_age - 65
    # 限制範圍在 -5 到 +5 年之間
    age_diff = max(-5, min(5, age_diff))
    adjustment_factor = 1 + (age_diff * 0.04)
    
    # 2. 雙軌制公式
    # A式: (平均月投保薪資 x 年資 x 0.775% + 3000元) x 係數
    formula_a = (salary * years * 0.00775 + 3000) * adjustment_factor
    
    # B式: (平均月投保薪資 x 年資 x 1.55%) x 係數
    formula_b = (salary * years * 0.0155) * adjustment_factor
    
    # 3. 擇優發給
    best_pension = max(formula_a, formula_b)
    
    return best_pension, adjustment_factor

def calculate_labor_pension(current_balance, salary, years_left, self_rate, roi, duration_years):
    """
    計算勞退 (勞退新制) - 包含雇主6% + 自提 + 複利
    """
    monthly_rate = roi / 100 / 12
    months_left = years_left * 12
    
    # 1. 現有資金的複利成長 (FV)
    fv_balance = current_balance * ((1 + monthly_rate) ** months_left)
    
    # 2. 未來投入資金的複利成長 (年金終值)
    monthly_contribution = salary * (0.06 + self_rate/100)
    if monthly_rate > 0:
        fv_contribution = monthly_contribution * (((1 + monthly_rate) ** months_left - 1) / monthly_rate)
    else:
        fv_contribution = monthly_contribution * months_left
        
    total_fund = fv_balance + fv_contribution
    
    # 3. 年金化 (PMT) - 算出退休後每月可領多少
    # 假設退休後資金繼續以同樣報酬率滾動
    months_duration = duration_years * 12
    if monthly_rate > 0:
        monthly_payment = total_fund * (monthly_rate * (1 + monthly_rate)**months_duration) / ((1 + monthly_rate)**months_duration - 1)
    else:
        monthly_payment = total_fund / months_duration
        
    return monthly_payment, total_fund

# ========================================================
# 🎛️ 側邊欄：輸入區
# ========================================================
with st.sidebar:
    st.header("👵 參數設定")
    
    # 基本資料
    name = st.text_input("暱稱", "宜蘭阿姨")
    age = st.number_input("目前年齡", 25, 64, 50)
    retire_age = st.number_input("預計退休年齡", 60, 75, 65, help="勞保法定是65歲，提早領會變少喔")
    life_expectancy = st.number_input("預計活到", 75, 100, 85)
    
    st.divider()
    
    # 薪資與勞保
    st.markdown("#### 💰 薪資與勞保")
    real_salary = st.number_input("實際月薪", 27470, 200000, 42000, step=1000)
    insured_salary = get_insured_salary(real_salary)
    st.caption(f"勞保投保薪資：${insured_salary:,}")
    work_years = st.number_input("已累積勞保年資", 0, 40, 20)
    
    # 勞退設定 (修正重點)
    st.markdown("#### 🏦 勞退設定")
    lao_tui_saved = st.number_input("勞退專戶累積金額", 0, 10000000, 600000, step=10000)
    self_contribution_rate = st.slider("勞退自提比例 (%)", 0, 6, 0, help="妳自己有沒有額外提撥？最多6%")
    lao_tui_roi = st.slider("勞退基金預期年報酬 (%)", 1.0, 6.0, 3.0, 0.5, help="勞保局保證約1.5%，但長期平均約3~4%，建議設3%")
    
    st.divider()
    
    # 其他資產
    current_savings = st.number_input("其他退休存款", 0, 50000000, 1000000, step=50000)
    
    # 環境參數
    st.markdown("#### 🌍 環境與風險")
    inflation_rate = st.slider("預估通膨率", 0.0, 5.0, 2.0, 0.1, format="%f%%")
    lao_bao_discount = st.slider("勞保破產風險打折", 50, 100, 100, 5, format="%d%%", help="設100%表示相信政府全額給付") / 100
    
    city = st.selectbox("居住地", ["宜蘭縣", "台北市", "新北市", "桃園/新竹", "台中市", "台南/高雄", "其他"], index=0)
    life_style = st.select_slider("生活等級", ["基礎", "舒適", "富裕"], value="舒適")

# ========================================================
# 🧠 後端計算
# ========================================================

# 1. 支出計算 (通膨後)
city_costs = {
    "台北市": [32000, 55000, 90000], "新北市": [26000, 42000, 70000],
    "桃園/新竹": [25000, 40000, 65000], "台中市": [24000, 38000, 60000],
    "台南/高雄": [23000, 35000, 55000], "宜蘭縣": [22000, 32000, 50000],
    "其他": [20000, 30000, 50000]
}
style_idx = 0 if life_style == "基礎" else (1 if life_style == "舒適" else 2)
base_monthly_need = city_costs[city][style_idx]

years_to_retire = max(0, retire_age - age)
retirement_duration = max(1, life_expectancy - retire_age)
future_monthly_need = base_monthly_need * ((1 + inflation_rate/100) ** years_to_retire)

# 2. 勞保計算 (雙軌制 + 減給/展延)
total_years = work_years + years_to_retire
lao_bao_monthly_raw, lb_factor = calculate_labor_insurance(insured_salary, total_years, age, retire_age)
lao_bao_monthly = lao_bao_monthly_raw * lao_bao_discount # 乘上使用者的打折預期

# 3. 勞退計算 (含自提 + 複利)
lao_tui_monthly, total_lao_tui_fund = calculate_labor_pension(
    lao_tui_saved, insured_salary, years_to_retire, 
    self_contribution_rate, lao_tui_roi, retirement_duration
)

govt_monthly = lao_bao_monthly + lao_tui_monthly
monthly_gap = max(0, future_monthly_need - govt_monthly)
total_gap = monthly_gap * 12 * retirement_duration

# 4. 存款缺口與投資目標
future_savings = current_savings * ((1 + 0.05) ** years_to_retire) # 假設存款以5%成長
real_gap = max(0, total_gap - future_savings)

if years_to_retire > 0 and real_gap > 0:
    monthly_invest_target = real_gap * (0.06/12) / ((1 + 0.06/12)**(years_to_retire*12) - 1)
else:
    monthly_invest_target = 0

# ========================================================
# 🖥️ 前端顯示
# ========================================================
st.title(f"👋 早安，{name}！")
tab1, tab2, tab3 = st.tabs(["🌳 財富花園", "🧮 退休精算", "🤖 AI 投資與診斷"])

# === 分頁 1 ===
with tab1:
    st.subheader("資產累積進度")
    total_need = future_monthly_need * 12 * retirement_duration
    have = (govt_monthly * 12 * retirement_duration) + future_savings
    progress = min(100, int((have / total_need) * 100))
    
    c1, c2 = st.columns([1, 2])
    with c1:
        if progress < 30: st.markdown("# 🌱"); st.caption("剛起步")
        elif progress < 70: st.markdown("# 🌳"); st.caption("成長中")
        else: st.markdown("# 🍎"); st.caption("快達標了")
    with c2:
        st.write(f"目前進度：**{progress}%**")
        if real_gap > 0:
            st.warning(f"💡 為了填補缺口，建議每月再投資 **${int(monthly_invest_target):,}**")
        else:
            st.success("🎉 資金充裕，可以安心退休！")

# === 分頁 2 (顯示詳細計算邏輯) ===
with tab2:
    st.subheader("🧮 退休金來源分析")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("退休後每月開銷", f"${int(future_monthly_need):,}", f"含通膨 {inflation_rate}%")
    col2.metric("政府每月給付", f"${int(govt_monthly):,}", f"涵蓋率 {int(govt_monthly/future_monthly_need*100)}%")
    col3.metric("每月缺口", f"${int(monthly_gap):,}", delta_color="inverse")
    
    st.divider()
    
    # 詳細計算過程 (回應使用者疑問)
    with st.expander("👀 點我查看：政府的錢是怎麼算出來的？"):
        st.markdown("#### ① 勞保老年年金 (雙軌擇優)")
        st.write(f"- **投保薪資**：${insured_salary:,}")
        st.write(f"- **總年資**：{total_years} 年")
        st.write(f"- **退休年齡係數**：{int((lb_factor-1)*100)}% ({retire_age}歲退休)")
        st.write(f"- **計算結果**：${int(lao_bao_monthly_raw):,}/月 (若設定打折後為 ${int(lao_bao_monthly):,})")
        st.caption("公式採勞保局 A式/B式 擇優計算，並納入展延/減給年金規定。")
        
        st.divider()
        
        st.markdown("#### ② 勞工退休金 (勞退新制)")
        st.write(f"- **雇主提撥 + 自提**：{6 + self_contribution_rate}%")
        st.write(f"- **預估基金報酬率**：{lao_tui_roi}% (複利滾存)")
        st.write(f"- **退休時累積總額**：約 ${int(total_lao_tui_fund):,}")
        st.write(f"- **月領金額 (年金化)**：${int(lao_tui_monthly):,}/月 (分 {retirement_duration} 年領)")

# === 分頁 3 (修復建議價 + 詳細原因) ===
with tab3:
    st.subheader("🤖 AI 個股診斷室")
    
    # 投資目標提示
    if monthly_invest_target > 0:
        st.info(f"🎯 本月目標：請投入 **${int(monthly_invest_target):,}** 進入市場，填補缺口！")

    # 搜尋區
    c_search, c_btn = st.columns([3, 1])
    with c_search:
        code_input = st.text_input("輸入股票代號 (如 2330, 00878)", "")
    with c_btn:
        st.write(""); st.write("")
        do_analyze = st.button("AI 診斷", use_container_width=True)

    if do_analyze and code_input:
        code = code_input.strip()
        # 中文名稱
        ch_name = code
        if code in twstock.codes:
            ch_name = twstock.codes[code].name

        try:
            with st.spinner(f"AI 正在分析 {ch_name} ..."):
                # 抓資料
                ticker_key = f"{code}.TW"
                stock = yf.Ticker(ticker_key)
                hist = stock.history(period="2y")
                if hist.empty:
                    ticker_key = f"{code}.TWO"
                    stock = yf.Ticker(ticker_key)
                    hist = stock.history(period="2y")
                
                if hist.empty:
                    st.error("❌ 查無資料")
                else:
                    # 數據提取
                    price = hist['Close'].iloc[-1]
                    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
                    ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
                    ma240 = hist['Close'].rolling(window=240).mean().iloc[-1]
                    
                    # 🎯 建議買入價 (修復 Feature ②)
                    buy_target = ma60 * 0.95
                    
                    # 顯示看板
                    st.markdown(f"### 📊 {ch_name} ({code})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("目前股價", f"${price:.2f}")
                    # 這裡放回建議價
                    m2.metric("🎯 建議買入價", f"${buy_target:.2f}", "季線95折")
                    m3.metric("季線 (60MA)", f"${ma60:.2f}")
                    m4.metric("年線 (240MA)", f"${ma240:.2f}")

                    # --- AI 深度解析 (修復 Feature ③) ---
                    st.write("#### 📋 AI 健檢報告書")
                    
                    reasons = []
                    score = 60 # 基礎分
                    
                    # 1. 趨勢檢查
                    if price > ma240:
                        reasons.append("✅ **長線多頭**：股價在年線之上，長期趨勢向上 (+20分)")
                        score += 20
                    else:
                        reasons.append("❌ **長線空頭**：股價跌破年線，趨勢轉弱，這是最大扣分項 (-30分)")
                        score -= 30
                        
                    if price > ma60:
                        reasons.append("✅ **中期強勢**：股價在季線之上 (+10分)")
                        score += 10
                    else:
                        reasons.append("⚠️ **中期整理**：股價跌破季線，可能在休息整理 (-10分)")
                        score -= 10
                        
                    # 2. 乖離率檢查 (是不是漲太多)
                    bias = (price - ma60) / ma60 * 100
                    if bias > 15:
                        reasons.append("⚠️ **過熱警報**：短線漲太多了(乖離率高)，現在買容易套牢，建議等回檔 (-20分)")
                        score -= 20
                    elif bias < -5:
                        reasons.append("✅ **價格便宜**：目前股價低於季線 5% 以上，是撿便宜好機會 (+20分)")
                        score += 20
                        
                    # 3. 結論
                    final_decision = ""
                    color = "orange"
                    if score >= 80:
                        final_decision = "🟢 強力推薦 (買進)"
                        color = "green"
                    elif score >= 60:
                        final_decision = "🟢 分批佈局 (持有)"
                        color = "#8BC34A" # 淺綠
                    elif score >= 40:
                        final_decision = "🟡 暫時觀望 (等待)"
                        color = "orange"
                    else:
                        final_decision = "🔴 不推薦 (賣出/避開)"
                        color = "red"
                        
                    # 顯示結果卡片
                    st.markdown(f"""
                    <div style="padding:15px; border-left:5px solid {color}; background-color:#f9f9f9;">
                        <h3>{final_decision} (評分: {score})</h3>
                        <p><b>分析原因：</b></p>
                        <ul>
                            {''.join([f'<li>{r}</li>' for r in reasons])}
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 畫圖
                    df_chart = pd.DataFrame({'Price': hist['Close'], 'MA240': hist['Close'].rolling(window=240).mean()}).tail(250)
                    st.line_chart(df_chart, color=["#888888", "#ff0000"])
                    
        except Exception as e:
            st.error(f"分析錯誤: {e}")
