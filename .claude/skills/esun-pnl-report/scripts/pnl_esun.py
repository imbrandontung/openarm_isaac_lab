# -*- coding: utf-8 -*-
"""每月已實現損益計算 — 加權平均成本分類帳 (現股 / 融資 分開記帳)。

已實現損益(每筆賣出) = 賣出淨收入(價金 − 手續費 − 交易稅)
                       − 平均成本 × 股數
                       − 融資利息
分類帳跨月累積：較早月份的買進會留在庫存，供之後月份的賣出計算成本。

限制：對帳單只含「當期」交易，最早一期之前的開倉成本無法取得。若某賣出的
股數 > 帳上已知庫存，缺口部分以「該筆賣價」回填成本(等於該部分損益記 0)，並在
note 中標記，避免虛增/虛減損益。
"""
from collections import defaultdict
from parse_esun import parse_statement


def compute(files):
    """files: 已解密對帳單 PDF 路徑清單。回傳每月彙總 list。"""
    stmts = [parse_statement(f) for f in files]
    stmts = [s for s in stmts if s["month"]]
    stmts.sort(key=lambda s: s["month"])

    ledger = defaultdict(lambda: [0.0, 0.0])   # (name,cat) -> [shares, cost(含買入手續費)]
    monthly = []
    for s in stmts:
        rp = 0.0
        fees = 0.0
        buy_amt = 0.0
        sell_amt = 0.0
        rows = []
        note = []
        for t in sorted(s["txns"], key=lambda x: x["date"]):
            key = (t["name"], t["cat"])
            if t["side"] == "買":
                ledger[key][0] += t["shares"]
                ledger[key][1] += t["gross"] + t["fee"]
                buy_amt += t["gross"] + t["fee"]
            else:
                sh, cost = ledger[key]
                if sh >= t["shares"] - 1e-6 and sh > 0:
                    avg = cost / sh
                    cost_out = avg * t["shares"]
                else:
                    # 庫存不足：缺口成本以賣價回填(該段損益=0)，其餘用現有均價
                    avg_known = cost / sh if sh > 0 else 0.0
                    known = sh
                    gap = t["shares"] - known
                    per_share_sell = t["gross"] / t["shares"]
                    cost_out = avg_known * known + per_share_sell * gap
                    avg = cost_out / t["shares"]
                    note.append(f"{t['name']}({t['cat']}) 賣量>帳上庫存 {int(gap)} 股，該段成本以賣價估")
                proceeds = t["gross"] - t["fee"] - t["tax"]
                pnl = proceeds - cost_out - t["interest"]
                rp += pnl
                sell_amt += t["gross"]
                ledger[key][0] = max(0.0, sh - t["shares"])
                ledger[key][1] = max(0.0, cost - cost_out)
                rows.append(dict(date=t["date"], name=t["name"], cat=t["cat"],
                                 shares=t["shares"], price=t["price"], avg=avg,
                                 proceeds=proceeds, cost=cost_out,
                                 interest=t["interest"], pnl=pnl))
            fees += t["fee"] + t["tax"] + t["interest"]
        monthly.append(dict(month=s["month"], nav=s["nav"], realized=rp, fees=fees,
                            buy=buy_amt, sell=sell_amt, turnover=buy_amt + sell_amt,
                            rows=rows, note=note))
    return monthly


if __name__ == "__main__":
    import sys
    m = compute(sys.argv[1:])
    for r in m:
        print(f"\n===== {r['month']}  NAV=${r['nav']:,}  已實現損益={r['realized']:+,.0f} "
              f"費用={r['fees']:,.0f} =====")
        for row in r["rows"]:
            print(f"  {row['date']} {row['name']}({row['cat']}) 賣{row['shares']:,.0f}@{row['price']:.2f} "
                  f"均成本{row['avg']:.2f} 損益{row['pnl']:+,.0f}")
        if r["note"]:
            print("  注意:", "; ".join(r["note"]))
    print(f"\n>>> 合計已實現損益 = {sum(r['realized'] for r in m):+,.0f} 元")
