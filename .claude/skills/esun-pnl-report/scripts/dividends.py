# -*- coding: utf-8 -*-
"""現金股利計算：每股現金股利 × 除息股數。

每股現金股利可由 TWSE `get_company_dividend`（欄位「股東配發-盈餘分配之現金股利(元/股)」
加上法定/資本公積現金）取得；除息股數來自玉山 App「現金股利」查詢或庫存。

用法（呼叫端先備好 per_share 與 ex_shares）：
    from dividends import cash_dividends
    rows, total = cash_dividends(
        {"臻鼎-KY":3.45, "力山":0.60, "中信金":2.50, "玉山金":1.40},
        {"臻鼎-KY":37000, "力山":42000, "中信金":186, "玉山金":80000},
        exclude={"玉山金"})   # 玉山金為遺產、另計
"""


def cash_dividends(per_share, ex_shares, exclude=None):
    exclude = exclude or set()
    rows, total = [], 0.0
    for name, ps in per_share.items():
        sh = ex_shares.get(name, 0)
        amt = ps * sh
        row = dict(name=name, per_share=ps, shares=sh, amount=amt,
                   counted=(name not in exclude))
        rows.append(row)
        if name not in exclude:
            total += amt
    return rows, total


if __name__ == "__main__":
    rows, total = cash_dividends(
        {"臻鼎-KY": 3.45, "力山": 0.60, "中信金": 2.50, "玉山金": 1.40},
        {"臻鼎-KY": 37000, "力山": 42000, "中信金": 186, "玉山金": 80000},
        exclude={"玉山金"})
    for r in rows:
        flag = "" if r["counted"] else "（另計）"
        print(f"  {r['name']:8s} {r['per_share']:.2f} × {r['shares']:,} = {r['amount']:+,.0f}{flag}")
    print(f"  操作配息合計 = {total:+,.0f}")
