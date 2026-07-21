# 公司郵件與官網建置 KB — im-brandon.com

> 知識庫文件｜品牌：imBrandon｜網域：`im-brandon.com`（Cloudflare 註冊/託管）
> 最後更新：2026-07-21

本文件記錄 imBrandon 公司網域郵件與官網的建置方案、實際 DNS 現況、修復步驟、費用與未來擴充。可作為設定 SOP 與日後查修依據。

---

## ⛔ 環境使用限制（重要）

**以後不使用 Claude Code 的「雲端／遠端環境」來執行需要動手操作的設定工作。**

- **原因**：雲端／遠端 Claude Code 的執行端是雲端 Linux 機器，**無法控制本機已登入的 Chrome、無法代為操作瀏覽器**（Google Workspace、Cloudflare 等設定頁面全都碰不到）。
- **改用方式（擇一，需能實際操作瀏覽器）**：
  - **Cowork（Claude 桌面 App）** — 內建電腦／瀏覽器操作能力，優先使用。
  - **本機終端機執行 Claude Code** — 讓 `claude` 跑在自己電腦上，並自行掛上 browser MCP（見 §7）。
- **如何判斷是不是雲端環境**：在終端機執行 `uname -a` 顯示 `Linux vm`、`whoami` 為 `root`、根目錄有 `container_info.json`，即為雲端沙盒 → 不適用本類需要動手點瀏覽器的工作。

---

## 0. 目前狀態速覽（含實測診斷）

以下為從外部 DNS 實際查到的 `im-brandon.com` 現況：

| 項目 | 狀態 | 內容 |
|------|:---:|------|
| 名稱伺服器 (NS) | ✅ | Cloudflare：`glen.ns.cloudflare.com` / `imani.ns.cloudflare.com` |
| 網域驗證 TXT | ✅ | `google-site-verification=ymHkdPa2rdOrTgf0kvuEJhanewLWae1PkCp2pyHnDV4`（已生效） |
| DKIM 簽章 | ✅ | `google._domainkey` 已發布 |
| MX 收信 | ⚠️ | `smtp.google.com`，**優先度為 10（應為 1）** |
| SPF | ⬜ | 建議補上（見 §3） |
| DMARC | ⬜ | 尚未設定（見 §3，可稍後補） |

### 🔧 目前唯一要修的地方

Google Workspace「驗證/啟用」失敗，最可能原因是 **MX 優先度不符**（Google 單筆 MX 標準為優先度 1，目前是 10），以及**按驗證時記錄尚未生效**。

**修復步驟：**
1. Cloudflare → `im-brandon.com` → DNS → 編輯 `MX @ smtp.google.com` → **Priority 10 → 1** → 儲存。
2. 回 Google Workspace 設定頁 → 再按一次「驗證 / 啟用 Gmail」。
3. 若仍失敗：代表該帳號要求的是**舊版 5 筆 MX**（見 §3 表），改用 5 筆版本後重試。

---

## 1. 整體架構

```
Cloudflare（管理 DNS + 網域）
   ├── 郵件 → Google Workspace（企業信箱收發）
   └── 官網 → Framer 或 Cloudflare Pages
```

Cloudflare 扮演「總機（DNS）」；郵件與網站分別交給各自服務商，只需在 Cloudflare 加對應 DNS 記錄。

---

## 2. 郵件方案：Google Workspace

### 為何選 Google Workspace
- 既有工作流已在 Google 生態（Gmail / Drive / Calendar），零學習成本。
- 需要正式收發（提案、報告），非僅轉發。
- 客戶往來、會議邀請以公司網域寄出，專業度高。

### 信箱命名規劃（1 付費帳號 + 免費別名）
只需付費開 **1 個使用者**，其餘用免費別名（每人最多約 30 個），全部收進同一信箱。

| 地址 | 用途 | 類型 |
|------|------|------|
| `brandon@im-brandon.com` | 主要對外身分 | 付費主帳號 |
| `hello@im-brandon.com` | 官網/社群公開接觸點 | 免費別名 |
| `training@im-brandon.com` | AI 工作坊/課程報名 | 免費別名 |
| `support@im-brandon.com` | 學員/客戶支援 | 免費別名 |
| `billing@im-brandon.com` | 請款、發票、財務 | 免費別名 |

