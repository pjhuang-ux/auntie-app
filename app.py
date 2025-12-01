import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import twstock
import altair as alt

# --- 設定網頁 ---
st.set_page_config(page_title="阿姨的樂退寶", page_icon="👵", layout="wide")

# ========================================================
# 🔧 工具函數區 (處理級距與數學)
# ========================================================

# 1. 勞保投保薪資分級表 (2024年版 - 簡化常用級距)
# 實際上更細，這裡列出常用區間，確保金額對應正確
INSURANCE_BRACKETS = [
    27470, 28800, 30300, 31800, 33300, 34800, 36300, 
    38200, 40100, 42000, 43900, 45800
]

def get_insured_salary(real_salary):
    """輸入實際薪資，回傳最接近的投保級距"""
    if real_salary >= 45800:
        return 45800
    if real_salary < 27470:
        return 27470
    # 找到第一個比實際薪資大的級距
    for bracket in INSURANCE_BRACKETS:
        if bracket >= real_salary:
            return bracket
    return 45800

# 2. 年金計算函數 (模擬勞動部試算)
def calculate_monthly_pension(principal, years, rate=0.0118):
    """
    principal: 累積總金額
    years: 預計要領幾年 (平均餘命)
    rate: 勞退基金保障收益率 (目前約 1.18% ~ 1.5%)
    使用 PMT 公式計算每月可領金額
    """
    months = years * 12
    monthly_rate = rate / 12
    # PMT 公式: 本金 * 利率 / (1 - (1+利率)^-期數)
    if rate == 0:
        return principal / months
    payment = principal * (monthly_rate * (1 + monthly_rate)**months) / ((1 + monthly_rate)**months - 1)
    return payment

# ========================================================
# 🎛️ 側邊欄：所有資料輸入 (統一入口)
# ========================================================
with st.sidebar:
    st.header("👵 阿姨的個人檔案")
    st.info("請先在這裡輸入資料，右邊會自動計算喔！")
    
    # 基本資料
    name = st.text_input("暱稱", "宜蘭阿姨")
    age = st.number_input("目前年齡", 25, 70, 50)
    retire_age = st.number_input("預計退休年齡", 55, 75, 65)
    life_expectancy = st.number_input("預計活到幾歲", 70, 100, 85, help="計算勞退要分幾年領")
    
    st.divider()
    
    # 財務資料
    st.markdown("#### 💰 收入與資產")
    real_salary = st.number_input("目前實際月薪", 27470, 200000, 42000, step=1000)
    # 自動轉換為投保薪資
    insured_salary = get_insured_salary(real_salary)
    st.caption(f"👉 自動對應投保級距：**${insured_salary:,}**")
    
    work_years = st.number_input("已累積勞保年資", 0, 40, 20)
    lao_tui_saved = st.number_input("勞退帳戶目前累積金額", 0, 10000000, 600000, step=10000)
    current_savings = st.number_input("目前已有的退休存款 (定存/股票)", 0, 50000000, 1000000, step=50000, help="除了勞保勞退，妳自己存了多少？")

    st.divider()
    
    # 環境設定
    st.markdown("#### 🌍 環境參數")
    inflation_rate = st.slider("預估通膨率", 0.0, 5.0, 2.0, 0.1, format="%f%%")
    city = st.selectbox("居住地點", ["台北市", "新北市", "桃園/新竹", "台中市", "台南/高雄", "宜蘭縣", "其他縣市"], index=5)
    life_style = st.select_slider("退休生活等級", options=["基礎(生存)", "舒適(生活)", "富裕(享受)"], value="舒適(生活)")
    lao_bao_discount = st.slider("勞保打折預估 (危機意識)", 50, 100, 80, 5, format="%d%%") / 100

# ========================================================
# 🧠 後端核心計算 (在顯示網頁前先算好)
# ========================================================

# 1. 支出計算
city_cost_db = {
    "台北市": [32000, 55000, 90000], "新北市": [26000, 42000, 70000],
    "桃園/新竹": [25000, 40000, 65000], "台中市": [24000, 38000, 60000],
    "台南/高雄": [23000, 35000, 55000], "宜蘭縣": [22000, 32000, 50000],
    "其他縣市": [20000, 30000, 50000]
}
style_idx = 0 if "基礎" in life_style else (1 if "舒適" in life_style else 2)
current_monthly_need = city_cost_db[city][style_idx]

# 通膨後的未來每月需求
years_to_retire = max(0, retire_age - age)
retirement_duration = max(1, life_expectancy - retire_age)
future_monthly_need = current_monthly_need * ((1 + inflation_rate/100) ** years_to_retire)

