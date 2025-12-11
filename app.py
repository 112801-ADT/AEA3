import streamlit as st
import os
from datetime import date, datetime, timedelta
from audiorecorder import audiorecorder
from pydub import AudioSegment
import shutil

# 設定 ffmpeg 路徑 (將 Scripts 加入 PATH，讓 pydub 找得到 ffmpeg/ffprobe)
ffmpeg_dir = r"C:\Users\cwe93\anaconda3\envs\EE\Scripts"
os.environ["PATH"] += os.pathsep + ffmpeg_dir
# 為了保險，也可指定 converter (但 ffprobe 還是依賴 PATH)
AudioSegment.converter = os.path.join(ffmpeg_dir, "ffmpeg.exe")
import altair as alt
import json
import os
import pandas as pd
from dotenv import load_dotenv
from google.genai import Client, types

# ----------------------------------------------------------
# 讀取 .env
# ----------------------------------------------------------
load_dotenv()

# ----------------------------------------------------------
# 基本設定
# ----------------------------------------------------------
st.set_page_config(page_title="AI 記帳工具", layout="wide")

DATA_PATH = "data/records.json"

# 確保 data 資料夾存在
os.makedirs("data", exist_ok=True)

# 若 JSON 不存在就建立
if not os.path.exists(DATA_PATH):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