> 寄件者顯示名稱（客戶收信看到的名字，如 `Brandon Tung`）於各帳號另設，隨時可改。

---

## 3. DNS 記錄完整參考

於 Cloudflare → DNS → Records 加入。**Name 欄只填前綴**，Cloudflare 會自動補網域。MX/TXT 不需（也不會）啟用橙色雲朵 Proxy。

### ① 網域驗證
| Type | Name | Content |
|------|------|---------|
| TXT | `@` | `google-site-verification=…`（從 Google 後台複製；現況值見 §0） |

### ② MX（收信）
**新版（單筆，建議）：**
| Type | Name | Server | Priority |
|------|------|--------|----------|
| MX | `@` | `smtp.google.com` | **1** |

**舊版（5 筆，若 Google 頁面顯示這組就用這組）：**
| Server | Priority |
|--------|----------|
| `aspmx.l.google.com` | 1 |
| `alt1.aspmx.l.google.com` | 5 |
| `alt2.aspmx.l.google.com` | 5 |
| `alt3.aspmx.l.google.com` | 10 |
| `alt4.aspmx.l.google.com` | 10 |

> ⚠️ 兩種擇一，不可混用。以 Google 設定頁顯示的為準。

### ③ SPF（授權寄信）
| Type | Name | Content |
|------|------|---------|
| TXT | `@` | `v=spf1 include:_spf.google.com ~all` |

> 全網域只能有一筆 `v=spf1` TXT；日後接電子報平台需併進同一筆。

### ④ DKIM（簽章）
| Type | Name | Content |
|------|------|---------|
| TXT | `google._domainkey` | `v=DKIM1; k=rsa; p=…`（Google 後台 → Gmail → Authenticate email 產生） |

### ⑤ DMARC（政策，循序漸進）
| Type | Name | Content |
|------|------|---------|
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:brandon@im-brandon.com` |

> 先 `p=none` 監控 1–2 週 → `p=quarantine` → 視情況 `p=reject`。

---

## 4. Google AI Plus（2TB 家庭）與 Workspace（30GB）會衝突嗎？

**不會衝突，但容量也不會合併。** 兩者是獨立帳號系統：

| | Google AI Plus（消費者） | Google Workspace（企業） |
|---|---|---|
| 綁定 | 個人 `@gmail.com` | `@im-brandon.com` |
| 容量 | 2TB（可家庭共享） | 30GB（每使用者獨立） |
| 家庭共享 | 支援 | **無法**加入消費者家庭群組 |

**重點：** 個人 2TB **不能**給公司信箱用；公司帳號只有自己的 30GB。實務分工——公司帳號放「信件＋客戶交付文件」，個人 2TB 當大倉庫，需要時用「分享」互通（分享不佔對方容量）。空間不足再升級 Business Standard（每人 2TB）。

---

## 5. 官網方案

| 方式 | 難度 | 適合 |
|------|------|------|
| **Framer**（推薦） | 低（拖拉） | 重設計的個人品牌，內建 CMS |
| Cloudflare Pages | 中（需寫/上傳） | 免費、與 Cloudflare 整合、自動 HTTPS |
| 自租主機 | 高 | 完全自主 |

**指向網域：** Framer/外部工具會給 A 記錄或 CNAME，加到 Cloudflare（可開橙雲）；Cloudflare Pages 則自動設定。
**SSL：** 網域在 Cloudflare 即自動免費簽發，後台 SSL/TLS 選 **Full (strict)**。

---

## 6. 費用總覽（起步一人）

| 項目 | 月費 | 年費 |
|------|------|------|
| Google Workspace Business Starter（1 人） | ~US$6–8 | ~US$72–96 |
| 免費別名（hello/training/support/billing） | US$0 | US$0 |
| 官網（Framer 付費） | ~US$5–15 | ~US$60–180 |
| 官網（改 Cloudflare Pages） | US$0 | US$0 |
| 網域續費（Cloudflare 成本價） | — | ~US$10 |
| SSL 憑證 | 免費 | 免費 |

> Framer 路線約每月台幣 350–730；Cloudflare Pages 路線約 190–260。

---

## 7. 讓 Claude 直接操作瀏覽器（進階，選用）

**重要限制：** Claude Code 若跑在**雲端遠端環境**（如 web / 桌面 App 連到雲端沙盒），執行端是雲端 Linux 機器，**無法控制你本機已登入的 Chrome**。要 AI 動手點瀏覽器，需 **Claude Code 跑在本機終端機**，再掛 browser MCP。

### 本機安裝 Claude Code
```bash
# Mac / Linux
curl -fsSL https://claude.ai/install.sh | bash
# 或 npm（需 Node.js LTS）
npm install -g @anthropic-ai/claude-code
```
```powershell
# Windows PowerShell
irm https://claude.ai/install.ps1 | iex
```

### 掛上 browser MCP（擇一，均已驗證存在於 npm）
```bash
# Browser MCP（擴充功能版，接管你現有登入分頁；最接近 Cowork 體驗）
claude mcp add browsermcp -- npx -y @browsermcp/mcp@latest        # 需在 Chrome 商店裝「Browser MCP」擴充並按 Connect

