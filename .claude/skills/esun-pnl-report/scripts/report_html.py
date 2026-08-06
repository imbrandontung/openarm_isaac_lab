# -*- coding: utf-8 -*-
"""產生「含配息」損益總覽 HTML（深淺色自適應、hover、資料表）。

build_html(data, out) 的 data 結構：
{
  "account": "884*-05**129", "asof": "2026-07-20", "basis": "含配息",
  "months":   [{"month":"2026-05","realized":277995,"official":False,"fee":21365,"interest":0,"nav":21542253}, ...],
  "holdings": [{"name":"力山","shares":37000,"avg":23.38,"price":44.0,"unreal":754509}, ...],  # 操作，不含遺產
  "dividends":[{"name":"臻鼎-KY","per_share":3.45,"shares":37000,"amount":127650}, ...],       # 操作
  "legacy":   {"name":"玉山金","shares":80000,"price":35.85,"mv":2868000,"dividend":112000,"note":"媽媽遺產"}  # 可為 None
}
純標準函式庫、輸出自包含 HTML，無外部資源。
"""
import json
import html


def _n(v):
    return f"{v:+,.0f}" if v < 0 else f"+{v:,.0f}"


def build_html(data, out="esun_pnl.html"):
    months = data["months"]
    holds = data["holdings"]
    divs = data.get("dividends", [])
    legacy = data.get("legacy")
    realized_total = sum(m["realized"] for m in months)
    unreal_total = sum(h["unreal"] for h in holds)
    div_total = sum(d["amount"] for d in divs)
    total = realized_total + unreal_total + div_total

    real_js = [{"label": m["month"], "val": m["realized"],
                "note": ("玉山官方" if m.get("official") else "對帳單推估")
                + f"｜手續費 {m.get('fee',0):,.0f}・利息 {m.get('interest',0):,.0f}",
                "cls": "official" if m.get("official") else ""} for m in months]
    un_js = [{"label": f"{h['name']} {h['shares']:,}股", "val": h["unreal"],
              "note": f"均價 {h['avg']:.2f} → {h['price']:.2f}", "cls": "official"} for h in holds]
    div_js = [{"label": d["name"], "val": d["amount"],
               "note": f"每股 {d['per_share']:.2f} × {d['shares']:,} 股", "cls": "div"} for d in divs]

    legacy_html = ""
    if legacy:
        legacy_html = f"""
  <div class="legacy">
    <span class="badge">🌷 {html.escape(legacy.get('note','另計'))}・另計</span>
    <div class="txt"><b style="color:var(--ink)">{html.escape(legacy['name'])} 現股 {legacy['shares']:,} 股</b>　·　現價 {legacy['price']:.2f}、繼承取得（成本以繼承日計、系統記 0），不列入操作損益。</div>
    <div class="amt">市值 ${legacy['mv']:,}<small>＋配息 {_n(legacy.get('dividend',0))}</small></div>
  </div>"""

    def xls(items, subfmt):
        return "".join(f'<div class="xl" style="flex:1">{html.escape(a)}<small>{html.escape(b)}</small></div>'
                       for a, b in [subfmt(x) for x in items])

    real_xl = xls(months, lambda m: (m["month"], ("玉山官方・已含費用" if m.get("official")
                  else f"手續費 {m.get('fee',0):,.0f}｜折讓 {m.get('rebate',0):,.0f}｜利息 {m.get('interest',0):,.0f}")))

    # 費用/折讓摘要（僅統計有手續費資料的月份）
    fee_rows = [m for m in months if m.get("fee")]
    tot_fee = sum(m.get("fee", 0) for m in fee_rows)
    tot_reb = sum(m.get("rebate", 0) for m in fee_rows)
    tot_net = tot_fee - tot_reb
    fee_summary = ""
    if tot_fee:
        fee_summary = (f"　·　手續費合計 {tot_fee:,.0f}｜折讓 {tot_reb:,.0f}｜"
                       f"淨手續費 {tot_net:,.0f}（折讓率 {tot_reb/tot_fee*100:.0f}%）")
    un_xl = xls(holds, lambda h: (h["name"], f"{h['shares']:,}股 @{h['avg']:.2f}"))
    div_xl = xls(divs, lambda d: (d["name"], f"{d['per_share']:.2f} × {d['shares']:,}股"))

    trows = ""
    for m in months:
        trows += f'<tr><td>{m["month"]} 已實現</td><td>—</td><td>—</td><td>—</td><td class="pos">{_n(m["realized"])}</td><td>—</td><td>{"玉山官方" if m.get("official") else "對帳單推估"}</td></tr>'
    dmap = {d["name"]: d["amount"] for d in divs}
    for h in holds:
        dv = dmap.get(h["name"], 0)
        trows += f'<tr><td>{html.escape(h["name"])}（庫存）</td><td>{h["shares"]:,}</td><td>{h["avg"]:.2f}</td><td>{h["price"]:.2f}</td><td class="pos">{_n(h["unreal"])}</td><td class="divc">{_n(dv) if dv else "—"}</td><td>官方+TWSE</td></tr>'
    trows += f'<tr style="font-weight:700"><td>操作總損益（{data.get("basis","含配息")}）</td><td></td><td></td><td></td><td colspan="2" class="pos">{_n(total)}</td><td></td></tr>'
    if legacy:
        trows += f'<tr style="color:var(--legacy)"><td>{html.escape(legacy["name"])}（{html.escape(legacy.get("note","遺產"))}・另計）</td><td>{legacy["shares"]:,}</td><td>繼承日</td><td>{legacy["price"]:.2f}</td><td>市值 {legacy["mv"]:,}</td><td>{_n(legacy.get("dividend",0))}</td><td>官方+TWSE</td></tr>'

    tpl = _TEMPLATE
    repl = {
        "@BASIS@": html.escape(data.get("basis", "含配息")),
        "@ACCOUNT@": html.escape(data.get("account", "")),
        "@ASOF@": html.escape(data.get("asof", "")),
        "@TOTAL@": _n(total),
        "@EQ@": f"已實現價差 {_n(realized_total)}　＋　未實現價差 {_n(unreal_total)}　＋　現金股利 {_n(div_total)}",
        "@REALIZED@": _n(realized_total), "@UNREAL@": _n(unreal_total), "@DIV@": _n(div_total),
        "@DIVDETAIL@": "＋".join(f"{d['name']} {d['amount']:,.0f}" for d in divs),
        "@LEGACY@": legacy_html,
        "@FEESUMMARY@": fee_summary,
        "@REAL_XL@": real_xl, "@UN_XL@": un_xl, "@DIV_XL@": div_xl,
        "@TROWS@": trows,
        "@REAL_JS@": json.dumps(real_js, ensure_ascii=False),
        "@UN_JS@": json.dumps(un_js, ensure_ascii=False),
        "@DIV_JS@": json.dumps(div_js, ensure_ascii=False),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, str(v))
    with open(out, "w", encoding="utf-8") as f:
        f.write(tpl)
    return out