# ----------------------------------------------------------
# Gemini 解析函式（已修正）
# ----------------------------------------------------------
def parse_item_amount_gemini(text: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY4")
    if not api_key:
        return {"item": "", "amount": 0, "error": "GEMINI_API_KEY4 not found"}

    try:
        # 正確的 Gemini Client 初始化
        client = Client(api_key=api_key)

        prompt = f"""
你是一個拆解句子的助理。
你會收到一段生活化的文字，請先理解語意，解析出：
1. 品項 item
2. 金額 amount
3. 自動分類 category（例如：餐飲食品, 交通運輸, 居家生活, 服飾購物, 休閒娛樂, 醫療保健, 投資儲蓄, 其他）

⚠️ 回覆格式要求：
- 僅回傳 JSON，不能有多餘文字
- 格式如下：
{{
  "item": "...",
  "amount": 數字,
  "category": "..."
}}

範例：
1. 我買了30元的果汁 => {{"item": "果汁", "amount": 30, "category": "餐飲食品"}}
2. 坐公車花了15元 => {{"item": "公車費", "amount": 15, "category": "交通運輸"}}
3. 看電影 300 元 => {{"item": "電影票", "amount": 300, "category": "娛樂"}}

請解析以下文字：
{text}
"""


        # 使用 gemini-2.5-flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        raw = response.text.strip()

        cleaned = (
            raw.replace("```json", "")
               .replace("```", "")
               .replace("'", '"')
               .strip()
        )

        return json.loads(cleaned)

    except Exception as e:
        return {"item": "", "amount": 0, "error": str(e)}

# ----------------------------------------------------------
# 主介面（完全不動）
# ----------------------------------------------------------
st.title("💰 算你狠 - AI 記帳助手")
st.caption("輕鬆管理您的日常支出")

# ----------------------------------------------------------
# 📌 頁首：(目前留空)
# ----------------------------------------------------------
# 暫時留空，或可放簡單標題
# st.markdown("...")


# ----------------------------------------------------------
# 📌 側邊欄導覽
# ----------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2953/2953363.png", width=50) # 一個示意圖示
    st.title("功能選單")
    
    selected_page = st.radio(
        "前往",
        ["總覽&記帳", "支出記錄", "記錄管理", "統計分析", "帳目分析"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.caption("AI 記帳工具 v1.2")


# ----------------------------------------------------------
# 📌 頁面路由邏輯
# ----------------------------------------------------------

# ----------------------------------------------------------
# PAGE 1：總覽（新增支出）
# ----------------------------------------------------------
if selected_page == "總覽&記帳":
    # --- 計算並顯示 本週/本月 總開銷 ---
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records_overview = json.load(f)
    
    total_week = 0
    total_month = 0
    
    if records_overview:
        df_ov = pd.DataFrame(records_overview)
        df_ov["日期"] = pd.to_datetime(df_ov["日期"])
        # 確保金額是數字
        df_ov["金額"] = pd.to_numeric(df_ov["金額"], errors='coerce').fillna(0)
        
        today = pd.Timestamp(date.today())
        start_of_week = today - timedelta(days=7)
        start_of_month = today.replace(day=1) # 簡單用當月1號
        
        # 本週 (近7天)
        total_week = df_ov[df_ov["日期"] >= start_of_week]["金額"].sum()
        
        # 本月 (這個月)
        # 注意：這裡使用 "與今天同一月份" 的邏輯
        total_month = df_ov[
            (df_ov["日期"].dt.year == today.year) & 
            (df_ov["日期"].dt.month == today.month)
        ]["金額"].sum()

    st.header("💲近期總覽")
    
    # 顯示指標卡片
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("📅 本週總開銷 (近7天)", f"${total_week:,.0f}")
    m_col2.metric("🗓️ 本月總開銷", f"${total_month:,.0f}")

    st.markdown("---")

    # --- 頁籤區塊 (對話式記帳移至第一位) ---
    st.header("📝 新增支出")
    add_tabs = st.tabs([
        "對話式記帳", 
        "傳統手動輸入",
        "語音輸入",
        "發票語音 (Mock)"
    ])

    # ------------------------------------------------------
    # 對話式記帳（Gemini）
    # ------------------------------------------------------
    with add_tabs[0]:
        st.write("輸入一句自然語言描述，我會自動解析品項與金額")

        user_text = st.text_area(
            "請輸入：",
            placeholder="例如：我買了珍奶50元",
            height=100
        )

        if st.button("解析並新增", type="primary"):
            if user_text.strip() == "":
                st.error("❌ 請輸入描述文字")
            else:
                result = parse_item_amount_gemini(user_text)

                if "error" in result and result["error"]:
                    st.error(f"AI 解析失敗：{result['error']}")
                else:
                    item = result.get("item", "")
                    amount = result.get("amount", 0)

                    with open(DATA_PATH, "r", encoding="utf-8") as f:
                        records = json.load(f)

                    category_ai = result.get("category", "其他")

                    new_record = {
                        "品項": item,
                        "分類": category_ai,
                        "金額": amount,
                        "日期": str(date.today()),
                        "備註": user_text
                    }

                    records.append(new_record)

                    with open(DATA_PATH, "w", encoding="utf-8") as f:
                        json.dump(records, f, ensure_ascii=False, indent=4)

                    st.success(f"新增成功：{item} - {amount} 元")

    # ------------------------------------------------------
    # 手動輸入
    # ------------------------------------------------------
    with add_tabs[1]:
        item_name = st.text_input("品項名稱（例如：珍奶 / 公車票 / 優格）")
        category = st.selectbox("分類", ["餐飲食品", "交通運輸", "居家生活", "服飾購物", "休閒娛樂", "醫療保健", "投資儲蓄", "其他"])
        amount = st.number_input("金額（NT$）", min_value=0, value=0)
        date_input = st.date_input("日期", value=date.today())
        note = st.text_input("備註", "")

        if st.button("＋ 新增支出"):
            if item_name.strip() == "":
                st.error("❌ 請輸入品項名稱")
            else:
                with open(DATA_PATH, "r", encoding="utf-8") as f:
                    records = json.load(f)

                new_record = {
                    "品項": item_name,
                    "分類": category,
                    "金額": amount,
                    "日期": str(date_input),
                    "備註": note
                }

                records.append(new_record)

                with open(DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=4)

                st.success("✅ 成功新增支出！")

    # ------------------------------------------------------
    # 語音輸入 (Voice Input)
    # ------------------------------------------------------
    with add_tabs[2]:
        st.write("🎙️ 請點擊下方按鈕開始錄音，說完後再點一次結束")
        
        audio = audiorecorder("按此開始錄音", "錄音中...按此結束")

        if len(audio) > 0:
            st.success(f"錄音完成！長度：{audio.duration_seconds:.1f} 秒")
            
            # 使用 spinner 顯示處理中
            with st.spinner("AI 正在聽打並分析您的語音..."):
                # 1. 將音訊存檔
                timestamp = int(datetime.now().timestamp())
                temp_filename = f"temp_voice_{timestamp}.mp3"
                audio.export(temp_filename, format="mp3")

                try:
                    # 2. 呼叫 Gemini 進行語音轉文字 (STT) + 理解
                    # 改用 API Key 3
                    api_key_voice = os.getenv("GEMINI_API_KEY3") 
                    if not api_key_voice:
                         st.warning("⚠️ 找不到 GEMINI_API_KEY3，嘗試使用 GEMINI_API_KEY")
                         api_key_voice = os.getenv("GEMINI_API_KEY")

                    client_voice = Client(api_key=api_key_voice)

                    # 讀取音訊檔案
                    with open(temp_filename, "rb") as audio_file:
                        audio_data = audio_file.read()

                    stt_prompt = "請準確聽打這段錄音的內容，直接輸出繁體中文文字，不要任何其他說明。"
                    
                    # 使用 2.5-flash
                    response_stt = client_voice.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[
                            stt_prompt,
                            types.Part.from_bytes(data=audio_data, mime_type="audio/mp3")
                        ]
                    )
                    
                    transcribed_text = response_stt.text.strip()
                    st.info(f"👂 AI 聽到： **「{transcribed_text}」**")

                    # 3. 解析內容
                    if transcribed_text:
                        result = parse_item_amount_gemini(transcribed_text)
                        
                        if "error" in result and result["error"]:
                            st.error(f"解析失敗：{result['error']}")
                        else:
                            item = result.get("item", "")
                            amount = result.get("amount", 0)
                            cat = result.get("category", "其他")

                            # 顯示預覽
                            st.markdown(
                                f"""
                                <div style="background:#e8f5e9;padding:10px;border-radius:5px;border:1px solid #c8e6c9;">
                                    <b>預覽新增：</b><br>
                                    品項：{item}<br>
                                    分類：{cat}<br>
                                    金額：{amount}
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            if st.button("✅ 確認並新增此筆支出", key="confirm_voice_add"):
                                with open(DATA_PATH, "r", encoding="utf-8") as f:
                                    records = json.load(f)

                                new_record = {
                                    "品項": item,
                                    "分類": cat,
                                    "金額": amount,
                                    "日期": str(date.today()),
                                    "備註": f"[語音] {transcribed_text}"
                                }
                                records.append(new_record)
                                
                                with open(DATA_PATH, "w", encoding="utf-8") as f:
                                    json.dump(records, f, ensure_ascii=False, indent=4)
                                
                                st.success("已儲存！")
                                os.remove(temp_filename)
                                st.rerun()

                except Exception as e:
                    st.error(f"語音處理失敗：{e}")
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

    # ------------------------------------------------------
    # 發票語音 (Mock)
    # ------------------------------------------------------
    with add_tabs[3]:
        st.info("功能開發中...")

# ----------------------------------------------------------
# PAGE 2：支出記錄
# ----------------------------------------------------------
elif selected_page == "支出記錄":
    st.header("📋 支出記錄")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    if len(records) == 0:
        st.info("目前沒有任何支出紀錄")
    else:
        df = pd.DataFrame(records)
        
        # 轉換日期格式以便處理
        df["日期"] = pd.to_datetime(df["日期"])
        
        # 建立「年月」欄位用來篩選
        df["Month"] = df["日期"].dt.strftime("%Y-%m")
        
        # 取得所有出現過的月份 (降序排列)
        available_months = sorted(df["Month"].unique().tolist(), reverse=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
             # 下拉選單
            selected_month = st.selectbox("請選擇月份", available_months)
        
        # 篩選資料
        filtered_df = df[df["Month"] == selected_month].drop(columns=["Month"]).sort_values("日期", ascending=False)
        
        st.write(f"顯示 **{selected_month}** 的支出細項，共 {len(filtered_df)} 筆：")
        st.dataframe(filtered_df, use_container_width=True)

# ----------------------------------------------------------
# PAGE 3：記錄管理
# ----------------------------------------------------------
elif selected_page == "記錄管理":
    st.header("🛠️ 記錄管理（查詢 / 修改 / 刪除）")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        st.info("目前沒有任何支出紀錄")
    else:
        # 1. 為了能修改原始資料，我們需要知道每筆資料在原始 list 中的 index
        #    因此先將 records 加上 index 資訊打包成 DataFrame
        #    順便處理日期格式
        df_all = pd.DataFrame(records)
        df_all["original_index"] = df_all.index
        df_all["日期_dt"] = pd.to_datetime(df_all["日期"])
        df_all["Month"] = df_all["日期_dt"].dt.strftime("%Y-%m")

        # 2. 建立月份篩選器
        all_months = sorted(df_all["Month"].unique().tolist(), reverse=True)
        col_filter1, col_filter2 = st.columns([1, 2])
        
        with col_filter1:
            selected_month_manage = st.selectbox("📅 篩選月份", all_months, key="manage_month")
        
        # 根據月份篩選資料
        df_filtered = df_all[df_all["Month"] == selected_month_manage].sort_values("日期", ascending=False)

        # 3. 顯示該月列表 (只讀瀏覽用)
        with col_filter2:
            st.caption(f"📊 {selected_month_manage} 共有 {len(df_filtered)} 筆紀錄")
        
        # 簡化顯示欄位
        display_cols = ["日期", "品項", "分類", "金額", "備註"]
        st.dataframe(df_filtered[display_cols], use_container_width=True, hide_index=True, height=200)

        st.markdown("---")

        # 4. 編輯區塊：下拉選單選擇要修改的紀錄
        st.subheader("✍️ 編輯與刪除")
        
        if df_filtered.empty:
            st.info("本月無資料可編輯")
        else:
            # 製作選單的選項 list: (original_index, 顯示文字)
            # 使用 format_func 讓使用者看到易讀的字串，但程式拿回 original_index
            
            # 建立一個選項對應字典
            options_dict = {}
            for idx, row in df_filtered.iterrows():
                # 顯示格式： [日期] 品項 ($金額) - 備註
                label = f"[{row['日期']}] {row['品項']} (${row['金額']}) - {row['備註']}"
                options_dict[row['original_index']] = label
            
            # 讓使用者選擇
            selected_idx = st.selectbox(
                "👇 請選擇要編輯的消費紀錄：",
                options=list(options_dict.keys()),
                format_func=lambda x: options_dict[x]
            )

            # 5. 顯示編輯表單
            if selected_idx is not None:
                record_to_edit = records[selected_idx]
                
                with st.form(key="edit_form"):
                    col_edit1, col_edit2 = st.columns(2)
                    
                    with col_edit1:
                        new_name = st.text_input("品項", record_to_edit["品項"])
                        new_category = st.selectbox(
                            "分類",
                            ["餐飲食品", "交通運輸", "居家生活", "服飾購物", "休閒娛樂", "醫療保健", "投資儲蓄", "其他"],
                            index=["餐飲食品", "交通運輸", "居家生活", "服飾購物", "休閒娛樂", "醫療保健", "投資儲蓄", "其他"]
                            .index(record_to_edit["分類"]) if record_to_edit["分類"] in ["餐飲食品", "交通運輸", "居家生活", "服飾購物", "休閒娛樂", "醫療保健", "投資儲蓄", "其他"] else 7
                        )
                    
                    with col_edit2:
                        new_amount = st.number_input("金額", value=int(record_to_edit["金額"]))
                        # 日期處理
                        curr_date = datetime.strptime(record_to_edit["日期"], "%Y-%m-%d").date()
                        new_date = st.date_input("日期", value=curr_date)
                        new_note = st.text_input("備註", record_to_edit["備註"])

                    # 按鈕區
                    col_btn1, col_btn2 = st.columns([1, 1])
                    with col_btn1:
                        submit_update = st.form_submit_button("💾 儲存修改", type="primary", use_container_width=True)
                    with col_btn2:
                        pass

                # 處理儲存
                if submit_update:
                    records[selected_idx] = {
                        "品項": new_name,
                        "分類": new_category,
                        "金額": int(new_amount),
                        "日期": str(new_date),
                        "備註": new_note
                    }
                    with open(DATA_PATH, "w", encoding="utf-8") as f:
                        json.dump(records, f, ensure_ascii=False, indent=4)
                    st.success("✅ 修改已儲存！")
                    st.rerun()

                # 刪除區塊 (獨立比較安全)
                with st.expander("🗑️ 刪除此紀錄", expanded=False):
                    st.warning("確定要刪除這筆紀錄嗎？此動作無法復原。")
                    if st.button("確認刪除", type="primary"):
                        records.pop(selected_idx)
                        with open(DATA_PATH, "w", encoding="utf-8") as f:
                            json.dump(records, f, ensure_ascii=False, indent=4)
                        st.success("✅ 紀錄已刪除！")
                        st.rerun()

# ----------------------------------------------------------
# PAGE 4：統計分析
# ----------------------------------------------------------
elif selected_page == "統計分析":
    st.header("📊 消費情形分析")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    
    if not records:
        st.info("目前沒有資料可供分析")
    else:
        df = pd.DataFrame(records)
        df["日期"] = pd.to_datetime(df["日期"])
        # 確保金額是數字
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)

        # 定義時間範圍
        today = pd.Timestamp(date.today())
        last_30_days = today - timedelta(days=30)
        last_7_days = today - timedelta(days=7)

        # 篩選資料
        df_month = df[df["日期"] >= last_30_days]
        df_week = df[df["日期"] >= last_7_days]

        # 定義樣式函數
        def style_dataframe(df_in):
            return df_in.style.format({
                "金額": "{:,.0f}"
            }).set_properties(**{
                'font-size': '20px',
                'font-family': 'Microsoft JhengHei, sans-serif'
            }).set_properties(subset=['金額'], **{
                'font-family': 'Consolas, monospace',
                'font-weight': 'bold',
                'color': '#2E86C1'
            })

        # --- 區塊 1：近 7 天 ---
        st.markdown("### 📅 近 7 天消費分析")
        col1_week, col2_week = st.columns([2, 3])
        
        with col1_week:
            if df_week.empty:
                st.write("無資料")
            else:
                week_group = df_week.groupby("分類")["金額"].sum().reset_index()
                chart_week = alt.Chart(week_group).mark_arc(innerRadius=60).encode(
                    theta=alt.Theta(field="金額", type="quantitative"),
                    color=alt.Color(field="分類", type="nominal"),
                    tooltip=["分類", "金額"],
                    order=alt.Order("金額", sort="descending")
                ).properties(height=300)
                st.altair_chart(chart_week, use_container_width=True)

        with col2_week:
            if not df_week.empty:
                st.markdown("#### 📝 詳細列表")
                week_group_sorted = df_week.groupby("分類")["金額"].sum().reset_index().sort_values("金額", ascending=False)
                st.dataframe(
                    style_dataframe(week_group_sorted),
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )

        st.markdown("---")

        # --- 區塊 2：近 30 天 ---
        st.markdown("### 📅 近 30 天消費分析")
        col1_month, col2_month = st.columns([2, 3])

        with col1_month:
            if df_month.empty:
                st.write("無資料")
            else:
                month_group = df_month.groupby("分類")["金額"].sum().reset_index()
                chart_month = alt.Chart(month_group).mark_arc(innerRadius=60).encode(
                    theta=alt.Theta(field="金額", type="quantitative"),
                    color=alt.Color(field="分類", type="nominal"),
                    tooltip=["分類", "金額"],
                    order=alt.Order("金額", sort="descending")
                ).properties(height=300)
                st.altair_chart(chart_month, use_container_width=True)

        with col2_month:
            if not df_month.empty:
                st.markdown("#### 📝 詳細列表")
                month_group_sorted = df_month.groupby("分類")["金額"].sum().reset_index().sort_values("金額", ascending=False)
                st.dataframe(
                    style_dataframe(month_group_sorted),
                    use_container_width=True,
                    hide_index=True,
                    height=300
                )

# ----------------------------------------------------------
# PAGE 5：帳目分析
# ----------------------------------------------------------
elif selected_page == "帳目分析":
    st.header("🤖 AI 帳目分析")
    st.caption("讓 AI 幫您檢視本月的消費健康度")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    # 為了給 AI 分析，我們先計算本月資料
    today = date.today()
    this_month_str = today.strftime("%Y-%m")

    # 篩選本月資料
    month_records = [r for r in records if r["日期"].startswith(this_month_str)]

    if not month_records:
        st.info("本月尚無消費紀錄，快去記一筆吧！")
    else:
        # Session State 控制
        if "ai_analysis_result" not in st.session_state:
            st.session_state["ai_analysis_result"] = None

        if st.button("✨ 啟動 AI 顧問分析本月狀況", type="primary", use_container_width=True):
            with st.spinner("AI 正在分析您的消費行為..."):
                try:
                    # 取得專用 KEY
                    api_key_2 = os.getenv("GEMINI_API_KEY2")
                    if not api_key_2:
                        st.error("找不到 GEMINI_API_KEY2，請檢查 .env 設定")
                    else:
                        # 準備資料給 AI
                        total_m = sum(r["金額"] for r in month_records)
                        cat_summary = {}
                        for r in month_records:
                            c = r["分類"]
                            cat_summary[c] = cat_summary.get(c, 0) + r["金額"]
                        
                        sorted_items = sorted(month_records, key=lambda x: x["金額"], reverse=True)[:5]
                        
                        analysis_prompt = f"""
                        你是一位專業且貼心的理財顧問。
                        以下是使用者這個月 ({this_month_str}) 的消費數據概要：
                        
                        - 總花費：{total_m} 元
                        - 各分類花費：{json.dumps(cat_summary, ensure_ascii=False)}
                        - 前 5 筆最高單價項目：{json.dumps(sorted_items, ensure_ascii=False)}
                        
                        請根據以上數據進行分析：
                        1. 判斷花費占比最多的部分是否合理？
                        2. 觀察是否有明顯的「衝動消費」或「非必要支出」？
                        3. 給予簡短、具體的後續消費或省錢建議。
                        4. 語氣要像朋友給建議一樣親切自然，不要太說教。
                        
                        請直接輸出內容，不需要開頭問候。
                        """

                        client_2 = Client(api_key=api_key_2)
                        response_2 = client_2.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=analysis_prompt
                        )
                        st.session_state["ai_analysis_result"] = response_2.text
                except Exception as e:
                    st.error(f"分析失敗：{e}")

        # 顯示結果
        if st.session_state["ai_analysis_result"]:
            st.markdown("---")
            st.markdown("### 📝 分析報告")
            st.markdown(
                f"""
                <div style="
                    background-color: #f0f8ff;
                    border: 1px solid #bdd7ee;
                    padding: 25px;
                    border-radius: 10px;
                    font-size: 18px;
                    line-height: 1.8;
                    color: #333;
                ">
                    {st.session_state["ai_analysis_result"]}
                </div>
                """,
                unsafe_allow_html=True
            )



