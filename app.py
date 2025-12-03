import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import twstock
import altair as alt

# --- 設定網頁 ---
st.set_page_config(page_title="阿姨的樂退寶 (最終版)", page_icon="👵", layout="wide")

# ========================================================
# 🔧 專業計算工具區
# ========================================================

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
    """計算勞保老年年金 (雙軌制 + 展延/減給)"""
    age_diff = retire_age - 65
    age_diff = max(-5, min(5, age_diff))
    adjustment_factor = 1 + (age_diff * 0.04)
    formula_a = (salary * years * 0.00775 + 3000) * adjustment_factor
    formula_b = (salary * years * 0.0155) * adjustment_factor
    return max(formula_a, formula_b), adjustment_factor

def calculate_labor_pension(current_balance, salary, years_left, self_rate, roi, duration_years):
    """計算勞退 (勞退新制) - 年金化 PMT"""
    monthly_rate = roi / 100 / 12
    months_left = years_left * 12
    
    # 退休時累積的總金額 (現有複利 + 未來投入複利)
    fv_balance = current_balance * ((1 + monthly_rate) ** months_left)
    
    monthly_contribution = salary * (0.06 + self_rate/100)
    if monthly_rate > 0:
        fv_contribution = monthly_contribution * (((1 + monthly_rate) ** months_left - 1) / monthly_rate)
    else:
        fv_contribution = monthly_contribution * months_left
        
    total_fund = fv_balance + fv_contribution
    
    # 計算月領金額 (假設分攤在 user 設定的餘命內領完)
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
    retire_age = st.number_input("預計退休年齡", 60, 75, 65)
    
    # 修正重點 ③：壽命設定
    st.markdown("#### 🎂 壽命設定")
    life_expectancy = st.number_input("預計活到幾歲", 75, 110, 84, help="台灣平均壽命約84歲，設太高會有長壽風險")
    if life_expectancy > 85:
        st.warning(f"⚠️ 妳設定活到 {life_expectancy} 歲 (高於平均)。注意：勞退金可能會在 84 歲左右用完，後面的日子完全要靠自己存！")
    
    st.divider()
    
    # 薪資與勞保
    st.markdown("#### 💰 薪資與勞保")
    real_salary = st.number_input("實際月薪", 27470, 200000, 42000, step=1000)
    insured_salary = get_insured_salary(real_salary)
    st.caption(f"自動對應投保薪資：${insured_salary:,}")
    work_years = st.number_input("已累積勞保年資", 0, 40, 20)
    
    # 勞退設定
    st.markdown("#### 🏦 勞退設定")
    lao_tui_saved = st.number_input("勞退專戶累積金額", 0, 10000000, 600000, step=10000)
    self_contribution_rate = st.slider("勞退自提比例 (%)", 0, 6, 0)
    lao_tui_roi = st.slider("勞退預期年報酬 (%)", 1.0, 6.0, 3.0, 0.5)
    
    st.divider()
    
    # 其他資產 (修正重點 ①)
    st.markdown("#### 🏦 其他存款")
    current_savings = st.number_input("目前已有退休儲蓄", 0, 50000000, 1000000, step=50000)
    st.caption("ℹ️ 此存款假設退休前以 5% 複利成長，退休後作為本金慢慢提領。")
    
    # 環境參數
    st.markdown("#### 🌍 環境與風險")
    inflation_rate = st.slider("預估通膨率", 0.0, 5.0, 2.0, 0.1, format="%f%%")
    lao_bao_discount = st.slider("勞保給付打折 (風險)", 50, 100, 100, 5, format="%d%%") / 100
    
    city = st.selectbox("居住地", ["宜蘭縣", "台北市", "新北市", "桃園/新竹", "台中市", "台南/高雄", "其他"], index=0)
    life_style = st.select_slider("生活等級", ["基礎", "舒適", "富裕"], value="舒適")

# ========================================================
# 🧠 後端計算
# ========================================================

# 1. 支出計算
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
# 通膨後的每月需求
future_monthly_need = base_monthly_need * ((1 + inflation_rate/100) ** years_to_retire)

# 2. 政府退休金
total_years = work_years + years_to_retire
lao_bao_monthly_raw, lb_factor = calculate_labor_insurance(insured_salary, total_years, age, retire_age)
lao_bao_monthly = lao_bao_monthly_raw * lao_bao_discount

lao_tui_monthly, total_lao_tui_fund = calculate_labor_pension(
    lao_tui_saved, insured_salary, years_to_retire, 
    self_contribution_rate, lao_tui_roi, retirement_duration
)

govt_monthly = lao_bao_monthly + lao_tui_monthly
monthly_gap = max(0, future_monthly_need - govt_monthly)
total_asset_gap = monthly_gap * 12 * retirement_duration # 總缺口

