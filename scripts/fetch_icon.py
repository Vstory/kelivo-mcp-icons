#!/usr/bin/env python3
"""Fetch official brand icons into icons/<name>.png.

Usage:
  fetch_icon.py gitbook https://www.gitbook.com
  fetch_icon.py strava --appstore 426424760
  fetch_icon.py --batch list.tsv          # lines: name<TAB>url

Sources are tried in order: <link rel=icon> tags, web app manifest icons,
common icon paths, then the App Store artwork when --appstore is given.
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from PIL import Image

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
MIN_SIDE = 180
MAX_BYTES = 2 * 1024 * 1024
COMMON = ("/apple-touch-icon.png", "/apple-touch-icon-precomposed.png", "/favicon.ico")
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
HREF_RE = re.compile(r"""\bhref\s*=\s*["']([^"']*)["']""", re.I)
REL_RE = re.compile(r"""\brel\s*=\s*["']([^"']*)["']""", re.I)
SIZES_RE = re.compile(r"""\bsizes\s*=\s*["']([^"']*)["']""", re.I)


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.geturl()


def decode_maybe(data):
    try:
        return data.decode("utf-8", "ignore")
    except Exception:
        return ""


def declared_size(tag):
    m = SIZES_RE.search(tag)
    if not m:
        return 0
    best = 0
    for part in m.group(1).lower().split():
        if "x" in part:
            try:
                w, h = part.split("x", 1)
                best = max(best, min(int(w), int(h)))
            except ValueError:
                pass
    return best


def html_candidates(base, html):
    out = []
    for tag in LINK_RE.findall(html):
        rel_m = REL_RE.search(tag)
        href_m = HREF_RE.search(tag)
        if not rel_m or not href_m:
            continue
        rel = rel_m.group(1).lower()
        if "icon" not in rel:
            continue
        href = href_m.group(1).strip()
        if not href or href.startswith("data:"):
            continue
        out.append((declared_size(tag), urllib.parse.urljoin(base, href), f"link[{rel}]"))
    return out


def manifest_candidates(base, html):
    out = []
    for tag in LINK_RE.findall(html):
        rel_m = REL_RE.search(tag)
        href_m = HREF_RE.search(tag)
        if not rel_m or not href_m or "manifest" not in rel_m.group(1).lower():
            continue
        url = urllib.parse.urljoin(base, href_m.group(1).strip())
        try:
            raw, _ = get(url)
            man = json.loads(decode_maybe(raw))
        except Exception:
            continue
        for icon in man.get("icons", []):
            src = icon.get("src")
            if not src:
                continue
            size = 0
            m = re.match(r"(\d+)", str(icon.get("sizes", "")))
            if m:
                size = int(m.group(1))
            out.append((size, urllib.parse.urljoin(url, src), "manifest"))
    return out


def appstore_candidates(app_id, country):
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
    raw, _ = get(url)
    data = json.loads(decode_maybe(raw))
    results = data.get("results") or []
    if not results:
        return []
    art = results[0].get("artworkUrl512") or ""
    if not art:
        return []
    png = re.sub(r"\.jpg$", ".png", art)
    return [(512, png, "appstore"), (512, art, "appstore")]


def try_download(candidates):
    best = None
    for size_hint, url, source in candidates:
        try:
            raw, final = get(url)
        except Exception as exc:
            print(f"  skip {url[:70]} ({type(exc).__name__})")
            continue
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
        except Exception:
            print(f"  skip {url[:70]} (not an image)")
            continue
        side = min(im.size)
        if side < MIN_SIDE:
            print(f"  skip {url[:70]} ({im.size[0]}x{im.size[1]} < {MIN_SIDE})")
            continue
        if len(raw) > MAX_BYTES:
            print(f"  skip {url[:70]} ({len(raw)}B > 2MB)")
            continue
        score = side * 1000 + size_hint
        if best is None or score > best[0]:
            best = (score, im, source, final)
    return best



def fetch(root, name, site=None, appstore_id=None, country="cn", force=False):
    out_path = os.path.join(root, "icons", f"{name}.png")
    if os.path.exists(out_path) and not force:
        print(f"exists: icons/{name}.png (use --force to overwrite)")
        return False

    candidates = []
    if site:
        if not site.startswith("http"):
            site = "https://" + site
        try:
            raw, base = get(site)
            html = decode_maybe(raw)
            candidates += html_candidates(base, html)
            candidates += manifest_candidates(base, html)
            parsed = urllib.parse.urlparse(base)
            for p in COMMON:
                candidates.append((0, f"{parsed.scheme}://{parsed.netloc}{p}", "common"))
        except Exception as exc:
            print(f"  index unreachable: {site} ({type(exc).__name__})")
    if appstore_id:
        try:
            candidates += appstore_candidates(appstore_id, country)
        except Exception as exc:
            print(f"  appstore lookup failed ({type(exc).__name__})")

    if not candidates:
        print(f"FAIL {name}: no candidates")
        return False

    candidates.sort(key=lambda c: -c[0])
    print(f"== {name}: {len(candidates)} candidate(s)")
    best = try_download(candidates)
    if not best:
        print(f"FAIL {name}: nothing usable")
        return False

    _, im, source, final = best
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    im.save(out_path, "PNG")
    size = os.path.getsize(out_path)
    print(f"OK {name}: {im.size[0]}x{im.size[1]} {im.mode} {size}B via {source}")
    print(f"   src: {final}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?")
    ap.add_argument("site", nargs="?")
    ap.add_argument("--appstore")
    ap.add_argument("--country", default="cn")
    ap.add_argument("--batch")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if args.batch:
        jobs = []
        for line in open(args.batch, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("\t") if p.strip()]
            if parts:
                jobs.append(parts)
        ok = 0
        for job in jobs:
            name = job[0]
            if len(job) > 1 and job[1].startswith("appstore:"):
                ok += fetch(root, name, appstore_id=job[1].split(":", 1)[1],
                            country=args.country, force=args.force)
            elif len(job) > 1:
                ok += fetch(root, name, site=job[1], force=args.force)
            else:
                ok += fetch(root, name, appstore_id=None, force=args.force)
        print(f"\n{ok}/{len(jobs)} fetched")
        return 0 if ok == len(jobs) else 1

    if not args.name:
        ap.error("name required unless --batch")
    ok = fetch(root, args.name, site=args.site, appstore_id=args.appstore,
               country=args.country, force=args.force)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
