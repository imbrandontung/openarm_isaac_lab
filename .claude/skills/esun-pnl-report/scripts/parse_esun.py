# -*- coding: utf-8 -*-
"""玉山證券 綜合月對帳單 解析引擎.

對帳單「上市、上櫃、興櫃交易明細」的每一筆交易在 PDF 內是「5 行折行」:
    L1: 類別(現股/融資/融券) [名稱片段] 手續費 <numA>
    L2: 2026
    L3: [名稱片段] 股數 單價 價金 c0 c1 c2 c3 c4 c5
    L4: MM/DD
    L5: 買賣(買進/賣出) [Ｙ] 交易稅 <numC>
其中 L3 價金後的 6 欄 = [債息, 利息, 融資金額, 融資自備款, 應收金額, 當日沖銷盈虧]。

parse_statement() 回傳 dict(month, nav, txns[...]).
可用對帳單底部「合計」欄位交叉驗證 Σ價金 / Σ手續費 / Σ交易稅 / Σ融資金額 / Σ利息。
"""
import re
import pdfplumber

CAT = {"現股", "融資", "融券"}
NUM = re.compile(r'^-?[\d,]+(?:\.\d+)?$')


def _n(t):
    return float(t.replace(',', '')) if NUM.match(t) else None


def _name(parts):
    s = "".join(parts).replace("－", "-").replace("Ｋ", "K").replace("Ｙ", "Y")
    return s


def parse_statement(path):
    """解析單一份對帳單 PDF (需為已解密檔)。"""
    with pdfplumber.open(path) as pdf:
        lines = []
        for pg in pdf.pages:
            lines += (pg.extract_text() or "").split("\n")

    nav = None
    ym = None
    rebate = 0.0   # 手續費折讓金額（對帳單底部）
    for ln in lines:
        m = re.search(r'(\d{4})年(\d{2})月', ln)
        if m and ym is None:
            ym = f"{m.group(1)}-{m.group(2)}"
        if ("資產總額" in ln or "資產小計" in ln):
            mm = re.search(r'\$([\d,]+)', ln)
            if mm:
                nav = int(mm.group(1).replace(',', ''))
        rb = re.search(r'手續費折讓金額\s*([\d,]+)\s*元', ln)
        if rb:
            rebate = float(rb.group(1).replace(',', ''))

    txns = []
    i = 0
    while i < len(lines) - 4:
        L1 = lines[i].split()
        if (L1 and L1[0] in CAT and lines[i + 1].strip() == "2026"
                and re.match(r'^\d\d/\d\d$', lines[i + 3].strip())):
            L3 = lines[i + 2].split()
            L5 = lines[i + 4].split()
            cat = L1[0]
            fee = next((_n(t) for t in L1[1:] if _n(t) is not None), 0.0)
            name1 = [t for t in L1[1:] if _n(t) is None]
            nums3 = [_n(t) for t in L3 if _n(t) is not None]
            name3 = [t for t in L3 if _n(t) is None]
            shares, price, gross = nums3[0], nums3[1], nums3[2]
            c = (nums3[3:9] + [0] * 6)[:6]          # 債息,利息,融資金額,融資自備款,應收,當沖
            interest = (c[0] or 0) + (c[1] or 0)
            margin_loan = c[2] or 0
            side = "買" if "買" in L5[0] else "賣"
            tax = next((_n(t) for t in L5[1:] if _n(t) is not None), 0.0)
            ymark = [t for t in L5 if t in ("Y", "Ｙ")]
            name = _name(name1 + name3 + ymark)
            txns.append(dict(
                month=ym, date="2026/" + lines[i + 3].strip(), cat=cat, name=name,
                side=side, shares=shares, price=price, gross=gross,
                fee=fee, tax=tax, interest=interest, margin_loan=margin_loan))
            i += 5
        else:
            i += 1
    return dict(month=ym, nav=nav, rebate=rebate, txns=txns)


def validate(path):
    """回傳解析後的欄位加總，供人工對照對帳單『合計』列。"""
    r = parse_statement(path)
    tx = r["txns"]
    return dict(month=r["month"], nav=r["nav"], n=len(tx),
                gross=sum(t["gross"] for t in tx),
                fee=sum(t["fee"] for t in tx),
                tax=sum(t["tax"] for t in tx),
                margin=sum(t["margin_loan"] for t in tx),
                interest=sum(t["interest"] for t in tx))


if __name__ == "__main__":
    import sys
    for f in sys.argv[1:]:
        print(validate(f))
