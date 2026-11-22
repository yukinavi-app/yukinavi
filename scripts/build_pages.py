"""Generate static, search-engine-readable pages from data/resorts.json.

Outputs (Japanese / English):
  r/<id>/index.html, en/r/<id>/index.html        one page per resort
  r/index.html, en/r/index.html                  prefecture-grouped list
  sitemap.xml, robots.txt
Re-run after any data change. The site URL lives in data/site.json.
"""
import html, json, os, shutil
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE = json.load(open(os.path.join(DATA, "site.json"), encoding="utf-8"))
BASE = SITE["baseUrl"].rstrip("/")
KLOOK_AID = "143472"


def klook_search(q, place, rid):
    """Klook公式のリンク生成ルール（affiliate.klook.com/redirect、k_siteはエンコードしたKlookのURL）"""
    from urllib.parse import quote
    target = f"https://www.klook.com/en-US/search/result/?query={quote(q)}"
    return (f"https://affiliate.klook.com/redirect?aid={KLOOK_AID}&amp;aff_label1=yukinavi&amp;aff_label2={place}"
            f"&amp;aff_label3={rid}&amp;k_site={quote(target, safe='-_.~')}")


A8_LINKMGR = '<script src="https://statics.8me.jp/a8link/a8linkmgr.js"></script><script>a8linkmgr({"config_id": "6ixko2yPeJmsYAuUlTIr"});</script>'  # A8の自動リンク変換（提携済み案件のリンクだけを書き換える）
RAKUTEN_ID = "59db25da.f3366089.59db25db.43c478c4"

PREF_ORDER = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県",
              "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県",
              "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県",
              "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県", "熊本県", "大分県",
              "宮崎県", "鹿児島県", "沖縄県"]

T = {
    "ja": {
        "lang": "ja", "title": "{name}（{pref}）リフト券料金・コース・アクセス｜YukiNavi",
        "desc": "{name}（{pref}）の{season}大人1日券{price}、標高{elev}、{courses}。{text}",
        "adult": "大人1日券", "student": "学生・ユース", "free": "無料", "elev": "標高（麓〜山頂）", "runs": "コース数",
        "lifts": "リフト数", "access": "アクセス", "terrain": "コース難易度", "beg": "初級", "int": "中級", "adv": "上級",
        "english": "英語対応", "en": {"high": "高い", "medium": "あり", "low": "限定的"}, "official": "公式サイト",
        "maps": "Googleマップで見る", "stay": "周辺の宿を探す（楽天トラベル）", "cta": "YukiNaviで今日の天気と雪の予報を見る", "same": "{pref}のほかのスキー場",
        "checked": "掲載情報の確認日：{d}。料金・営業状況は変わることがあります。お出かけ前に公式サイトでご確認ください。",
        "na": "—", "see_official": "公式サイトで確認", "list_title": "全国のスキー場一覧（都道府県別）｜YukiNavi",
        "list_desc": "日本全国{n}か所のスキー場の2026-27シーズンのリフト券料金・コース数・アクセスを都道府県別にまとめました。",
        "list_h1": "全国のスキー場一覧", "home": "YukiNavi トップ", "all": "全国のスキー場一覧",
        "runs_n": "{n}コース", "lifts_n": "{n}基", "season": "（{s}シーズン）",
        "ad": "PR：このページには広告（アフィリエイトリンク）が含まれます。", "about": "運営者情報・プライバシーポリシー",
    },
    "en": {
        "lang": "en", "title": "{name} ({pref}) lift pass price, runs & access | YukiNavi",
        "desc": "{name} in {pref}, Japan: {season}adult day pass {price}, elevation {elev}, {courses}. {text}",
        "adult": "Adult day pass", "student": "Student / youth", "free": "Free", "elev": "Elevation (base–top)", "runs": "Runs",
        "lifts": "Lifts", "access": "Access", "terrain": "Terrain", "beg": "Beginner", "int": "Intermediate",
        "adv": "Advanced", "english": "English support", "en": {"high": "Good", "medium": "Some", "low": "Limited"},
        "official": "Official site", "maps": "Open in Google Maps", "stay": "Find hotels nearby (Klook)", "klook_ski": "Lift tickets & rentals on Klook",
        "cta": "See today’s weather and snow forecast on YukiNavi", "same": "More ski resorts in {pref}",
        "checked": "Info last checked: {d}. Prices and operating status can change; check the official site before you go.",
        "na": "—", "see_official": "See official site", "list_title": "All ski resorts in Japan by prefecture | YukiNavi",
        "list_desc": "Lift pass prices, runs and access for {n} ski resorts across Japan for the 2026-27 season, by prefecture.",
        "list_h1": "Ski resorts in Japan", "home": "YukiNavi home", "all": "All ski resorts in Japan",
        "runs_n": "{n} runs", "lifts_n": "{n} lifts", "season": "{s} ",
        "ad": "Ad: this page contains affiliate links.", "about": "About & privacy policy",
    },
}