# 3. 存款抵扣 (修正邏輯：退休前複利，退休後視為整筆資金可用)
future_savings_val = current_savings * ((1 + 0.05) ** years_to_retire)
real_total_gap = max(0, total_asset_gap - future_savings_val)

# 4. 建議每月投入金額 (PMT)
if years_to_retire > 0 and real_total_gap > 0:
    monthly_invest_target = real_total_gap * (0.06/12) / ((1 + 0.06/12)**(years_to_retire*12) - 1)
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
    total_need_val = future_monthly_need * 12 * retirement_duration
    have_val = (govt_monthly * 12 * retirement_duration) + future_savings_val
    progress = min(100, int((have_val / total_need_val) * 100))
    
    c1, c2 = st.columns([1, 2])
    with c1:
        if progress < 30: st.markdown("# 🌱"); st.caption("剛起步")
        elif progress < 70: st.markdown("# 🌳"); st.caption("成長中")
        else: st.markdown("# 🍎"); st.caption("快達標了")
    with c2:
        st.metric("目前達成率", f"{progress}%")
        if real_total_gap > 0:
            st.warning(f"💡 建議每月再投資 **${int(monthly_invest_target):,}**，才能補足缺口！")
        else:
            st.success("🎉 資金充裕！您的存款加上政府年金，足夠過完理想的退休生活。")

# === 分頁 2 ===
with tab2:
    st.subheader("🧮 退休金來源分析")
    col1, col2, col3 = st.columns(3)
    col1.metric("退休後每月開銷", f"${int(future_monthly_need):,}", f"含通膨 {inflation_rate}%")
    col2.metric("政府每月給付", f"${int(govt_monthly):,}", f"涵蓋率 {int(govt_monthly/future_monthly_need*100)}%")
    col3.metric("每月缺口", f"${int(monthly_gap):,}", delta_color="inverse")
    
    st.divider()
    
    # 長壽風險視覺化
    if life_expectancy > 85:
        st.warning(f"⚠️ **長壽風險警示**：您設定活到 {life_expectancy} 歲，但勞退金通常依據平均餘命 (約84歲) 計算。84 歲以後的開銷，主要需靠「勞保年金 (活到老領到老)」與「個人存款」支撐。")

    with st.expander("👀 詳細數據 (勞保/勞退/存款)"):
        st.write(f"**1. 勞保年金 (終身俸)**：${int(lao_bao_monthly):,}/月")
        st.write(f"**2. 勞退月領 (帳戶制)**：${int(lao_tui_monthly):,}/月 (分 {retirement_duration} 年領)")
        st.write(f"**3. 您的存款 (退休時價值)**：${int(future_savings_val):,}")
        st.caption("註：存款假設退休前年化報酬 5%。")

