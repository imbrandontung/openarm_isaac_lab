# 交接文件 → 地端（本機）Claude Code

> 由「雲端／遠端 Claude Code」交接給「本機 Claude Code」。
> 專案：imBrandon 公司郵件與官網建置｜網域：`im-brandon.com`
> 交接日：2026-07-21

---

## 為什麼交接

雲端／遠端 Claude Code 的執行端是雲端 Linux 沙盒，**無法操作使用者本機已登入的 Chrome**，因此無法代為點按 Google Workspace / Cloudflare 的設定頁。剩下的工作需要**能操作瀏覽器的本機環境**接手。

完整背景與所有技術細節見同目錄：**`company-email-setup-kb.md`**（以下簡稱 KB）。

---

## 接手前確認（本機 Claude Code 請先自檢）

1. **確認在本機執行**：`uname -a` 不應顯示 `Linux vm`、`whoami` 不應是 `root`、根目錄不應有 `container_info.json`。若出現這些 → 仍是雲端沙盒，**不要接手**。
2. **browser MCP 已掛且連上**：`claude mcp list` 顯示 `✔ Connected`（`@browsermcp/mcp` 或 `chrome-devtools-mcp` 或 `@playwright/mcp`，見 KB §7）。
3. **使用者的 Chrome 已登入**：Google Workspace 管理主控台、Cloudflare Dashboard 皆已登入。

---

## 目前進度

- ✅ 網域 `im-brandon.com` 在 Cloudflare（NS 正確）
- ✅ Google Workspace 註冊進行中（卡在網域驗證 / 啟用 Gmail 這一步）
- ✅ DNS 已發布：網域驗證 TXT、DKIM、MX 皆已生效（實際值見 KB §0 與附錄）
- ⬜ 未完成：完成 Google 驗證/啟用、SPF、DMARC、別名、官網

---

## 待辦（由本機 Claude Code 透過瀏覽器完成）

依序處理，每步做完回報使用者：

1. **校正 Cloudflare DNS**：對照 **KB §3**，確認 MX、SPF、DKIM、DMARC 記錄正確（含補上尚缺的 SPF / DMARC）。Name 欄用 `@` / `_dmarc` / `google._domainkey`。
2. **完成 Google Workspace 驗證**：回設定頁按「驗證 / 啟用 Gmail」；若失敗，依 KB §3、§9 對照 MX 組合與優先度。
3. **建立信箱與別名**：主帳號 `brandon@`，別名 `hello@` / `training@` / `support@` / `billing@`（KB §2）。
4. **驗證送達率**：用 mail-tester.com 寄測試信，確認 **10/10**（SPF/DKIM/DMARC 全綠）。
5. **官網（可後續）**：選 Framer 或 Cloudflare Pages → 加 A/CNAME → 開 HTTPS（KB §5）。

---

## 界線（務必遵守）

- **登入、兩步驗證（2FA）、刷卡付款**一律停下來交回使用者本人操作，不要代填。
- 只動與本任務相關的 DNS 記錄，**不要更動其他既有記錄**。
- 每個步驟做完就回報結果，卡住就把畫面／錯誤貼給使用者，不要自行硬推。

---

## 參考

- 主文件：`docs/company-email-setup-kb.md`（方案、DNS 完整記錄、費用、疑難排解、實測 DNS 值）
- 追蹤 PR：`imbrandontung/openarm_isaac_lab` #2（分支 `claude/company-email-setup-ju30a7`）