CSS = """.pr-note{font-size:13px;color:#5E6D7C;margin:6px 0 14px}*{box-sizing:border-box}body{margin:0;font-family:'Zen Kaku Gothic New',-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif;background:#F7F8F6;color:#14263A;line-height:1.65}
.num,.box b{font-family:'Barlow Condensed','Zen Kaku Gothic New',sans-serif;font-weight:600;font-variant-numeric:tabular-nums}
a{color:#14263A}.wrap{max-width:760px;margin:0 auto;padding:16px}header{background:#14263A;color:#fff}header a{color:#fff;text-decoration:none;font-weight:700;letter-spacing:.02em}
.crumb{font-size:12px;color:#5E6D7C;margin:6px 0 2px}.crumb a{color:#5E6D7C}h1{font-size:26px;line-height:1.3;margin:4px 0 6px}.sub{color:#5E6D7C;font-size:13px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px 18px;margin:14px 0}.box{border-left:2px solid #D3DDE5;padding:2px 0 2px 12px}
.box b{display:block;font-size:24px;line-height:1.1}.box span{font-size:12px;color:#5E6D7C}.bar{display:flex;height:10px;border-radius:3px;overflow:hidden;margin:6px 0}
.legend{font-size:12px;color:#5E6D7C}.cta{display:block;text-align:center;background:#EF5A1F;color:#fff;font-weight:700;text-decoration:none;border-radius:10px;padding:14px;margin:18px 0}
.links a{display:inline-block;margin:0 14px 8px 0}.note{font-size:12px;color:#5E6D7C;border-top:1px solid #D3DDE5;padding-top:12px;margin-top:20px}
ul.list{list-style:none;padding:0;columns:2;font-size:14px}ul.list li{margin:3px 0;break-inside:avoid}h2{font-size:18px;margin:22px 0 8px}
.lang{float:right;font-size:12px}
.article h2{font-size:19px;margin:28px 0 8px;padding-bottom:6px;border-bottom:1px solid #D3DDE5}.article p,.article li{font-size:15px;line-height:1.85}
.article table{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0;display:block;overflow-x:auto}.article th,.article td{border-bottom:1px solid #D3DDE5;padding:7px 8px;text-align:left;white-space:nowrap}.article th{background:#EEF3F6}
ul.guides{list-style:none;padding:0}ul.guides li{background:#fff;border:1px solid #D3DDE5;border-radius:10px;padding:12px 14px;margin:10px 0}"""


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def yen(v, L):
    return T[L]["free"] if v == 0 else f"¥{v:,}"


def page_url(L, rid):
    return f"{BASE}/{'en/' if L == 'en' else ''}r/{rid}/"