# 2. 收入計算 (政府給的)
# 勞保 (月領)
total_work_years = work_years + years_to_retire
lao_bao_monthly = min(insured_salary, 45800) * total_work_years * 0.0155 * lao_bao_discount

# 勞退 (月領 - 修正版公式)
# 假設未來薪資不成長，雇主提撥 6%，基金年化報酬率 2%
future_contribution = insured_salary * 0.06 * 12 * years_to_retire
# 簡化計算：將現有累積 + 未來提撥 加總 (實務上會有複利，這裡做保守估計)
total_lao_tui_fund = lao_tui_saved + future_contribution
# 使用年金公式算出月領金額 (假設退休後平均餘命領完)
lao_tui_monthly = calculate_monthly_pension(total_lao_tui_fund, retirement_duration)

govt_monthly_total = lao_bao_monthly + lao_tui_monthly

# 3. 缺口計算
monthly_gap = max(0, future_monthly_need - govt_monthly_total)
# 總資金缺口 (缺口 x 12個月 x 退休年數)
total_asset_gap = monthly_gap * 12 * retirement_duration

# 4. 投資目標計算 (每月要存多少？)
# 假設已有的存款 (current_savings) 會以 5% 複利成長
future_savings_val = current_savings * ((1 + 0.05) ** years_to_retire)
# 真實缺口 = 總資金缺口 - (現有存款長大後的錢)
real_total_gap = max(0, total_asset_gap - future_savings_val)

# 計算每月需要投入多少 (PMT) 來填補這個真實缺口
# 假設投資年報酬率 6%
if years_to_retire > 0 and real_total_gap > 0:
    monthly_invest_target = real_total_gap * (0.06/12) / ((1 + 0.06/12)**(years_to_retire*12) - 1)
else:
    monthly_invest_target = 0

# ========================================================
# 🖥️ 主頁面顯示
# ========================================================
st.title(f"👋 早安，{name}！")

tab1, tab2, tab3 = st.tabs(["🌳 財富花園 (總覽)", "🧮 缺口明細 (計算)", "🤖 投資行動 (建議)"])

# === 分頁 1: 財富花園 (自動化版) ===
with tab1:
    st.subheader("我的退休準備進度")
    
    # 計算進度百分比
    # 分母 = 退休需要的總資產 (政府給的總額 + 需要自備的總額)
    total_need_asset = (future_monthly_need * 12 * retirement_duration)
    # 分子 = 政府給的 + 自己已存的 (未來價值)
    govt_total_asset = govt_monthly_total * 12 * retirement_duration
    have_asset = govt_total_asset + future_savings_val
    
    progress = min(100, int((have_asset / total_need_asset) * 100))
    
    col_tree, col_msg = st.columns([1, 2])
    with col_tree:
        # 根據自動計算的進度顯示
        if progress < 30:
            st.markdown("# 🌱")
            st.caption(f"目前進度 {progress}% - 剛起步")
        elif progress < 70:
            st.markdown("# 🌳")
            st.caption(f"目前進度 {progress}% - 成長中")
        else:
            st.markdown("# 🍎🌳🍎")
            st.caption(f"目前進度 {progress}% - 快達標了！")
            
    with col_msg:
        st.write("#### 預期資產成長")
        if real_total_gap > 0:
            st.warning(f"阿姨，為了填補缺口，妳每個月建議要再多投資 **${int(monthly_invest_target):,}** 元！")
        else:
            st.success("恭喜！妳目前的存款與政府退休金非常足夠，保持下去即可！")
            
        # 畫圖
        chart_data = pd.DataFrame({
            "資金來源": ["政府給付", "現有存款(複利後)", "還需要存的缺口"],
            "金額": [govt_total_asset, future_savings_val, real_total_gap]
        })
        st.altair_chart(alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="金額", type="quantitative"),
            color=alt.Color(field="資金來源", type="nominal", scale=alt.Scale(range=['#4CAF50', '#2196F3', '#FF5252']))
        ))

