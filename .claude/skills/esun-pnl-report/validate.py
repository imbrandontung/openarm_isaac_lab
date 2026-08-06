# -*- coding: utf-8 -*-
"""Skill 自我驗證：用官方資料 fixture 驗證損益彙總與報表產出。

不需對帳單 PDF（避免個資入庫）——驗證「官方數字模式」的計算與 HTML 產出。
用法：python validate.py [fixture.json]（預設 examples/2026-07_official.json）
成功 exit 0；任何斷言失敗 exit 1。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))
import report_html  # noqa: E402


def approx(a, b, tol=1):
    return abs(a - b) <= tol


def validate(fixture):
    with open(fixture, encoding="utf-8") as f:
        d = json.load(f)
    exp = d.get("_expected", {})
    fails = []

    realized = sum(m["realized"] for m in d["months"])
    unreal = sum(h["unreal"] for h in d["holdings"])
    div = sum(x["amount"] for x in d.get("dividends", []))
    op_total = realized + unreal + div

    checks = [
        ("已實現價差合計", realized, exp.get("realized_total")),
        ("未實現價差合計", unreal, exp.get("unrealized_total")),
        ("現金股利合計", div, exp.get("dividend_total")),
        ("操作總損益", op_total, exp.get("operation_total")),
    ]
    for name, got, want in checks:
        if want is None:
            continue
        ok = approx(got, want)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: 得 {got:,} / 期望 {want:,}")
        if not ok:
            fails.append(name)

    # 遺產(legacy)必須不計入操作損益
    legacy = d.get("legacy")
    if legacy:
        legacy_in_holdings = any(h["name"] == legacy["name"] for h in d["holdings"])
        legacy_in_div = any(x["name"] == legacy["name"] for x in d.get("dividends", []))
        ok = not legacy_in_holdings and not legacy_in_div
        print(f"  [{'PASS' if ok else 'FAIL'}] 遺產持股 {legacy['name']} 未列入操作損益")
        if not ok:
            fails.append("legacy_excluded")

    # 配息交叉驗證：每股 × 除息股數 == amount
    for x in d.get("dividends", []):
        calc = round(x["per_share"] * x["shares"])
        ok = approx(calc, x["amount"])
        print(f"  [{'PASS' if ok else 'FAIL'}] 配息 {x['name']}: {x['per_share']}×{x['shares']:,}={calc:,} / 表列 {x['amount']:,}")
        if not ok:
            fails.append(f"div:{x['name']}")

    # HTML 產出驗證
    out = os.path.join(HERE, "_validate_out.html")
    report_html.build_html(d, out)
    html = open(out, encoding="utf-8").read()
    for token, label in [(f"{op_total:,}", "操作總損益數字"),
                         (legacy["name"] if legacy else "力山", "內容")]:
        ok = token in html
        print(f"  [{'PASS' if ok else 'FAIL'}] HTML 含 {label}（{token}）")
        if not ok:
            fails.append(f"html:{label}")
    os.remove(out)
    return fails


if __name__ == "__main__":
    fx = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "examples", "sample_official.json")
    print(f"=== 驗證 fixture: {os.path.basename(fx)} ===")
    fails = validate(fx)
    if fails:
        print(f"\n❌ 驗證失敗：{', '.join(fails)}")
        sys.exit(1)
    print("\n✅ 全部通過")
