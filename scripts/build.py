"""소현생정 링크페이지 데이터 수집기.

네이버 블로그 RSS에서 카테고리별 최신 글을 가져오고, 각 글 본문에 들어 있는
제휴 링크(쿠팡 파트너스·여기어때·마이리얼트립 등)를 찾아 data/feed.json에 저장한다.
GitHub Actions가 3시간마다 실행한다. 로컬 실행: python scripts/build.py
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
DATA = ROOT / "data"
THUMBS = ROOT / "assets" / "thumbs"
CACHE_FILE = DATA / "affiliates-cache.json"
FEED_FILE = DATA / "feed.json"
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; sohyunguide-linkpage/1.0; +https://revi404.github.io/sohyunguide/)"
RECHECK_DAYS = 14  # 최근 글은 제휴 링크를 나중에 추가할 수 있어 매번 다시 확인

BLOG_ID = CONFIG["blog"]["id"]


def fetch(url: str, retries: int = 2) -> bytes:
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": f"https://blog.naver.com/{BLOG_ID}"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise last  # type: ignore[misc]


def save_thumb(url: str) -> str:
    """원격 이미지를 assets/thumbs에 저장하고 상대경로를 돌려준다(외부 핫링크 차단 대비)."""
    if not url:
        return ""
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".jpg"
    dest = THUMBS / name
    if not dest.exists():
        try:
            raw = fetch(url)
            try:
                from PIL import Image  # 선택: 있으면 400px로 줄여 용량 절감

                im = Image.open(io.BytesIO(raw)).convert("RGB")
                im.thumbnail((400, 400))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=82, optimize=True)
                raw = buf.getvalue()
            except Exception:  # noqa: BLE001
                pass
            THUMBS.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        except Exception as e:  # noqa: BLE001
            print(f"  ! 썸네일 실패 {url[:80]}: {e}", file=sys.stderr)
            return ""
    return f"assets/thumbs/{name}"


# ---------- RSS ----------
def read_rss() -> tuple[dict, list[dict]]:
    root = ET.fromstring(fetch(f"https://rss.blog.naver.com/{BLOG_ID}.xml"))
    ch = root.find("channel")
    info = {
        "title": (ch.findtext("title") or "").strip(),
        "image": (ch.findtext("image/url") or "").split("?")[0],
    }
    posts = []
    for it in ch.findall("item"):
        guid = (it.findtext("guid") or "").strip()
        m = re.search(r"/(\d+)$", guid)
        if not m:
            continue
        desc = it.findtext("description") or ""
        img = re.search(r'<img src="([^"]+)"', desc)
        summary = re.sub(r"<[^>]+>", "", desc)
        summary = re.sub(r"\s+", " ", html.unescape(summary)).strip()
        pub = parsedate_to_datetime(it.findtext("pubDate"))
        posts.append({
            "logNo": m.group(1),
            "title": (it.findtext("title") or "").strip(),
            "category": (it.findtext("category") or "").strip(),
            "url": f"https://blog.naver.com/{BLOG_ID}/{m.group(1)}",
            "date": pub.astimezone(KST).strftime("%Y-%m-%d"),
            "ts": pub.timestamp(),
            "summary": summary[:90],
            "thumbSrc": img.group(1) if img else "",
        })
    return info, posts


# ---------- 본문 제휴 링크 ----------
def partner_of(url: str) -> str | None:
    low = url.lower()
    for rule in CONFIG["affiliate"]["rules"]:
        if any(k.lower() in low for k in rule["match"]):
            return rule["partner"]
    return None


def clean_title(t: str, partner: str) -> str:
    t = html.unescape(re.sub(r"\s+", " ", t)).strip()
    t = re.sub(r"^[^\w가-힣\[(]+", "", t)  # 앞쪽 👉·▶ 같은 장식 제거
    t = re.sub(r"\s*\|\s*(쿠팡|여기어때|마이리얼트립|MyRealTrip).*$", "", t, flags=re.I)
    if partner == "쿠팡":
        t = re.sub(r"\s+-\s+[^-]{1,20}$", "", t)  # "... - 건조기" 같은 끝 카테고리 제거
    return t


def decode_thumb(src: str) -> str:
    src = html.unescape(src)
    q = urllib.parse.urlparse(src)
    if "dthumb-phinf" in q.netloc:
        inner = urllib.parse.parse_qs(q.query).get("src", [""])[0].strip('"')
        if inner:
            return inner
    return src


def extract_affiliates(post: dict) -> list[dict]:
    url = f"https://blog.naver.com/PostView.naver?blogId={BLOG_ID}&logNo={post['logNo']}&redirect=Dlog&widgetTypeCall=true&directAccess=false"
    page = fetch(url).decode("utf-8", "replace")
    found: dict[str, dict] = {}

    # 1) 링크 카드(OG 링크) — 제목·썸네일 포함
    for block in re.findall(r'<div class="se-component se-oglink.*?</script>', page, re.S):
        link = re.search(r'<a href="([^"]+)"', block)
        if not link:
            continue
        href = html.unescape(link.group(1))
        p = partner_of(href)
        if not p:
            continue
        title = re.search(r'class="se-oglink-title">(.*?)</strong>', block, re.S)
        img = re.search(r'<img src="([^"]+)"', block)
        found.setdefault(href, {
            "url": href, "partner": p,
            "title": clean_title(title.group(1), p) if title else "",
            "thumbSrc": decode_thumb(img.group(1)) if img else "",
        })

    # 2) 본문 텍스트 링크
    for m in re.finditer(r'<a\s[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', page, re.S):
        href = html.unescape(m.group(1))
        p = partner_of(href)
        if not p or href in found:
            continue
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if text.startswith("http"):
            text = ""
        found[href] = {"url": href, "partner": p, "title": clean_title(text, p), "thumbSrc": ""}

    items = []
    for it in found.values():
        it.update({
            "title": it["title"] or post["title"],
            "thumbSrc": it["thumbSrc"] or post["thumbSrc"],
            "postTitle": post["title"],
            "postUrl": post["url"],
            "category": post["category"],
            "date": post["date"],
            "ts": post["ts"],
        })
        items.append(it)
    return items


def main() -> None:
    DATA.mkdir(exist_ok=True)
    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}
    info, posts = read_rss()
    print(f"RSS: {len(posts)}개 글")

    # 프로필 사진(블로그 프로필) — config에 별도 사진이 없을 때 사용
    prof = ROOT / "assets" / "profile.jpg"
    if info["image"] and not prof.exists():
        try:
            prof.write_bytes(fetch(info["image"]))
        except Exception as e:  # noqa: BLE001
            print(f"  ! 프로필 사진 실패: {e}", file=sys.stderr)

    now = time.time()
    for p in posts:
        c = cache.get(p["logNo"])
        fresh = now - p["ts"] < RECHECK_DAYS * 86400
        if c is None or fresh:
            try:
                c = {"checked": int(now), "items": extract_affiliates(p)}
                cache[p["logNo"]] = c
                print(f"  {p['logNo']} 제휴 {len(c['items'])}개 · {p['title'][:30]}")
            except Exception as e:  # noqa: BLE001
                print(f"  ! 본문 확인 실패 {p['logNo']}: {e}", file=sys.stderr)
            time.sleep(0.6)

    # 카테고리별 최신 글
    per = CONFIG["blog"]["perCategory"]
    by_cat: dict[str, list] = {}
    for p in sorted(posts, key=lambda x: -x["ts"]):
        lst = by_cat.setdefault(p["category"], [])
        if len(lst) < per:
            lst.append({k: p[k] for k in ("title", "url", "date", "summary", "category")} | {"thumb": save_thumb(p["thumbSrc"])})

    # 제휴 링크: RSS에서 빠진 예전 글 것도 캐시로 유지
    hidden = set(CONFIG["affiliate"].get("hidden", []))
    seen, affs = set(), []
    for c in sorted(cache.values(), key=lambda c: -(c["items"][0]["ts"] if c["items"] else 0)):
        for it in c["items"]:
            if it["url"] in seen or it["url"] in hidden:
                continue
            seen.add(it["url"])
            affs.append({k: it[k] for k in ("title", "url", "partner", "postTitle", "postUrl", "category", "date")}
                        | {"thumb": save_thumb(it["thumbSrc"])})
    affs.sort(key=lambda a: a["date"], reverse=True)

    feed = {"updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "posts": by_cat, "affiliates": affs}
    FEED_FILE.write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding="utf-8")
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    # 쓰지 않는 썸네일 정리
    used = {Path(x["thumb"]).name for v in by_cat.values() for x in v if x["thumb"]} | {Path(a["thumb"]).name for a in affs if a["thumb"]}
    used |= {Path(p.get("image", "")).name for p in CONFIG.get("products", [])}
    for f in THUMBS.glob("*.jpg"):
        if f.name not in used:
            f.unlink()
    print(f"완료: 카테고리 {len(by_cat)}개, 제휴 링크 {len(affs)}개")


if __name__ == "__main__":
    main()
