#!/usr/bin/env python3
"""向證交所(上市)抓最新收盤資料,產生已內嵌資料的 index.html。
細分族群由 subsectors.json 決定(可自行編輯);沒列在裡面的個股沿用證交所產業別。
用法:python3 build.py            (產生後自動用瀏覽器開啟)
      python3 build.py --no-open  (排程/自動化時用)
"""
import csv, io, json, sys, datetime, pathlib, urllib.request, webbrowser

BASE = "https://openapi.twse.com.tw/v1"
HERE = pathlib.Path(__file__).parent
IND = {"01":"水泥工業","02":"食品工業","03":"塑膠工業","04":"紡織纖維","05":"電機機械","06":"電器電纜",
"08":"玻璃陶瓷","09":"造紙工業","10":"鋼鐵工業","11":"橡膠工業","12":"汽車工業","14":"建材營造",
"15":"航運業","16":"觀光餐旅","17":"金融保險","18":"貿易百貨","20":"其他","21":"化學工業",
"22":"生技醫療","23":"油電燃氣","24":"半導體業","25":"電腦及週邊設備","26":"光電業","27":"通信網路業",
"28":"電子零組件","29":"電子通路業","30":"資訊服務業","31":"其他電子業","35":"綠能環保",
"36":"數位雲端","37":"運動休閒","38":"居家生活"}

def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def num(v):
    try:
        return float(str(v).replace(",", "").replace("+", "").strip())
    except ValueError:
        return None

def load_sub():
    p = HERE / "subsectors.json"
    m = {}
    if p.exists():
        for name, codes in json.loads(p.read_text(encoding="utf-8")).items():
            for c in codes:
                m[str(c)] = name
    return m

def main():
    prices = get("/exchangeReport/STOCK_DAY_ALL")
    info = get("/opendata/t187ap03_L")
    px = {r.get("Code"): r for r in prices}
    sub = load_sub()
    rows = []
    for c in info:
        p = px.get(c.get("公司代號"))
        if not p:
            continue
        close, chg = num(p.get("ClosingPrice")), num(p.get("Change"))
        sh = num(c.get("已發行普通股數或TDR原股發行股數"))
        if not close or chg is None or not sh or close - chg <= 0:
            continue
        code = str(c["公司代號"])
        ind = IND.get(str(c.get("產業別")).zfill(2), str(c.get("產業別")))
        rows.append([code, c.get("公司簡稱", ""), ind, round(sh * close / 1e8, 1), round(chg / (close - chg) * 100, 2), round((num(p.get("TradeValue")) or 0) / 1e8, 2)])
    if not rows:
        print("沒有產生任何資料。證交所欄位可能有變,以下是各資料集第一筆的欄位供除錯:")
        print("STOCK_DAY_ALL:", list(prices[0].keys()) if prices else "空")
        print("t187ap03_L:", list(info[0].keys()) if info else "空")
        sys.exit(1)
    # 有任何個股被細分的產業,其餘沒被細分的個股歸入「產業別｜其他」
    split_inds = {r[2] for r in rows if r[0] in sub}
    for r in rows:
        ind = r[2]
        r[2] = sub.get(r[0]) or (f"{ind}｜其他" if ind in split_inds else ind)
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    d = str(prices[0].get("Date", ""))
    try:
        date = f"{int(d[:-4]) + 1911}-{d[-4:-2]}-{d[-2:]}"
    except ValueError:
        date = datetime.date.today().isoformat()
    # 資金流向:各族群成交金額(億),與歷史紀錄中前一個交易日比較
    tv = {}
    for r in rows:
        tv[r[2]] = tv.get(r[2], 0) + r[5]
    hist_p = HERE / "history.json"
    try:
        hist = json.loads(hist_p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        hist = {}
    prev = sorted(k for k in hist if k < date)
    flow = None
    if prev:
        pd = prev[-1]
        ptot = sum(hist[pd].values()) or 1
        flow = {"prevDate": pd, "s": {s: [v, round(v / ptot * 100, 3)] for s, v in hist[pd].items()}}
    hist[date] = {s: round(v, 2) for s, v in tv.items()}
    for k in sorted(hist)[:-60]:
        del hist[k]
    hist_p.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    emb = "const EMBED=" + json.dumps({"csv": buf.getvalue(), "date": date, "flow": flow}, ensure_ascii=False).replace("</", "<\\/") + ";"
    out = HERE / "index.html"
    out.write_text(tpl.replace("/*EMBED*/", emb, 1), encoding="utf-8")
    print(f"完成:{len(rows)} 檔,{len({r[2] for r in rows})} 個族群,資料日期 {date} → {out}")
    if "--no-open" not in sys.argv:
        webbrowser.open(out.resolve().as_uri())

if __name__ == "__main__":
    main()
