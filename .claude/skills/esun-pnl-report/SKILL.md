---
name: esun-pnl-report
description: >
  計算玉山證券（E.SUN Securities）帳戶的每月損益並產生統計圖。當使用者提到
  「玉山證」「玉山證券」「綜合月對帳單」「對帳單損益」「每月損益」「已實現/未實現損益」
  「損益統計圖」，或提供玉山證券的對帳單 PDF / 已實現損益查詢截圖時觸發。
  能力：從 Gmail/Google Drive 取得加密對帳單 → 用身分證字號解密 → 座標式解析交易明細
  → 加權平均成本法算每月已實現損益 → 併入今日市價(TWSE)算未實現損益 → 產生中文統計圖。
  可選擇以玉山官方「已實現損益查詢」「未實現損益查詢」數字覆蓋推估值，取得精準結果。
---

# 玉山證券 每月損益報表 (esun-pnl-report)

## 用途
把玉山證券的「綜合月對帳單」PDF 轉成每月損益數字與統計圖。對帳單本身**沒有**
現成的損益欄位，本 skill 用買賣明細以加權平均成本法自行計算已實現損益，並可
結合當日市價計算未實現（帳面）損益。

## 資料來源與流程
1. **取得對帳單**：寄件者 `esunnotify@bhcr.esunsec.com.tw`，主旨「【玉山證券】綜合月對帳單」。
   PDF 附件無法用 Gmail 連接器直接下載 → 請使用者在 Gmail 按「新增至雲端硬碟」，
   再用 Google Drive 連接器 `download_file_content`（大檔會落地成 tool-results 檔，
   用 Python 讀 JSON 的 `content` 欄位 base64 解碼成 PDF）。
2. **解密**：PDF 密碼＝持有人身分證字號（英文大寫）。用 `pikepdf.open(path, password=...)`。
   ⚠️ 身分證字號屬敏感個資，只在當次執行當密碼用，**絕不寫入檔案、commit 或外傳**。
3. **解析**：`scripts/parse_esun.py`（交易明細為 5 行折行，以「現股/融資/融券」為錨點）。
   解析後務必用對帳單底部「合計」列交叉驗證 Σ價金/手續費/交易稅/融資/利息。
4. **算損益**：`scripts/pnl_esun.py`（現股/融資分帳的加權平均成本分類帳）。
5. **今日市價**：用 TWSE 連接器 `get_realtime_quote(["1515","4958",...])` 取當日價，
   對照庫存算未實現損益。（股票代號：力山=1515、臻鼎-KY=4958。）
6. **出圖**：`scripts/chart_esun.py`（中文用文泉驛正黑字型；綠/紅=已實現、琥珀=未實現、藍線=NAV）。

## 一鍵執行
```bash
python scripts/run_report.py \
  --pdfs 對帳單1.pdf 對帳單2.pdf \
  --password <身分證字號大寫> \
  --prices '{"力山":44.0,"臻鼎-KY":478.5}' \
  --asof 07-20 --outdir OUT
```
輸出 `OUT/esun_pnl.png`、`esun_pnl.json`、`esun_pnl.csv`，並印出各月合計驗證與摘要。
`--prices` 由呼叫端先用 TWSE 即時報價工具取得後以 JSON 傳入。

## 精準模式（含配息＋玉山官方＋股利，建議）
對帳單推估的「現股」成本可能偏高（若持有人有早於首張對帳單的低成本舊庫存），
且看不到未在對帳單交易過的持股（例如繼承取得）。要精準時，請使用者提供玉山官方
三個查詢的截圖，用官方數字覆蓋、並加計配息：

1. **已實現損益查詢**（可查近三年、單次最長一年，切「不含配息」）→ 每月已實現「價差」官方值。
2. **未實現損益 / 庫存損益查詢** → 確切庫存股數與平均成本 → 精準未實現「價差」。
   逐檔標記類別；**繼承/贈與取得（成本記 0）之持股應獨立為 legacy、不列入操作損益**。
3. **現金股利查詢** → 各檔「除息股數」。每股現金股利用 TWSE `get_company_dividend`
   （盈餘＋公積現金股利）取得，`scripts/dividends.py` 計算 每股 × 除息股數。

### 產生含配息 HTML 報表
把上面官方數字整理成 data dict（見 `report_html.py` 的 demo 結構），呼叫：
```bash
python scripts/report_html.py report_data.json esun_pnl.html
```
`report_html.build_html()` 產生自包含、深淺色自適應、可 hover、附資料表的 HTML。
`operation 總損益 = 已實現價差 + 未實現價差 + 現金股利`；legacy（遺產）持股獨立卡、不計入。

## 開倉庫存（修正現股成本）
若持有人有早於首張對帳單的舊庫存（成本與近期買進不同），`pnl_esun.compute(files, opening=...)`
可注入開倉庫存 `{(name, cat): [shares, cost]}`（用玉山官方「庫存損益查詢」的股數×平均成本），
讓賣出的已實現損益用正確加權平均成本計算，修正「現股成本偏高」。

## 自我驗證
`python validate.py [fixture.json]`（預設 `examples/sample_official.json`，**去識別化假資料**）
驗證損益彙總、遺產排除、配息交叉核對與 HTML 產出；全通過 exit 0。不需對帳單 PDF。
> 隱私：committed 的 fixture 一律用去識別化假資料；真實帳戶數字只在當次 session 驗證、不入庫。
> 真實 7 月官方案例已於 session 驗證通過（已實現 +1,459,316、未實現 +2,281,280、配息 +153,315、
> 操作總損益 +3,893,911，遺產玉山金另計）。

## 相依套件
`pip install pikepdf pdfplumber matplotlib`；中文字型 `wqy-zenhei`（Debian/Ubuntu 內建）。

## 每月自動化
已搭配每月排程（Routine）在每月上旬觸發：抓最新對帳單 → 通知使用者提供密碼（不儲存）
→ 解析算損益出圖 → 回報。詳見 repo 內 `AUTOMATION.md`。
