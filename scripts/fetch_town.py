"""各スキー場の近く（中心から半径2km）にある飲食店とコンビニ・スーパーの数を、OpenStreetMap（Overpass API）で数え、
data/town.json に保存して data/resorts.json の "town" に書き込む。診断の「近くに町がある」に使う。
データは © OpenStreetMap contributors（ODbL）。

使い方: python3 scripts/fetch_town.py          （未取得の分だけ取る。merge_batches.py の後にも再実行すれば town が戻る）
       python3 scripts/fetch_town.py --merge  （取得はせず、town.json を resorts.json に書き込むだけ）
店の数は頻繁には変わらないので、シーズン前に1回回せば十分。
"""
import json, math, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "town.json")
RES = os.path.join(ROOT, "data", "resorts.json")
UA = "YukiNavi/1.0 https://yukinavi-app.github.io/yukinavi/"
API = "https://overpass-api.de/api/interpreter"
RADIUS = 2000
BATCH = 25
FOOD = {"restaurant", "cafe", "bar", "pub", "fast_food", "izakaya"}
SHOP = {"convenience", "supermarket"}


def query(batch):
    parts = []
    for r in batch:
        a = f"around:{RADIUS},{r['lat']},{r['lng']}"
        parts.append(f'nwr({a})[amenity~"^({"|".join(sorted(FOOD))})$"];nwr({a})[shop~"^({"|".join(sorted(SHOP))})$"];')
    q = f"[out:json][timeout:240];({''.join(parts)});out tags center;"
    for attempt in range(5):
        # macOS付属のPythonはOverpassとTLS接続できないことがあるのでcurlを使う
        p = subprocess.run(["curl", "-s", "--max-time", "300", "-A", UA, "--data-urlencode", f"data={q}", API],
                           capture_output=True, text=True)
        try:
            return json.loads(p.stdout)["elements"]
        except Exception:
            print("  retry", attempt + 1, p.stdout[:80].replace("\n", " "))
            time.sleep(30 * (attempt + 1))   # 混雑（429/504）は待ってやり直す
    raise RuntimeError("overpass failed")


def dist_m(lat1, lng1, lat2, lng2):
    x = math.radians(lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(x, math.radians(lat2 - lat1)) * 6371000


def merge(out):
    resorts = json.load(open(RES, encoding="utf-8"))
    for r in resorts:
        t = out.get(r["id"])
        r["town"] = {"food": t["food"], "shop": t["shop"]} if t else None
    json.dump(resorts, open(RES, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def main():
    out = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if "--merge" not in sys.argv:
        resorts = [r for r in json.load(open(RES, encoding="utf-8")) if r.get("lat") is not None and r["id"] not in out]
        for i in range(0, len(resorts), BATCH):
            batch = resorts[i:i + BATCH]
            try:
                els = query(batch)
            except RuntimeError:
                print("failed batch", i); continue
            pts = []
            for e in els:
                lat = e.get("lat") or (e.get("center") or {}).get("lat")
                lng = e.get("lon") or (e.get("center") or {}).get("lon")
                tg = e.get("tags", {})
                kind = "food" if tg.get("amenity") in FOOD else "shop" if tg.get("shop") in SHOP else None
                if lat is not None and kind:
                    pts.append((lat, lng, kind))
            for r in batch:
                near = [k for la, ln, k in pts if dist_m(r["lat"], r["lng"], la, ln) <= RADIUS]
                out[r["id"]] = {"food": near.count("food"), "shop": near.count("shop")}
            json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            print(f"{min(i + BATCH, len(resorts))}/{len(resorts)}", flush=True)
            time.sleep(5)
    merge(out)


if __name__ == "__main__":
    main()
