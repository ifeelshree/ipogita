#!/usr/bin/env python3
"""IPOgita collector.

Reads ipowatch.in's GMP page and IPO news page, merges the result into
site/data.json and keeps a running day-wise GMP history for each IPO.
Runs from GitHub Actions every ~30 minutes. Needs: requests, beautifulsoup4.
"""
import json, re, sys, datetime as dt
from pathlib import Path
import requests
from bs4 import BeautifulSoup

GMP_URL = "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/"
NEWS_URL = "https://ipowatch.in/ipo-news/"
DATA = Path(__file__).resolve().parent.parent / "site" / "data.json"
HEADERS = {"User-Agent": "IPOgita personal dashboard (reads 2 pages every 30 min)"}
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def now_ist():
    return dt.datetime.now(IST)


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clean_name(raw):
    n = re.sub(r"\s+", " ", raw).strip()
    n = re.sub(r"\b(IPO|GMP|Today|SME)\b", "", n, flags=re.I)
    n = re.sub(r"[\(\)\[\]]", "", n)
    return re.sub(r"\s+", " ", n).strip(" -–|")


def parse_date(text, ref):
    """Find a day + month name in text, e.g. '29 Oct', 'Oct 29, 2026', '29-Oct-2026'."""
    t = text.lower()
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?[\s\-/,]*([a-z]{3})[a-z]*[\s\-/,]*(\d{4})?", t)
    if m and m.group(2) in MONTHS:
        day, mon, yr = int(m.group(1)), MONTHS[m.group(2)], m.group(3)
    else:
        m = re.search(r"([a-z]{3})[a-z]*\.?[\s\-/]*(\d{1,2})(?:st|nd|rd|th)?(?:[\s,\-/]*(\d{4}))?", t)
        if not (m and m.group(1) in MONTHS):
            return None
        day, mon, yr = int(m.group(2)), MONTHS[m.group(1)], m.group(3)
    year = int(yr) if yr else ref.year
    try:
        d = dt.date(year, mon, day)
    except ValueError:
        return None
    if not yr and (d - ref.date()).days > 200:   # 'Jan' seen in December etc.
        d = d.replace(year=year - 1)
    elif not yr and (ref.date() - d).days > 200:
        d = d.replace(year=year + 1)
    return d.isoformat()


def first_number(text):
    m = re.search(r"-?\d[\d,]*\.?\d*", text.replace("₹", ""))
    return float(m.group(0).replace(",", "")) if m else None


def parse_band(text):
    nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", text.replace("₹", ""))]
    if not nums:
        return None, None
    hi = max(nums[:2])
    lo = min(nums[:2])
    fmt = lambda v: f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"
    return (f"₹{fmt(lo)}–{fmt(hi)}" if lo != hi else f"₹{fmt(hi)}"), hi


def heading_before(table):
    h = table.find_previous(["h1", "h2", "h3", "h4"])
    return h.get_text(" ", strip=True).lower() if h else ""


def find_cols(headers):
    cols = {}
    for i, h in enumerate(headers):
        h = h.lower()
        if "name" not in cols and any(k in h for k in ("ipo", "company", "name")) and "gmp" not in h and "price" not in h:
            cols["name"] = i
        elif "gmp" in h and "est" not in h and "gmp" not in cols:
            cols["gmp"] = i
        elif "price" in h and "est" not in h and "listing" not in h and "band" not in cols:
            cols["band"] = i
        elif "open" in h and "open" not in cols:
            cols["open"] = i
        elif "close" in h and "close" not in cols:
            cols["close"] = i
        elif "size" in h and "size" not in cols:
            cols["size"] = i
    return cols


