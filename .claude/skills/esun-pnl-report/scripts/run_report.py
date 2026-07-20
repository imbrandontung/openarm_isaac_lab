# -*- coding: utf-8 -*-
"""總控腳本：對帳單 → 解密 → 解析 → 每月已實現損益 → (選)截至今日未實現 → 出圖 + JSON。

用法：
  python run_report.py --pdfs a.pdf b.pdf [--password ID] \
        [--prices '{"力山":44.0,"臻鼎-KY":478.5}'] [--asof 07-20] \
        [--outdir OUT]

--pdfs 可為加密或已解密檔；提供 --password 會先用 pikepdf 解密到暫存。
--prices 由外部(呼叫端先用 TWSE 即時報價工具取得)以 JSON 傳入，用來算未實現損益。
輸出：OUT/esun_pnl.png、OUT/esun_pnl.json、OUT/esun_pnl.csv 並印出摘要。
"""
import argparse
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_esun import parse_statement, validate          # noqa: E402
from pnl_esun import compute                                # noqa: E402
import chart_esun                                           # noqa: E402


def _decrypt(paths, password):
    import pikepdf
    out = []
    tmp = tempfile.mkdtemp(prefix="esun_")
    for p in paths:
        try:
            pdf = pikepdf.open(p)              # 已是無密碼
            pdf.close()
            out.append(p)
        except pikepdf.PasswordError:
            if not password:
                raise SystemExit(f"[錯誤] {p} 已加密，請用 --password 提供身分證字號(大寫)")
            dp = os.path.join(tmp, os.path.basename(p).replace(".pdf", "_dec.pdf"))
            pk = pikepdf.open(p, password=password)
            pk.save(dp)
            pk.close()
            out.append(dp)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdfs", nargs="+", required=True)
    ap.add_argument("--password", default=os.environ.get("ESUN_PDF_PASSWORD"))
    ap.add_argument("--prices", default=None, help='JSON, e.g. {"力山":44.0}')
    ap.add_argument("--asof", default=None, help="截至日期標籤，如 07-20")
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    pdfs = _decrypt(a.pdfs, a.password)

    # 驗證 (印出各月加總，供對照對帳單『合計』)
    print("=== 解析驗證（對照對帳單合計）===")
    for p in pdfs:
        print(" ", validate(p))

    monthly = compute(pdfs)
    prices = json.loads(a.prices) if a.prices else None

    png = os.path.join(a.outdir, "esun_pnl.png")
    chart_esun.make_chart(pdfs, out=png, prices=prices,
                          asof_label=(f"截至 {a.asof}" if a.asof else None))

    # 未實現
    unreal_total, unreal_rows = (None, [])
    if prices:
        unreal_total, unreal_rows = chart_esun.unrealized(pdfs, prices)

    realized_sum = sum(r["realized"] for r in monthly)
    summary = dict(
        months=[dict(month=r["month"], nav=r["nav"], realized=round(r["realized"]),
                     fee=round(sum(t["fee"] for t in parse_statement(p)["txns"]))
                     if False else None,  # fee 於 CSV 另存
                     note=r["note"]) for r, p in zip(monthly, pdfs)],
        realized_total=round(realized_sum),
        unrealized_total=(round(unreal_total) if unreal_total is not None else None),
        unrealized_rows=[{k: (round(v, 2) if isinstance(v, float) else v)
                          for k, v in row.items()} for row in unreal_rows],
        total_pnl=round(realized_sum + (unreal_total or 0)),
        chart=png,
    )
    with open(os.path.join(a.outdir, "esun_pnl.json"), "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # CSV：每月 + 每筆已實現
    with open(os.path.join(a.outdir, "esun_pnl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["月份", "已實現損益", "手續費", "交易稅", "融資利息", "月底NAV"])
        for r, p in zip(monthly, pdfs):
            tx = parse_statement(p)["txns"]
            w.writerow([r["month"], round(r["realized"]),
                        round(sum(t["fee"] for t in tx)),
                        round(sum(t["tax"] for t in tx)),
                        round(sum(t["interest"] for t in tx)), r["nav"]])

    print("\n=== 摘要 ===")
    for r in monthly:
        print(f"  {r['month']}  已實現 {r['realized']:+,.0f}  NAV ${r['nav']:,}")
        for n in r["note"]:
            print("     注意:", n)
    print(f"  已實現合計 {realized_sum:+,.0f}")
    if unreal_total is not None:
        print(f"  未實現(截至 {a.asof}) {unreal_total:+,.0f}")
        print(f"  總損益 {realized_sum+unreal_total:+,.0f}")
    print(f"\n輸出：{png}, esun_pnl.json, esun_pnl.csv")


if __name__ == "__main__":
    main()