# === 分頁 3 (修正重點 ②：推薦清單回歸) ===
with tab3:
    st.subheader("🤖 投資行動計畫")
    
    # 1. 投資目標 (最顯眼)
    if monthly_invest_target > 0:
        st.markdown(f"""
        <div style="padding:15px; border:2px solid #2196F3; border-radius:10px; background-color:#e3f2fd; color:black;">
            <h4>💰 本月任務：請投資 <b>${int(monthly_invest_target):,}</b> 元</h4>
            <p>只要每月投入這個金額 (目標年化 6%)，就能填補退休缺口。</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()

    # 2. 不動腦推薦清單 (Fix: 強制顯示)
    st.write("### 📋 阿姨的懶人投資清單")
    years_left = retire_age - age
    
    if years_left <= 5:
        st.success("🛡️ 您快退休了，建議以 **「保守領息」** 為主：")
        recommendations = pd.DataFrame({
            "代號": ["00878", "0056", "2412", "2892"],
            "名稱": ["國泰永續高股息", "元大高股息", "中華電", "第一金"],
            "類型": ["核心 ETF", "核心 ETF", "防禦個股", "官股金控"],
            "操作": ["定期定額", "定期定額", "低接", "存股"]
        })
    else:
        st.info(f"🚀 還有 {years_left} 年才退休，建議 **「市值成長 + 高股息」** 雙管齊下：")
        recommendations = pd.DataFrame({
            "代號": ["0050/006208", "00878", "2330", "5880"],
            "名稱": ["台灣50 (大盤)", "永續高股息", "台積電", "合庫金"],
            "類型": ["核心成長", "核心領息", "衛星成長", "穩健存股"],
            "配置建議": ["40% (主攻)", "40% (防守)", "10% (衝刺)", "10% (現金流)"]
        })
    
    st.table(recommendations)
    
    st.divider()
# === 新增功能：定期定額績效驗收 ===
    with st.expander("📝 投資成績單：我每月固定存，績效有達標嗎？"):
        st.caption("阿姨，因為妳是分批買，我們用「及格線」來檢查。輸入妳每月存多少，我幫妳算算看！")
        
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            monthly_pay = st.number_input("每月固定扣款金額 (元)", 1000, 1000000, 5000, step=1000)
        with c_p2:
            invest_duration = st.number_input("持續扣款多久了？ (月)", 1, 600, 24, step=1)
            st.caption(f"約 {invest_duration/12:.1f} 年")
        with c_p3:
            current_value = st.number_input("現在庫存總市值 (元)", 0, 10000000, 130000, step=10000, help="請看券商APP顯示的總市值")

        # 計算邏輯：定期定額的終值 (Future Value of Annuity)
        # 公式：FV = PMT * (((1 + r)^n - 1) / r)
        # 我們設定及格標準是年化 6% (月利率 0.5%)
        target_rate = 0.06 / 12
        total_cost = monthly_pay * invest_duration
        
        # 算出「如果這筆錢有達到6%，應該要變多少錢？」
        target_value = monthly_pay * (((1 + target_rate) ** invest_duration - 1) / target_rate)
        
        if total_cost > 0:
            st.divider()
            
            # 顯示比較結果
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("妳的總投入本金", f"${int(total_cost):,}")
                st.metric("目前實際市值", f"${int(current_value):,}")
            with col_res2:
                st.metric("6% 及格目標線", f"${int(target_value):,}", help="如果達到年化6%，至少應該要有這個數字")
                diff = current_value - target_value
                st.metric("與目標差距", f"${int(diff):,}", delta_color="normal")

            # 講評
            if current_value >= target_value:
                st.success(f"🎉 **太棒了！成績優異！**\n\n妳的資產比「6% 及格線」還多了 **${int(diff):,}** 元。\n這代表妳的定期定額策略非常成功，年化報酬率超過 6% 囉！")
                st.balloons()
            elif current_value > total_cost:
                st.info(f"🙂 **有賺錢，但還在努力中**\n\n雖然有賺錢 (比本金多 **${int(current_value-total_cost):,}**)，但還沒超過 6% 的及格線。\n如果是剛開始存前兩年，這很正常，繼續保持！")
            else:
                st.error(f"📉 **目前暫時虧損**\n\n現在市值低於本金。定期定額最喜歡這種時候（微笑曲線），因為現在買的單位數變多了，等行情回來會賺更快！")
    # 3. 個股 AI 診斷
    st.write("### 🔍 個股健康檢查")
    c_search, c_btn = st.columns([3, 1])
    with c_search:
        code_input = st.text_input("輸入股票代號 (如 2330)", "")
    with c_btn:
        st.write(""); st.write("")
        do_analyze = st.button("AI 診斷", use_container_width=True)

    if do_analyze and code_input:
        code = code_input.strip()
        ch_name = twstock.codes[code].name if code in twstock.codes else code

        try:
            with st.spinner(f"AI 正在分析 {ch_name} ..."):
                # 抓資料
                ticker = f"{code}.TW"
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2y")
                if hist.empty:
                    ticker = f"{code}.TWO"
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="2y")
                
                if hist.empty:
                    st.error("❌ 查無資料")
                else:
                    price = hist['Close'].iloc[-1]
                    ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
                    ma240 = hist['Close'].rolling(window=240).mean().iloc[-1]
                    buy_target = ma60 * 0.95 # 建議價
                    
                    st.markdown(f"#### 📊 {ch_name} ({code})")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("目前股價", f"${price:.2f}")
                    m2.metric("🎯 建議買入價", f"${buy_target:.2f}", "季線95折")
                    m3.metric("季線", f"${ma60:.2f}")
                    m4.metric("年線", f"${ma240:.2f}")

                    # AI 說明
                    st.write("#### 📋 AI 健檢報告")
                    reasons = []
                    score = 60
                    
                    if price > ma240:
                        reasons.append("✅ **長線多頭**：股價在年線之上 (+20分)")
                        score += 20
                    else:
                        reasons.append("❌ **長線空頭**：股價跌破年線，趨勢轉弱 (-30分)")
                        score -= 30
                        
                    if price < ma60:
                        reasons.append("✅ **價格合理**：低於季線，適合分批買 (+10分)")
                        score += 10
                    
                    # 顏色判斷
                    color = "green" if score >= 80 else ("orange" if score >= 40 else "red")
                    decision = "強力推薦" if score >= 80 else ("分批佈局" if score >= 60 else ("觀望" if score >= 40 else "不推薦"))
                    
                    st.markdown(f"""
                    <div style="padding:15px; border-left:5px solid {color}; background-color:#f9f9f9;">
                        <h3>{decision} (評分: {score})</h3>
                        <ul>{''.join([f'<li>{r}</li>' for r in reasons])}</ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 圖表
                    df_chart = pd.DataFrame({'Price': hist['Close'], 'MA240': hist['Close'].rolling(window=240).mean()}).tail(250)
                    st.line_chart(df_chart, color=["#888888", "#ff0000"])

        except Exception as e:
            st.error(f"分析錯誤: {e}")
