# AI Accounting Tool - 功能與技術架構總表

本文件整理了目前系統中各項功能所使用的關鍵技術，按照應用程式的頁面結構進行編排。

## 核心技術 (Core Technologies)
*   **語言**: Python 3.12+
*   **介面框架**: Streamlit
*   **AI 模型**: Google Gemini 2.5 Flash 
*   **API 管理**: 自建 **高併發輪替機制 (Key Loop)**，支援 A~H 共 8 組 Key 自動故障轉移 (Failover)。
*   **資料儲存**: 本地 JSON 文件 (`data/records.json`, `data/budget.json`)。
*   **資料處理**: Pandas (數據分析), Altair (視覺化圖表)。

---

## 各頁面功能詳解

### 1. 側邊欄 (Sidebar)
*   **功能**: 頁面導航。
*   **技術**: `st.sidebar`, `st.radio` 用於切換不同功能模組。

### 2. 總覽&記帳 (Page 1)
此為應用程式的首頁，包含財務儀表板與多種記帳模式。

#### A. 財務儀表板 (Dashboard)
*   **功能**: 
    *   顯示本週與本月總支出。
    *   **[新功能]** 預算執行狀況表：紅字警示超支項目。
*   **技術**: 
    *   `Pandas` 時間序列篩選 (`dt.year`, `dt.month`)。
    *   `Pandas Style` 進行表格條件格式化 (超支顯示紅字)。

#### B. 記帳頁籤 (Tabs)

*   **Tab 1: 對話式記帳 (Conversational AI)**
    *   **功能**: 輸入自然語言（如「買咖啡50」），自動解析。
    *   **技術**: Gemini API (Text Generation)。
    *   **提示工程**: 設定 System Prompt 要求輸出純 JSON 格式。

*   **Tab 2: 傳統手動輸入 (Manual)**
    *   **功能**: 表單式輸入。
    *   **技術**: `st.text_input`, `st.number_input`, `st.selectbox`, `st.date_input`。

*   **Tab 3: 語音輸入 (Voice Input)**
    *   **功能**: 錄音後直接轉成記帳紀錄。
    *   **技術**: 
        *   `streamlit-audiorecorder`: 前端錄音元件。
        *   `pydub` + `ffmpeg`: 後端音訊處理與轉檔。
        *   **Gemini Multimodal (Audio)**: 直接將音訊檔傳給 AI 進行「語音轉文字 (STT)」與「意圖理解」。

*   **Tab 4: 掃描辨識 (Scan & Recognize)**
    *   **功能**: 上傳發票/收據照片，自動辨識消費細節。
    *   **技術**: 
        *   `st.file_uploader`: 圖片上傳。
        *   **Gemini Vision**: 視覺模型辨識圖片文字與結構。
        *   **防呆機制**: Prompt 中加入指令，若辨識不清則強制歸類為「其他」。

*   **Tab 5: 預算設定 (Budget Settings)**
    *   **功能**: 設定各分類每月預算上限。
    *   **技術**: 
        *   `st.slider`: 滑桿互動介面。
        *   JSON I/O: 讀寫 `data/budget.json`。

---

### 3. 支出記錄 (Page 2)
*   **功能**: 檢視歷史消費清單。
*   **技術**: 
    *   `Pandas`: 讀取 JSON 並轉為 DataFrame。
    *   `Dropdown`: 依照 `YYYY-MM` 格式動態生成月份篩選選單。

### 4. 記錄管理 (Page 3)
*   **功能**: 修改或刪除錯誤的紀錄。
*   **技術**: 
    *   `List Indexing`: 透過原始索引值定位 JSON 資料。
    *   `st.form`: 建立編輯表單，批量提交修改。

### 5. 統計分析 (Page 4)
*   **功能**: 視覺化消費分佈（近7天、近30天）。
*   **技術**: 
    *   `Altair`: 繪製互動式甜甜圈圖 (Donut Chart)。
    *   `Pandas GroupBy`: 進行分類匯總計算。

### 6. AI 帳目分析 (Page 5)
*   **功能**: AI 理財顧問，綜合分析消費習慣與預算執行率。
*   **技術**: 
    *   **Context Injection**: 將「本月消費紀錄」與「預算設定檔」動態注入到 Prompt 中。
    *   **Gemini 2.5**: 進行複雜邏輯推演與建議生成。
