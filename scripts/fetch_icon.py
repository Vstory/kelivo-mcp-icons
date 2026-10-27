#!/usr/bin/env python3
# SCRIPT_VERSION=1.0.0    # 脚本版本(无模板上游, 独立维护; 内容变更 +1)
"""抓取官方品牌图标到 icons/<name>.png。

用法:
  fetch_icon.py gitbook https://www.gitbook.com
  fetch_icon.py strava --appstore 426424760
  fetch_icon.py --batch list.tsv          # 每行 name<TAB>url 或 name<TAB>appstore:ID
  fetch_icon.py --selftest                # 不联网自检
  fetch_icon.py --version

候选顺序: 页面 <link rel=icon> → Web App Manifest 的 icons → 常见路径 →
App Store artwork(给了 --appstore 才走)。每张图都实下实测, 小于 180×180 或
大于 2MB 丢弃, 取尺寸最大者存 PNG。

输出契约: stdout 只放产物(图标路径/尺寸), 过程与被跳过的候选走 stderr。
默认不覆盖已有图标, 覆盖须显式 --force。
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


def log(msg):
    print(msg, file=sys.stderr, flush=True)


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


def iter_links(html):
    for tag in LINK_RE.findall(html):
        rel_m = REL_RE.search(tag)
        href_m = HREF_RE.search(tag)
        if not rel_m or not href_m:
            continue
        rel = rel_m.group(1).lower()
        href = href_m.group(1).strip()
        if not href or href.startswith("data:"):
            continue
        yield rel, href, declared_size(tag)


def html_candidates(base, html):
    out = []
    for rel, href, size in iter_links(html):
        if "icon" in rel:
            out.append((size, urllib.parse.urljoin(base, href), f"link[{rel}]"))
    return out


def manifest_urls(base, html):
    return [
        urllib.parse.urljoin(base, href)
        for rel, href, _ in iter_links(html)
        if "manifest" in rel
    ]


def manifest_candidates(url):
    try:
        raw, _ = get(url)
        man = json.loads(decode_maybe(raw))
    except Exception:
        return []
    out = []
    for icon in man.get("icons", []):
        src = icon.get("src")
        if not src:
            continue
        m = re.match(r"(\d+)", str(icon.get("sizes", "")))
        out.append((
            int(m.group(1)) if m else 0,
            urllib.parse.urljoin(url, src),
            "manifest",
        ))
    return out


def appstore_candidates(app_id, country):
    raw, _ = get(f"https://itunes.apple.com/lookup?id={app_id}&country={country}")
    results = json.loads(decode_maybe(raw)).get("results") or []
    if not results:
        return []
    art = results[0].get("artworkUrl512") or ""
    if not art:
        return []
    return [(512, re.sub(r"\.jpg$", ".png", art), "appstore"),
            (512, art, "appstore")]


def pick_best(loaded):
    best = None
    for size_hint, url, source, im, nbytes in loaded:
        side = min(im.size)
        if side < MIN_SIDE:
            log(f"  skip {url[:70]} ({im.size[0]}x{im.size[1]} < {MIN_SIDE})")
            continue
        if nbytes > MAX_BYTES:
            log(f"  skip {url[:70]} ({nbytes}B > 2MB)")
            continue
        score = side * 1000 + size_hint
        if best is None or score > best[0]:
            best = (score, im, source, url)
    return best


def download_candidates(candidates):
    loaded = []
    for size_hint, url, source in candidates:
        try:
            raw, final = get(url)
        except Exception as exc:
            log(f"  skip {url[:70]} ({type(exc).__name__})")
            continue
        try:
            im = Image.open(io.BytesIO(raw))
            im.load()
        except Exception:
            log(f"  skip {url[:70]} (not an image)")
            continue
        loaded.append((size_hint, final, source, im, len(raw)))
    return loaded


def collect(site, appstore_id, country):
    candidates = []
    if site:
        if not site.startswith("http"):
            site = "https://" + site
        try:
            raw, base = get(site)
            html = decode_maybe(raw)
            for murl in manifest_urls(base, html):
                candidates += manifest_candidates(murl)
            candidates += html_candidates(base, html)
            parsed = urllib.parse.urlparse(base)
            candidates += [
                (0, f"{parsed.scheme}://{parsed.netloc}{p}", "common") for p in COMMON
            ]
        except Exception as exc:
            log(f"  index unreachable: {site} ({type(exc).__name__})")
    if appstore_id:
        try:
            candidates += appstore_candidates(appstore_id, country)
        except Exception as exc:
            log(f"  appstore lookup failed ({type(exc).__name__})")
    candidates.sort(key=lambda c: -c[0])
    return candidates


def fetch(root, name, site=None, appstore_id=None, country="cn", force=False):
    out_path = os.path.join(root, "icons", f"{name}.png")
    if os.path.exists(out_path) and not force:
        log(f"exists: icons/{name}.png (use --force to overwrite)")
        return False

    candidates = collect(site, appstore_id, country)
    if not candidates:
        log(f"FAIL {name}: no candidates")
        return False

    log(f"== {name}: {len(candidates)} candidate(s)")
    best = pick_best(download_candidates(candidates))
    if not best:
        log(f"FAIL {name}: nothing usable")
        return False

    _, im, source, final = best
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    im.save(out_path, "PNG")
    log(f"   {source}: {final}")
    print(f"icons/{name}.png\t{im.size[0]}x{im.size[1]}\t{os.path.getsize(out_path)}B")
    return True


def selftest():
    failures = []

    def check(label, cond):
        log(("  ok   " if cond else "  FAIL ") + label)
        if not cond:
            failures.append(label)

    base = "https://example.com/dir/page"
    html = (
        '<link rel="apple-touch-icon" sizes="180x180" href="/a.png">'
        '<link rel="icon" href="rel/b.png">'
        '<link rel="manifest" href="/m.json">'
        '<link rel="stylesheet" href="/s.css">'
        '<link href="/no-rel.png">'
    )
    links = list(iter_links(html))
    check("iter_links 只取带 rel+href 的 link", len(links) == 4)
    check("sizes 解析取最小边", declared_size('<link sizes="180x181">') == 180)
    check("无 sizes 时为 0", declared_size('<link rel="icon">') == 0)

    cands = html_candidates(base, html)
    urls = [u for _, u, _ in cands]
    check("相对 href 解析为绝对地址", "https://example.com/dir/rel/b.png" in urls)
    check("根路径 href 解析正确", "https://example.com/a.png" in urls)
    check("非 icon 的 link 被排除", len(cands) == 2)
    check("manifest 单独收集",
          manifest_urls(base, html) == ["https://example.com/m.json"])

    small = Image.new("RGBA", (64, 64))
    big = Image.new("RGBA", (512, 512))
    loaded = [
        (0, "https://x/small.png", "link", small, 1000),
        (0, "https://x/big.png", "link", big, 1000),
        (0, "https://x/huge.png", "link", big, MAX_BYTES + 1),
    ]
    best = pick_best(loaded)
    check("小于 180 的被丢弃且不选中", best is not None and best[3] == "https://x/big.png")
    check("超过 2MB 的被丢弃", all(r[3] != "https://x/huge.png" for r in [best]))

    if failures:
        log(f"SELFTEST FAILED ({len(failures)}): " + "; ".join(failures))
        return 1
    log("SELFTEST OK")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?")
    ap.add_argument("site", nargs="?")
    ap.add_argument("--appstore")
    ap.add_argument("--country", default="cn")
    ap.add_argument("--batch")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()

    if args.version:
        print("fetch_icon.py 1.0.0")
        return 0
    if args.selftest:
        return selftest()
    if args.batch and args.name:
        log("--batch 与单个 name 互斥")
        return 2

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
            arg = job[1] if len(job) > 1 else ""
            if arg.startswith("appstore:"):
                ok += fetch(root, name, appstore_id=arg.split(":", 1)[1],
                            country=args.country, force=args.force)
            elif arg:
                ok += fetch(root, name, site=arg, force=args.force)
            else:
                ok += fetch(root, name, force=args.force)
        log(f"{ok}/{len(jobs)} fetched")
        return 0 if ok == len(jobs) else 1

    if not args.name:
        ap.error("需要 name（或用 --batch / --selftest / --version）")
    ok = fetch(root, args.name, site=args.site, appstore_id=args.appstore,
               country=args.country, force=args.force)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
