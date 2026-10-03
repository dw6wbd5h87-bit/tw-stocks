#!/usr/bin/env python3
"""向證交所(上市)抓最新收盤資料,產生已內嵌資料的 index.html。
用法:python3 build.py        (產生後自動用瀏覽器開啟)
      python3 build.py --no-open   (排程/自動化時用)
"""
import csv, io, json, sys, datetime, pathlib, urllib.request, webbrowser

BASE = "https://openapi.twse.com.tw/v1"
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

def main():
    prices = get("/exchangeReport/STOCK_DAY_ALL")
    info = get("/opendata/t187ap03_L")
    px = {r.get("Code"): r for r in prices}
    buf, n = io.StringIO(), 0
    w = csv.writer(buf)
    for c in info:
        p = px.get(c.get("公司代號"))
        if not p:
            continue
        close, chg = num(p.get("ClosingPrice")), num(p.get("Change"))
        sh = num(c.get("已發行普通股數或TDR原股發行股數"))
        if not close or chg is None or not sh or close - chg <= 0:
            continue
        sec = IND.get(str(c.get("產業別")).zfill(2), str(c.get("產業別")))
        w.writerow([c["公司代號"], c.get("公司簡稱", ""), sec, round(sh * close / 1e8, 1), round(chg / (close - chg) * 100, 2)])
        n += 1
    if n == 0:
        print("沒有產生任何資料。證交所欄位可能有變,以下是各資料集第一筆的欄位供除錯:")
        print("STOCK_DAY_ALL:", list(prices[0].keys()) if prices else "空")
        print("t187ap03_L:", list(info[0].keys()) if info else "空")
        sys.exit(1)
    d = str(prices[0].get("Date", ""))
    try:
        date = f"{int(d[:-4]) + 1911}-{d[-4:-2]}-{d[-2:]}"
    except ValueError:
        date = datetime.date.today().isoformat()
    here = pathlib.Path(__file__).parent
    tpl = (here / "template.html").read_text(encoding="utf-8")
    emb = "const EMBED=" + json.dumps({"csv": buf.getvalue(), "date": date}, ensure_ascii=False).replace("</", "<\\/") + ";"
    out = here / "index.html"
    out.write_text(tpl.replace("/*EMBED*/", emb, 1), encoding="utf-8")
    print(f"完成:{n} 檔,資料日期 {date} → {out}")
    if "--no-open" not in sys.argv:
        webbrowser.open(out.resolve().as_uri())

if __name__ == "__main__":
    main()