# === 分頁 2: 缺口試算 (精確版) ===
with tab2:
    st.subheader("🧮 資金天平")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("退休後每月開銷 (含通膨)", f"${int(future_monthly_need):,}", f"現在行情: ${int(current_monthly_need):,}")
    with c2:
        st.metric("政府每月給妳 (預估)", f"${int(govt_monthly_total):,}", f"投保薪資: ${insured_salary:,}")
    with c3:
        if monthly_gap > 0:
            st.metric("每月資金缺口", f"${int(monthly_gap):,}", "需靠投資補足", delta_color="inverse")
        else:
            st.metric("每月結餘", f"${int(-monthly_gap):,}", "資金充裕")

    st.divider()
    
    st.write("#### 📝 詳細組成表")
    detail_df = pd.DataFrame({
        "項目": ["① 勞保年金 (打折後)", "② 勞退月領 (年金化)", "③ 資金缺口"],
        "金額 (月)": [int(lao_bao_monthly), int(lao_tui_monthly), int(monthly_gap)],
        "說明": [f"年資{total_work_years}年 x 1.55%", f"分{retirement_duration}年領完", "不足的部分"]
    })
    st.dataframe(detail_df, hide_index=True, use_container_width=True)
    
    if monthly_gap > 0:
        st.error(f"⚠️ 嚴重警告：如果不投資，退休後這 {retirement_duration} 年總共會缺 **${int(real_total_gap/10000):,} 萬元**！")

# === 分頁 3: AI 投資管家 (主動建議版) ===
with tab3:
    st.subheader("🤖 投資行動計畫")
    
    # 1. 顯示具體的投資目標 (回應 Feedback ⑥)
    if monthly_invest_target > 0:
        st.markdown(f"""
        <div style="padding:15px; border:2px solid #2196F3; border-radius:10px; background-color:#e3f2fd; color:black;">
            <h4>💰 本月任務：請投資 <b>${int(monthly_invest_target):,}</b> 元</h4>
            <p>只要每月投入這個金額，並達到年化 6% 報酬，就能填補妳的退休缺口！</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("妳的資金很充裕，可以選擇更保守的投資，或是單純領股息過生活！")
        
    st.divider()

    # 2. 預設推薦清單 (回應 Feedback ④, ⑤)
    st.write("### 📋 阿姨的專屬選股清單")
    
    # 判斷年齡給建議
    years_left = retire_age - age
    if years_left <= 5:
        st.warning(f"⚠️ 離退休只剩 {years_left} 年！建議轉向「保守防禦型」配置。")
        recommendations = pd.DataFrame({
            "代號": ["00878", "0056", "2412", "2892"],
            "名稱": ["國泰永續高股息", "元大高股息", "中華電", "第一金"],
            "類型": ["核心 (ETF)", "核心 (ETF)", "核心 (個股)", "核心 (金融)"],
            "適合原因": ["波動低、領息穩", "老牌高股息", "電信龍頭避風港", "官股銀行大到不能倒"]
        })
    else:
        st.info(f"💪 離退休還有 {years_left} 年，可以配置部分「成長型」資產來放大本金。")
        recommendations = pd.DataFrame({
            "代號": ["0050", "006208", "2330", "00878"],
            "名稱": ["元大台灣50", "富邦台50", "台積電", "國泰永續高股息"],
            "類型": ["核心 (大盤ETF)", "核心 (大盤ETF)", "衛星 (成長個股)", "核心 (配息ETF)"],
            "適合原因": ["跟著台灣經濟成長", "內扣費用低的大盤", "全球半導體龍頭", "波動小當作防護罩"]
        })
        
    st.table(recommendations) # 直接顯示表格
    
    st.divider()

    # 3. AI 個股診斷功能
    st.write("### 🔍 個股健康檢查")
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        stock_input = st.text_input("輸入代號查詢 (例如 2330)", "")
    with col_s2:
        st.write("")
        st.write("")
        btn = st.button("AI 診斷", use_container_width=True)

    if btn and stock_input:
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
                    
                    st.markdown(f"#### 📊 {ch_name} ({code})")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("股價", f"${current_price:.2f}")
                    c2.metric("季線", f"${ma60:.2f}")
                    c3.metric("年線", f"${ma240:.2f}")
                    
                    # 資金分配建議 (回應 Feedback ④)
                    st.write("#### 💰 資金分配建議")
                    if current_price < safe_price and current_price > ma240:
                        st.success("🟢 **強力買進**：建議分配 **30%** 資金買入 (衛星配置)")
                    elif current_price < ma60:
                        st.success("🟢 **分批買進**：建議分配 **10-15%** 資金買入")
                    else:
                        st.warning("🟡 **暫時觀望**：目前不建議投入，請保留現金或買 ETF。")

                    # 圖表
                    chart_df = pd.DataFrame({'Price': hist['Close'], 'MA240': hist['Close'].rolling(window=240).mean()}).tail(250)
                    st.line_chart(chart_df, color=["#888888", "#ff0000"])

        except Exception as e:
            st.error(f"分析錯誤: {e}")