_TEMPLATE = r"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>玉山證券 損益總覽（@BASIS@）</title>
<style>
:root{--bg:#0f1720;--card:#16212e;--card2:#131c27;--line:#243244;--ink:#e8eef5;--ink2:#9fb0c3;--muted:#6b7c90;--gain:#22c55e;--loss:#ef4444;--div:#2dd4bf;--legacy:#a78bfa;--legacy-soft:#4c3a86;--shadow:0 1px 3px rgba(0,0,0,.4);}
@media (prefers-color-scheme:light){:root{--bg:#f1f5f9;--card:#fff;--card2:#f8fafc;--line:#e2e8f0;--ink:#0f172a;--ink2:#475569;--muted:#94a3b8;--gain:#16a34a;--loss:#dc2626;--div:#0d9488;--legacy:#7c3aed;--legacy-soft:#ede9fe;--shadow:0 1px 3px rgba(0,0,0,.08);}}
:root[data-theme=dark]{--bg:#0f1720;--card:#16212e;--card2:#131c27;--line:#243244;--ink:#e8eef5;--ink2:#9fb0c3;--muted:#6b7c90;--gain:#22c55e;--loss:#ef4444;--div:#2dd4bf;--legacy:#a78bfa;--legacy-soft:#4c3a86;}
:root[data-theme=light]{--bg:#f1f5f9;--card:#fff;--card2:#f8fafc;--line:#e2e8f0;--ink:#0f172a;--ink2:#475569;--muted:#94a3b8;--gain:#16a34a;--loss:#dc2626;--div:#0d9488;--legacy:#7c3aed;--legacy-soft:#ede9fe;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;-webkit-font-smoothing:antialiased;line-height:1.5;padding:24px 16px 48px}
.wrap{max-width:1040px;margin:0 auto}h1{font-size:22px;margin:0 0 2px}.sub{color:var(--ink2);font-size:13px;margin:0 0 20px}
.tag{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;background:rgba(45,212,191,.14);border:1px solid var(--div);color:var(--div);margin-left:6px;font-weight:700}
.hero{background:linear-gradient(135deg,var(--card),var(--card2));border:1px solid var(--line);border-radius:16px;padding:22px 24px;margin-bottom:16px;box-shadow:var(--shadow)}
.hero .lbl{color:var(--ink2);font-size:13px;margin-bottom:4px}.hero .big{font-size:40px;font-weight:800;color:var(--gain);font-variant-numeric:tabular-nums}.hero .eq{color:var(--muted);font-size:12.5px;margin-top:6px;font-variant-numeric:tabular-nums}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}.tile{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow)}
.tile .k{color:var(--ink2);font-size:12.5px;margin-bottom:6px}.tile .v{font-size:23px;font-weight:700;font-variant-numeric:tabular-nums}.tile .s{color:var(--muted);font-size:11.5px;margin-top:3px}
.pos{color:var(--gain)}.neg{color:var(--loss)}.divc{color:var(--div)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px 12px;box-shadow:var(--shadow)}
.panel h2{font-size:15px;margin:0 0 2px}.panel .h-sub{color:var(--ink2);font-size:12px;margin:0 0 18px}
.chart{display:flex;align-items:flex-end;gap:min(6%,34px);height:210px;padding:0 4px;border-bottom:1px solid var(--line)}
.col{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;position:relative}
.bar{width:min(62%,64px);border-radius:5px 5px 2px 2px;transition:filter .12s;min-height:3px;cursor:default;background:var(--gain)}
.bar.official{outline:2px solid #fbbf24;outline-offset:1px}.bar.div{background:var(--div)}.col:hover .bar{filter:brightness(1.13)}
.val{font-size:12.5px;font-weight:700;margin-bottom:6px;font-variant-numeric:tabular-nums;color:var(--ink)}
.xl{margin-top:8px;text-align:center;font-size:12px;color:var(--ink2)}.xl small{display:block;color:var(--muted);font-size:10.5px;margin-top:2px}
.tip{position:fixed;pointer-events:none;opacity:0;transition:opacity .1s;background:var(--card2);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.35);z-index:9;color:var(--ink);max-width:230px}
.legacy{margin-bottom:16px;background:var(--card);border:1px dashed var(--legacy);border-radius:16px;padding:16px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;box-shadow:var(--shadow)}
.legacy .badge{background:var(--legacy-soft);color:var(--legacy);font-size:12px;font-weight:700;padding:4px 10px;border-radius:999px;white-space:nowrap}.legacy .txt{flex:1;min-width:200px;font-size:13px;color:var(--ink2)}
.legacy .amt{font-size:19px;font-weight:700;font-variant-numeric:tabular-nums;text-align:right}.legacy .amt small{display:block;color:var(--div);font-size:12px;font-weight:600}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:12.5px;font-variant-numeric:tabular-nums}th,td{text-align:right;padding:7px 10px;border-bottom:1px solid var(--line)}th:first-child,td:first-child{text-align:left}thead th{color:var(--ink2);font-weight:600;font-size:11.5px}
details{margin-top:4px}summary{cursor:pointer;color:var(--ink2);font-size:13px;padding:6px 0}.foot{color:var(--muted);font-size:11px;margin-top:18px;line-height:1.7}.foot b{color:var(--ink2)}
@media (max-width:720px){.tiles{grid-template-columns:1fr}.grid2{grid-template-columns:1fr}.hero .big{font-size:32px}}
</style></head><body><div class="wrap">
<h1>玉山證券 損益總覽 <span class="tag">@BASIS@</span></h1>
<p class="sub">帳號 @ACCOUNT@　·　截至 @ASOF@　·　遺產持股另計、不列入操作損益@FEESUMMARY@</p>
<div class="hero"><div class="lbl">操作總損益（買賣價差 ＋ 現金股利）</div><div class="big">@TOTAL@ 元</div><div class="eq">@EQ@</div></div>
<div class="tiles">
<div class="tile"><div class="k">已實現價差</div><div class="v pos">@REALIZED@</div><div class="s">對帳單/玉山官方</div></div>
<div class="tile"><div class="k">未實現價差（今日庫存）</div><div class="v pos">@UNREAL@</div><div class="s">玉山官方庫存</div></div>
<div class="tile"><div class="k">現金股利</div><div class="v divc">@DIV@</div><div class="s">@DIVDETAIL@</div></div>
</div>
@LEGACY@
<div class="grid2">
<div class="panel"><h2>每月已實現價差</h2><p class="h-sub">綠柱＝獲利；金框＝玉山官方</p><div class="chart" id="c-real"></div><div style="display:flex;gap:min(6%,34px);padding:0 4px">@REAL_XL@</div></div>
<div class="panel"><h2>未實現價差（今日庫存）</h2><p class="h-sub">玉山官方庫存</p><div class="chart" id="c-unreal"></div><div style="display:flex;gap:min(6%,34px);padding:0 4px">@UN_XL@</div></div>
</div>
<div class="panel" style="margin-bottom:16px"><h2 style="color:var(--div)">現金股利</h2><p class="h-sub">每股股利 × 除息股數（TWSE）</p><div class="chart" id="c-div" style="height:150px"></div><div style="display:flex;gap:min(6%,34px);padding:0 4px">@DIV_XL@</div></div>
<details><summary>顯示資料表</summary><table><thead><tr><th>項目</th><th>股數</th><th>均價</th><th>現價</th><th>價差損益</th><th>配息</th><th>來源</th></tr></thead><tbody>@TROWS@</tbody></table></details>
<p class="foot">※ 價差：對帳單推估或玉山官方查詢。※ 配息：每股現金股利(TWSE)×除息股數。※ 遺產持股成本記0、另計。※ 個人試算，非正式對帳文件。</p>
</div><div class="tip" id="tip"></div>
<script>
const tip=document.getElementById('tip');
function bars(id,data,h){const el=document.getElementById(id);if(!el||!data.length)return;const mx=Math.max(...data.map(d=>Math.abs(d.val)));
data.forEach(d=>{const c=document.createElement('div');c.className='col';const v=document.createElement('div');v.className='val';v.textContent=(d.val>=0?'+':'')+d.val.toLocaleString();
const b=document.createElement('div');b.className='bar '+(d.cls||'');b.style.height=Math.max(3,Math.abs(d.val)/mx*h)+'px';if(d.val<0)b.style.background='var(--loss)';c.append(v,b);
c.addEventListener('mousemove',e=>{tip.style.opacity=1;tip.style.left=Math.min(e.clientX+14,innerWidth-238)+'px';tip.style.top=(e.clientY+14)+'px';
tip.innerHTML='<b style="color:'+(d.cls==='div'?'var(--div)':'var(--gain)')+'">'+(d.val>=0?'+':'')+d.val.toLocaleString()+' 元</b><br>'+d.label+'<br><span style="color:var(--muted)">'+d.note+'</span>';});
c.addEventListener('mouseleave',()=>tip.style.opacity=0);el.appendChild(c);});}
bars('c-real',@REAL_JS@,165);bars('c-unreal',@UN_JS@,165);bars('c-div',@DIV_JS@,105);
</script></body></html>"""


if __name__ == "__main__":
    import sys
    # 若提供 JSON 資料檔：python report_html.py data.json out.html
    if len(sys.argv) >= 2 and sys.argv[1].endswith(".json"):
        with open(sys.argv[1], encoding="utf-8") as f:
            d = json.load(f)
        out = sys.argv[2] if len(sys.argv) >= 3 else "esun_pnl.html"
        print("wrote", build_html(d, out))
        sys.exit(0)
    demo = {
        "account": "884*-05**129", "asof": "2026-07-20", "basis": "含配息",
        "months": [
            {"month": "2026-05", "realized": 277995, "official": False, "fee": 21365, "interest": 0, "nav": 21542253},
            {"month": "2026-06", "realized": 360149, "official": False, "fee": 13924, "interest": 1740, "nav": 28534706},
            {"month": "2026-07", "realized": 821172, "official": True, "fee": 0, "interest": 0, "nav": None},
        ],
        "holdings": [
            {"name": "力山", "shares": 37000, "avg": 23.38, "price": 44.0, "unreal": 754509},
            {"name": "臻鼎-KY", "shares": 44000, "avg": 441.09, "price": 478.5, "unreal": 1525259},
            {"name": "中信金", "shares": 186, "avg": 53.1, "price": 61.5, "unreal": 1512},
        ],
        "dividends": [
            {"name": "臻鼎-KY", "per_share": 3.45, "shares": 37000, "amount": 127650},
            {"name": "力山", "per_share": 0.60, "shares": 42000, "amount": 25200},
            {"name": "中信金", "per_share": 2.50, "shares": 186, "amount": 465},
        ],
        "legacy": {"name": "玉山金", "shares": 80000, "price": 35.85, "mv": 2868000, "dividend": 112000, "note": "媽媽遺產"},
    }
    print("wrote", build_html(demo, "esun_pnl_demo.html"))
