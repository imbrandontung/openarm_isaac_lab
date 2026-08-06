# -*- coding: utf-8 -*-
"""每月損益統計圖。

長條：每月「已實現損益」(綠獲利/紅虧損) + 選配「截至今日(未實現)」(琥珀色)。
折線：月底總資產 NAV。
每月柱下標示：手續費、融資利息。
prices: {股票名稱: 今日價}；asof_label: 例如 '截至 07-20(未實現)'。
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from collections import defaultdict
from pnl_esun import compute
from parse_esun import parse_statement

_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]
FONT = next((p for p in _CANDIDATES if os.path.exists(p)), None)


def _fp(sz):
    return fm.FontProperties(fname=FONT, size=sz) if FONT else fm.FontProperties(size=sz)


plt.rcParams["axes.unicode_minus"] = False


def current_holdings(files):
    """從對帳單累積出目前庫存 (name,cat)->[shares,cost]。"""
    ledger = defaultdict(lambda: [0.0, 0.0])
    for f in sorted(files):
        s = parse_statement(f)
        for t in sorted(s["txns"], key=lambda x: x["date"]):
            k = (t["name"], t["cat"])
            if t["side"] == "買":
                ledger[k][0] += t["shares"]
                ledger[k][1] += t["gross"] + t["fee"]
            else:
                sh, c = ledger[k]
                avg = c / sh if sh else 0
                ledger[k][0] = max(0, sh - t["shares"])
                ledger[k][1] = max(0, c - avg * t["shares"])
    return {k: v for k, v in ledger.items() if v[0] > 0}


def unrealized(files, prices):
    """回傳 (總未實現損益, 明細list)。prices: {name: px}。"""
    rows = []
    tot = 0.0
    for (name, cat), (sh, cost) in sorted(current_holdings(files).items()):
        px = prices.get(name)
        if px is None:
            continue
        u = sh * px - cost
        tot += u
        rows.append(dict(name=name, cat=cat, shares=sh, avg=cost / sh, price=px,
                         mv=sh * px, cost=cost, u=u))
    return tot, rows


def make_chart(files, out="esun_pnl.png", prices=None, asof_label=None):
    m = compute(files)
    months = [r["month"] for r in m]
    realized = [r["realized"] for r in m]
    nav = [r["nav"] for r in m]
    fee_m = [sum(t2 for t2 in [r["fees"]]) for r in m]  # 費用合計(含稅息)備用
    # 分開的手續費/利息（重新讀對帳單）
    fee_only, int_only = [], []
    for f in sorted(files):
        s = parse_statement(f)
        fee_only.append(sum(t["fee"] for t in s["txns"]))
        int_only.append(sum(t["interest"] for t in s["txns"]))

    xs = list(months)
    ys = list(realized)
    kinds = ["realized"] * len(months)
    u_tot = None
    if prices:
        u_tot, _ = unrealized(files, prices)
        xs.append(asof_label or "截至今日")
        ys.append(u_tot)
        kinds.append("unreal")

    fig, ax1 = plt.subplots(figsize=(11, 6), dpi=150)
    bg = "#0f1720"
    fig.patch.set_facecolor(bg)
    ax1.set_facecolor(bg)
    colors = []
    for v, k in zip(ys, kinds):
        if k == "unreal":
            colors.append("#f59e0b")
        else:
            colors.append("#16a34a" if v >= 0 else "#dc2626")
    idx = list(range(len(xs)))
    bars = ax1.bar(idx, ys, width=0.5, color=colors, zorder=3, edgecolor=bg)
    ax1.axhline(0, color="#64748b", lw=.8)
    hi = max(ys + [0])
    lo = min(ys + [0])
    ax1.set_ylim(lo - abs(lo) * 0.18 - 1, hi * 1.32 + 1)
    ax1.set_ylabel("損益 (元)", color="#e2e8f0", fontproperties=_fp(12))
    # X 軸標籤：月份 + 手續費/利息（多行），避免壓字
    xlabels = []
    for i, k in enumerate(kinds):
        if k == "realized":
            xlabels.append(f"{xs[i]}\n手續費 {fee_only[i]:,.0f}｜利息 {int_only[i]:,.0f}")
        else:
            xlabels.append(f"{xs[i]}\n未實現・以今日現價估")
    ax1.set_xticks(idx)
    ax1.set_xticklabels(xlabels, fontproperties=_fp(11), color="#cbd5e1")
    ax1.tick_params(colors="#94a3b8", length=0)
    for lbl in ax1.get_yticklabels():
        lbl.set_fontproperties(_fp(9))
    for i, (v, k) in enumerate(zip(ys, kinds)):
        ax1.text(i, v + hi * 0.03, f"{v:+,.0f}", ha="center", va="bottom",
                 color="#e2e8f0", fontproperties=_fp(13), fontweight="bold")
        if k == "unreal":
            ax1.text(i, v * 0.5, "未實現", ha="center", va="center",
                     color="#7c3b00", fontproperties=_fp(12), fontweight="bold")
    ax1.grid(axis="y", color="#1e293b", lw=.7, zorder=0)

    ax2 = ax1.twinx()
    ax2.plot(idx[:len(months)], nav, color="#38bdf8", marker="o", lw=2.2, zorder=4, markersize=7)
    ax2.set_ylabel("月底總資產 NAV (元)", color="#38bdf8", fontproperties=_fp(12))
    ax2.tick_params(colors="#38bdf8")
    for lbl in ax2.get_yticklabels():
        lbl.set_fontproperties(_fp(9))
    ax2.set_ylim(min(nav) * 0.90, max(nav) * 1.12)
    ax2.set_xlim(ax1.get_xlim())
    for i, y in zip(idx[:len(months)], nav):
        ax2.annotate(f"NAV ${y/1e6:.1f}M", (i, y), textcoords="offset points", xytext=(0, 12),
                     ha="center", color="#7dd3fc", fontproperties=_fp(10),
                     bbox=dict(boxstyle="round,pad=0.2", fc="#0b1220", ec="#1e3a5f", lw=.6))
    for sp in list(ax1.spines.values()) + list(ax2.spines.values()):
        sp.set_color("#334155")

    rsum = sum(realized)
    sub = f"已實現(對帳單) {rsum:+,.0f} 元"
    if u_tot is not None:
        sub += f"　+　未實現(今日) {u_tot:+,.0f} 元　=　總損益 {rsum+u_tot:+,.0f} 元"
    fig.suptitle("玉山證券 每月損益統計", color="#f8fafc", y=0.985,
                 fontproperties=_fp(18), fontweight="bold")
    ax1.set_title(sub, color="#94a3b8", pad=10, fontproperties=_fp(11))
    leg = [Patch(fc="#16a34a", label="已實現損益(獲利)"),
           Patch(fc="#dc2626", label="已實現損益(虧損)"),
           Patch(fc="#f59e0b", label="未實現損益(截至今日)"),
           Line2D([0], [0], color="#38bdf8", marker="o", label="月底總資產 NAV")]
    ax1.legend(handles=leg, loc="upper left", facecolor="#111c28", edgecolor="#334155",
               labelcolor="#cbd5e1", prop=_fp(9))
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out, facecolor=fig.get_facecolor())
    return out, m


if __name__ == "__main__":
    make_chart(["202605_dec.pdf", "202606_dec.pdf"], prices={"力山": 44.00, "臻鼎-KY": 478.50},
               asof_label="截至 07-20")
    print("saved")