def scrape_gmp():
    soup = get(GMP_URL)
    ref = now_ist()
    out = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [c.get_text(" ", strip=True) for c in rows[0].find_all(["th", "td"])]
        cols = find_cols(headers)
        if "name" not in cols or "gmp" not in cols:
            continue
        sme_table = "sme" in heading_before(table)
        for tr in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) <= max(cols.values()):
                continue
            raw = cells[cols["name"]]
            name = clean_name(raw)
            if not name or len(name) < 3:
                continue
            gtxt = cells[cols["gmp"]]
            gmp = first_number(gtxt) if re.search(r"\d", gtxt) else None
            band, hi = parse_band(cells[cols["band"]]) if "band" in cols else (None, None)
            rec = {
                "id": slug(name), "name": name,
                "seg": "SME" if (sme_table or "sme" in raw.lower()) else "Mainboard",
                "open": parse_date(cells[cols["open"]], ref) if "open" in cols else None,
                "close": parse_date(cells[cols["close"]], ref) if "close" in cols else None,
                "band": band, "hi": hi,
                "size": first_number(cells[cols["size"]]) if "size" in cols else None,
                "gmp": gmp,
            }
            out.append(rec)
    return out


def scrape_news(limit=8):
    soup = get(NEWS_URL)
    items, seen = [], set()
    for h in soup.find_all(["h2", "h3"]):
        a = h.find("a", href=True)
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        href = a["href"]
        if not href.startswith("https://ipowatch.in/") or title in seen or len(title) < 15:
            continue
        seen.add(title)
        d = None
        art = h.find_parent(["article", "div"])
        if art:
            t = art.find("time")
            if t:
                d = (t.get("datetime") or t.get_text())[:10]
                if not re.match(r"\d{4}-\d{2}-\d{2}$", d):
                    d = parse_date(t.get_text(), now_ist())
        items.append({"t": title, "u": href, "d": d})
        if len(items) >= limit:
            break
    return items


def merge(old, scraped, today):
    by_id = {r["id"]: r for r in old["ipos"]}
    for s in scraped:
        r = by_id.get(s["id"])
        if r is None:
            if not (s["open"] and s["close"]):
                continue                         # cannot place an IPO without dates
            r = {"id": s["id"], "name": s["name"], "seg": s["seg"], "open": s["open"], "close": s["close"],
                 "band": s["band"], "hi": s["hi"], "size": s["size"], "gmp": s["gmp"], "h": [], "extra": None}
            by_id[s["id"]] = r
        for k in ("open", "close", "band", "hi", "size"):
            if s.get(k) is not None:
                r[k] = s[k]
        if s["seg"] == "SME" and r["seg"] == "Mainboard":
            r["seg"] = "SME"
        if s["gmp"] is not None:
            r["gmp"] = int(s["gmp"]) if s["gmp"] == int(s["gmp"]) else s["gmp"]
            hist = r.setdefault("h", [])
            if hist and hist[-1][0] == today:
                hist[-1][1] = r["gmp"]            # latest reading of the day wins
            else:
                hist.append([today, r["gmp"]])
    # drop issues that closed more than 21 days ago
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=21)).isoformat()
    ipos = [r for r in by_id.values() if r["close"] >= cutoff]
    ipos.sort(key=lambda r: (r["close"], r["name"]))
    old["ipos"] = ipos
    return old


def main():
    data = json.loads(DATA.read_text(encoding="utf8"))
    ref = now_ist()
    scraped = scrape_gmp()
    if len(scraped) < 3:
        print(f"Only {len(scraped)} IPO rows found on the GMP page; layout may have changed. Not updating.")
        sys.exit(1)
    data = merge(data, scraped, ref.date().isoformat())
    try:
        news = scrape_news()
        if news:
            data["news"] = news
    except Exception as e:                        # news is optional
        print("News fetch failed, keeping old headlines:", e)
    data["updated"] = ref.isoformat(timespec="seconds")
    new_text = json.dumps(data, ensure_ascii=False, indent=1)
    DATA.write_text(new_text + "\n", encoding="utf8")
    print(f"OK: {len(scraped)} rows scraped, {len(data['ipos'])} IPOs stored.")


if __name__ == "__main__":
    main()