def head(L, title, desc, canonical, alt_ja, alt_en, jsonld=None):
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html><html lang="{L}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{alt_ja}"><link rel="alternate" hreflang="en" href="{alt_en}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}"><meta property="og:site_name" content="YukiNavi"><meta property="og:image" content="{BASE}/{"og-en.png" if L == "en" else "og.png"}"><meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;500;700&family=Barlow+Condensed:wght@600&display=swap"><link rel="icon" href="{BASE}/icons/icon-192.png"><link rel="apple-touch-icon" href="{BASE}/icons/apple-touch-icon.png"><style>{CSS}</style>{ld}</head><body>
<header><div class="wrap"><a href="{BASE}/">YukiNavi</a></div></header><main class="wrap">"""


def resort_page(r, L, same_pref):
    t = T[L]
    ja = L == "ja"
    name = r["nameJa"] if ja else (r.get("nameEn") or r["nameJa"])
    pref = r["prefJa"] if ja else (r.get("prefEn") or r["prefJa"])
    text = (r.get("descJa") if ja else r.get("descEn")) or ""
    access = r.get("accessJa") if ja else (r.get("accessEn") or r.get("accessJa"))
    if not access and r.get("timeJa"):
        access = f"{r['cityJa']}から {r['timeJa']}" if ja else f"{r.get('timeEn') or r['timeJa']} from {r.get('cityEn') or r['cityJa']}"
    season = t["season"].format(s=r["priceSeason"]) if r.get("priceSeason") else ""
    has_price = r.get("liftAdult") is not None
    has_elev = r.get("base") is not None and r.get("top") is not None
    price = yen(r["liftAdult"], L) if has_price else t["see_official"]
    elev = f"{r['base']}–{r['top']}m" if has_elev else None
    # 説明文には分かっている数字だけを並べる（「—」を入れない）
    parts = []
    if ja:
        if has_price: parts.append(f"{season}大人1日券{price}")
        if has_elev: parts.append(f"標高{elev}")
        if r.get("courses") is not None: parts.append(t["runs_n"].format(n=r["courses"]))
        desc = (f"{name}（{pref}）の" + "、".join(parts) + "。" if parts else f"{name}（{pref}）。") + text
    else:
        if has_price: parts.append(f"{season}adult day pass {price}")
        if has_elev: parts.append(f"elevation {elev}")
        if r.get("courses") is not None: parts.append(t["runs_n"].format(n=r["courses"]))
        desc = f"{name} in {pref}, Japan" + (": " + ", ".join(parts) if parts else "") + ". " + text
    desc = desc[:160]
    url_ja, url_en = page_url("ja", r["id"]), page_url("en", r["id"])
    jsonld = {"@context": "https://schema.org", "@type": "SkiResort", "name": name,
              "address": {"@type": "PostalAddress", "addressRegion": pref, "addressCountry": "JP"},
              "url": page_url(L, r["id"])}
    if r.get("lat") is not None:
        jsonld["geo"] = {"@type": "GeoCoordinates", "latitude": r["lat"], "longitude": r["lng"]}
    if r.get("officialUrl"):
        jsonld["sameAs"] = r["officialUrl"]

    boxes = [(price, t["adult"] + (f" ({r['priceSeason']})" if r.get("priceSeason") else ""))]
    if r.get("liftStudent") is not None:
        boxes.append((yen(r["liftStudent"], L), t["student"]))
    if has_elev:
        boxes.append((elev, t["elev"]))
    if r.get("courses") is not None:
        boxes.append((t["runs_n"].format(n=r["courses"]), t["runs"]))
    if r.get("lifts") is not None:
        boxes.append((t["lifts_n"].format(n=r["lifts"]), t["lifts"]))
    if r.get("english") in t["en"]:
        boxes.append((t["en"][r["english"]], t["english"]))
    grid = "".join(f'<div class="box"><b>{esc(v)}</b><span>{esc(k)}</span></div>' for v, k in boxes)

    terrain = ""
    if r.get("terrain"):
        b, i, a = r["terrain"]
        terrain = (f'<h2>{t["terrain"]}</h2><div class="bar"><div style="width:{b}%;background:#2E9E5B"></div>'
                   f'<div style="width:{i}%;background:#D7263D"></div><div style="width:{a}%;background:#1C1C1C"></div></div>'
                   f'<div class="legend">{t["beg"]} {b}% ・ {t["int"]} {i}% ・ {t["adv"]} {a}%</div>')

    links = []
    if r.get("officialUrl"):
        links.append(f'<a href="{esc(r["officialUrl"])}" rel="noopener" target="_blank">{t["official"]}</a>')
    from urllib.parse import quote
    links.append(f'<a href="https://www.google.com/maps/search/?api=1&query={quote(r["nameJa"])}" rel="noopener" target="_blank">{t["maps"]}</a>')
    if ja:
        stay = quote(f"https://travel.rakuten.co.jp/dosearch/?f_keyword={quote(r['nameJa'] + ' 周辺')}", safe="")
        links.append(f'<a href="https://hb.afl.rakuten.co.jp/hgc/{RAKUTEN_ID}/?pc={stay}&m={stay}" rel="noopener sponsored" target="_blank">{t["stay"]}</a>')
    else:
        # 英語ページは日本語の予約画面で離脱しないようKlookへ
        en_name = r.get("nameEn") or r["nameJa"]
        links.append(f'<a href="{klook_search(en_name + " hotel", "page-stay", r["id"])}" rel="noopener sponsored" target="_blank">{t["stay"]}</a>')
        links.append(f'<a href="{klook_search(en_name + " ski", "page-ticket", r["id"])}" rel="noopener sponsored" target="_blank">{t["klook_ski"]}</a>')

    others = "".join(
        f'<li><a href="{page_url(L, o["id"])}">{esc(o["nameJa"] if ja else (o.get("nameEn") or o["nameJa"]))}</a></li>'
        for o in same_pref if o["id"] != r["id"])
    app_link = f"{BASE}/?r={r['id']}" + ("&lang=en" if not ja else "")
    other_lang = f'<a class="lang" href="{url_en if ja else url_ja}">{"English" if ja else "日本語"}</a>'

    return (head(L, t["title"].format(name=name, pref=pref), desc, page_url(L, r["id"]), url_ja, url_en, jsonld)
            + f'{other_lang}<div class="crumb"><a href="{BASE}/{"en/" if not ja else ""}r/">{t["all"]}</a> › {esc(pref)}</div>'
            + f'<h1>{esc(name)}</h1><div class="sub">{esc(pref)}{" ・ " + esc(access) if access else ""}</div>'
            + f'<p class="pr-note">{esc(t["ad"])}</p>'
            + (f"<p>{esc(text)}</p>" if text else "")
            + f'<div class="grid">{grid}</div>{terrain}'
            + f'<a class="cta" href="{app_link}">{t["cta"]}</a>'
            + (f'<h2>{t["access"]}</h2><p>{esc(access)}</p>' if access else "")
            + f'<div class="links">{"".join(links)}</div>'
            + (f'<h2>{esc(t["same"].format(pref=pref))}</h2><ul class="list">{others}</ul>' if others else "")
            + f'<div class="note">{esc(t["checked"].format(d=r.get("checkedAt", "")))}<br><a href="{BASE}/about/">{t["about"]}</a></div>'
            + "</main>" + A8_LINKMGR + "</body></html>")


def list_page(L, by_pref, n):
    t = T[L]
    ja = L == "ja"
    body = ""
    for pref, rs in by_pref.items():
        label = pref if ja else (rs[0].get("prefEn") or pref)
        items = "".join(
            f'<li><a href="{page_url(L, r["id"])}">{esc(r["nameJa"] if ja else (r.get("nameEn") or r["nameJa"]))}</a>'
            f'{" — " + yen(r["liftAdult"], L) if r.get("liftAdult") is not None else ""}</li>' for r in rs)
        body += f"<h2>{esc(label)}（{len(rs)}）</h2><ul class=\"list\">{items}</ul>" if ja else \
            f"<h2>{esc(label)} ({len(rs)})</h2><ul class=\"list\">{items}</ul>"
    url_ja, url_en = f"{BASE}/r/", f"{BASE}/en/r/"
    other = f'<a class="lang" href="{url_en if ja else url_ja}">{"English" if ja else "日本語"}</a>'
    return (head(L, t["list_title"], t["list_desc"].format(n=n), url_ja if ja else url_en, url_ja, url_en)
            + f'{other}<h1>{t["list_h1"]}</h1><p>{esc(t["list_desc"].format(n=n))}</p>{body}</main></body></html>')


ARTICLE_T = {
    "ja": {"by": "書いた人：しい（現役スキーインストラクター・SAJクラウンプライズ）", "updated": "更新日：{d}",
           "list_title": "スキーの読みもの｜YukiNavi", "list_h1": "スキーの読みもの",
           "list_desc": "はじめてのスキーの準備、持ち物、行き方、お得なリフト券の買い方を、現役インストラクターがまとめました。",
           "cta": "YukiNaviで自分に合うスキー場を探す", "ad": "PR：このページには広告（アフィリエイトリンク）が含まれます。",
           "more": "ほかの読みもの"},
    "en": {"by": "Written by Schi, working ski instructor (SAJ Crown Prize)", "updated": "Updated {d}",
           "list_title": "Ski guides for Japan | YukiNavi", "list_h1": "Ski guides",
           "list_desc": "Practical guides for skiing in Japan: first-timer prep, train access, English lessons and lift pass prices.",
           "cta": "Find a resort that suits you on YukiNavi", "ad": "Ad: this page contains affiliate links.",
           "more": "More guides"},
}


def article_url(L, slug):
    return f"{BASE}/{'en/' if L == 'en' else ''}guide/{slug}/"


def link_resorts(html_body, L, ids):
    import re as _re
    def sub(m):
        rid = m.group(1)
        r = ids.get(rid)
        if not r:
            return esc(rid)
        name = r["nameJa"] if L == "ja" else (r.get("nameEn") or r["nameJa"])
        return f'<a href="{page_url(L, rid)}">{esc(name)}</a>'
    return _re.sub(r"\[\[([a-z0-9_]+)\]\]", sub, html_body)


def article_page(a, L, ids, others):
    t = ARTICLE_T[L]
    url = article_url(L, a["slug"])
    jsonld = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "description": a["description"],
              "dateModified": a["updated"], "author": {"@type": "Person", "name": "Schi"}, "inLanguage": L}
    more = "".join(f'<li><a href="{article_url(L, o["slug"])}">{esc(o["title"])}</a></li>' for o in others if o["slug"] != a["slug"])
    return (head(L, f'{a["title"]}｜YukiNavi' if L == "ja" else f'{a["title"]} | YukiNavi', a["description"], url, url, url, jsonld)
            + f'<div class="crumb"><a href="{BASE}/{"en/" if L == "en" else ""}guide/">{t["list_h1"]}</a></div>'
            + f'<h1>{esc(a["title"])}</h1><div class="sub">{t["by"]}<br>{t["updated"].format(d=a["updated"])}</div>'
            + f'<div class="note" style="border:none;padding:0;margin:0 0 14px">{t["ad"]}</div>'
            + f'<article class="article">{link_resorts(a["html"], L, ids)}</article>'
            + f'<a class="cta" href="{BASE}/{"?lang=en" if L == "en" else ""}">{t["cta"]}</a>'
            + (f'<h2>{t["more"]}</h2><ul>{more}</ul>' if more else "")
            + f'<div class="note"><a href="{BASE}/about/">{T[L]["about"]}</a></div></main>{A8_LINKMGR}</body></html>')


def articles_list_page(L, arts):
    t = ARTICLE_T[L]
    url = f"{BASE}/{'en/' if L == 'en' else ''}guide/"
    items = "".join(f'<li><a href="{article_url(L, a["slug"])}"><b>{esc(a["title"])}</b></a><br><span class="legend">{esc(a["description"])}</span></li>' for a in arts)
    return (head(L, t["list_title"], t["list_desc"], url, url, url)
            + f'<h1>{t["list_h1"]}</h1><p>{esc(t["list_desc"])}</p><ul class="guides">{items}</ul></main></body></html>')


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(content)


def main():
    resorts = [r for r in json.load(open(os.path.join(DATA, "resorts.json"), encoding="utf-8")) if r.get("status") != "closed"]
    by_pref = OrderedDict((p, []) for p in PREF_ORDER)
    for r in resorts:
        by_pref.setdefault(r["prefJa"], []).append(r)
    by_pref = OrderedDict((p, sorted(rs, key=lambda x: x["nameJa"])) for p, rs in by_pref.items() if rs)

    for d in ("r", os.path.join("en", "r")):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
    urls = [f"{BASE}/", f"{BASE}/r/", f"{BASE}/en/r/"]
    for pref, rs in by_pref.items():
        for r in rs:
            for L in ("ja", "en"):
                sub = "r" if L == "ja" else os.path.join("en", "r")
                write(os.path.join(ROOT, sub, r["id"], "index.html"), resort_page(r, L, rs))
                urls.append(page_url(L, r["id"]))
    write(os.path.join(ROOT, "r", "index.html"), list_page("ja", by_pref, len(resorts)))
    write(os.path.join(ROOT, "en", "r", "index.html"), list_page("en", by_pref, len(resorts)))

    ids = {r["id"]: r for r in resorts}
    for L in ("ja", "en"):
        ap = os.path.join(DATA, f"articles_{L}.json")
        sub = "guide" if L == "ja" else os.path.join("en", "guide")
        shutil.rmtree(os.path.join(ROOT, sub), ignore_errors=True)
        if not os.path.exists(ap):
            continue
        arts = json.load(open(ap, encoding="utf-8"))
        for a in arts:
            write(os.path.join(ROOT, sub, a["slug"], "index.html"), article_page(a, L, ids, arts))
            urls.append(article_url(L, a["slug"]))
        write(os.path.join(ROOT, sub, "index.html"), articles_list_page(L, arts))
        urls.append(f"{BASE}/{'en/' if L == 'en' else ''}guide/")
        print(f"articles {L}: {len(arts)}")

    sm = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    write(os.path.join(ROOT, "sitemap.xml"),
          f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
    write(os.path.join(ROOT, "robots.txt"), f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"pages: {len(resorts) * 2} resort pages + 2 lists, sitemap {len(urls)} urls, base {BASE}")


if __name__ == "__main__":
    main()
