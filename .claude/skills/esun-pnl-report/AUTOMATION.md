# 每月自動執行 (Monthly automation)

玉山證券每月上旬（約每月 2–5 日）寄出上一個月的「綜合月對帳單」。本 skill 搭配一個
每月排程（claude-code-remote Routine / 排程觸發器）自動化整個流程。

## 觸發時間
每月 **6 日 09:00**（給對帳單寄達留緩衝）。cron：`0 9 6 * *`。

## 每次觸發要做的事（Routine prompt 摘要）
1. 到 Google Drive 找最新的 `綜合月對帳單.pdf`（`search_files: title contains '綜合月對帳單'`，取最新一份）。
   - 若 Drive 沒有新的一份，改到 Gmail 搜 `from:esunnotify@bhcr.esunsec.com.tw`，
     提醒使用者在 Gmail 按「新增至雲端硬碟」。
2. `download_file_content` 抓進環境，解碼成 PDF。
3. **向使用者索取身分證字號當密碼**（不儲存、不寫檔）。解密。
4. 用 TWSE `get_realtime_quote` 取庫存標的當日價（力山=1515、臻鼎-KY=4958…）。
5. 算每月已實現價差（run_report.py）+ 未實現價差 + **現金股利**（dividends.py，每股股利用 TWSE
   `get_company_dividend` × 除息股數）。**含配息＝價差＋股利**。
6. 產生**含配息 HTML 報表**（`report_html.py`，把資料整理成 data dict）；用 `SendUserFile`
   （display: render）回傳給使用者。
7. **精準模式**：請使用者提供玉山官方「已實現損益查詢／庫存損益查詢／現金股利查詢」截圖，
   以官方數字覆蓋推估值；**繼承取得（成本記 0）之持股獨立為 legacy、不列入操作損益**。

## 為何需要人工提供密碼
PDF 以身分證字號加密；為保護個資，**不把身分證字號存進 Routine、環境變數或 repo**。
每月觸發時由使用者當次提供。若使用者接受風險、要求全自動，可自行將其設為當次環境變數
`ESUN_PDF_PASSWORD`，`run_report.py` 會讀取。

## 限制
- 本 session 無瀏覽器/Chrome MCP，無法自動登入玉山網帳抓「當月即時成交」或官方損益查詢；
  該部分需使用者提供匯出/截圖。
- 對帳單推估的「現股」成本，若持有人有早於首張對帳單的舊庫存會偏高；精準值請用玉山官方查詢覆蓋。