# Chrome DevTools MCP（Google 官方）
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --browser-url=http://127.0.0.1:9222

# Playwright MCP（Microsoft 官方）
claude mcp add playwright -- npx -y @playwright/mcp@latest --cdp-endpoint=http://localhost:9222
```
驗證：`claude mcp list` 顯示 `✔ Connected`。

### 注意
- **2FA / 密碼 / 刷卡**一律本人操作；MCP 只沿用已登入 session。
- Chrome 136+ 的 `--remote-debugging-port` 不能用預設 profile，需加 `--user-data-dir` 指到獨立資料夾。

---

## 8. 建置順序 Checklist

- [ ] 確認網域在 Cloudflare（NS 為 Cloudflare）— ✅ 已完成
- [ ] Google Workspace 註冊，公司名稱填 `imBrandon`
- [ ] 加入 驗證 TXT ＋ MX ＋ SPF
- [ ] 產生並加入 DKIM
- [ ] **MX 優先度設為 1**（目前為 10，需修正）
- [ ] 回 Google 頁面按驗證 / 啟用 Gmail
- [ ] 設定 hello / training / support / billing 別名
- [ ] 加入 DMARC（先 `p=none`）
- [ ] mail-tester.com 寄測試信，確認 10/10
- [ ] 1–2 週後 DMARC 改 `p=quarantine`
- [ ] 官網：選 Framer / Cloudflare Pages → 加 A/CNAME → 開 HTTPS

---

## 9. 疑難排解

| 症狀 | 可能原因 | 解法 |
|------|----------|------|
| DNS 驗證失敗 | 記錄尚未生效就按驗證 | 等 10–15 分鐘再按 |
| Gmail 啟用失敗 | MX 優先度或組合不符 | 優先度改 1；或改用 Google 頁面顯示的那組 |
| 收不到信 | MX 開了橙雲 Proxy | MX 設 DNS only（本來就無橙雲選項） |
| 寄信進垃圾桶 | 缺 SPF/DKIM/DMARC | 三者補齊，mail-tester 檢查 |
| 改了沒反應 | 改到別的 zone / Name 欄錯 | 確認在 im-brandon.com，Name 用 `@`/`_dmarc`/`google._domainkey` |

---

## 附錄：實測 DNS 原始值（2026-07-21）

```
NS   : glen.ns.cloudflare.com, imani.ns.cloudflare.com
TXT  : google-site-verification=ymHkdPa2rdOrTgf0kvuEJhanewLWae1PkCp2pyHnDV4
MX   : smtp.google.com  (priority 10  ← 應改為 1)
DKIM : google._domainkey  → v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A…（已發布）
DMARC: 未設定 (ENOTFOUND)
```
