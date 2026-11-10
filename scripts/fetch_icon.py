#!/usr/bin/env python3
# SCRIPT_VERSION=1.1.1    # 脚本版本(无模板上游, 独立维护)
# 版本判级: 新增能力/参数 -> minor; 修缺陷/文案 -> patch; 改既有 CLI 或输出契约 -> major
"""抓取官方品牌图标到 icons/<name>.png。

用法:
  fetch_icon.py gitbook https://www.gitbook.com
  fetch_icon.py strava --appstore 426424760
  fetch_icon.py wkinfo --svg-mark https://example.com/logo.svg   # 横版 logo 取方形 mark
  fetch_icon.py --batch list.tsv          # 每行 name<TAB>url / name<TAB>appstore:ID / name<TAB>svg:url
  fetch_icon.py --selftest                # 不联网自检
  fetch_icon.py --version

候选顺序: 页面 <link rel=icon> → Web App Manifest 的 icons → 常见路径 →
App Store artwork(给了 --appstore 才走)。每张图都实下实测, 小于 180×180 或
大于 2MB 丢弃, 取尺寸最大者存 PNG。

--svg-mark: 站点只有横版带字 logo(SVG)时, 矢量渲染到 2048 高再自动裁出方形 mark,
缩到 --size(默认 1024)。全程无插值放大; 判定不出 mark 时用 --mark-box 手给裁框。

输出契约: stdout 只放产物(图标路径/尺寸), 过程与被跳过的候选走 stderr。
默认不覆盖已有图标, 覆盖须显式 --force。
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageChops, ImageDraw, ImageFilter

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
# 部分站点(如 upload.wikimedia.org)反而对浏览器式 UA 返 429, 对自述 UA 放行
ALT_UA = "KelivoIconBot/1.1 (+https://github.com/Vstory/kelivo-mcp-icons)"
UA_RETRY_STATUS = (403, 429)
MIN_SIDE = 180
MAX_BYTES = 2 * 1024 * 1024
SVG_RENDER_H = 2048          # 矢量渲染基准高度; 后续只缩小不放大
ALPHA_INK = 8                # alpha 大于此值算"有内容"
MARK_RATIO = 1.33            # 段宽高比在此内视为方形 mark
TALL_BLOCK_RATIO = 0.7       # 连通块高度达到整图 ink 高度的此比例才算 mark 主体(文字更矮)
COMMON = ("/apple-touch-icon.png", "/apple-touch-icon-precomposed.png", "/favicon.ico")
LINK_RE = re.compile(r"<link\b[^>]*>", re.I)
HREF_RE = re.compile(r"""\bhref\s*=\s*["']([^"']*)["']""", re.I)
REL_RE = re.compile(r"""\brel\s*=\s*["']([^"']*)["']""", re.I)
SIZES_RE = re.compile(r"""\bsizes\s*=\s*["']([^"']*)["']""", re.I)


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def get(url, timeout=25):
    '''取字节, UA 被拦(403/429)时换成自述 UA 重试一次。'''
    last = None
    for ua in (UA, ALT_UA):
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.geturl()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in UA_RETRY_STATUS:
                raise
            log(f"  {exc.code} with browser UA, retry as bot: {url[:70]}")
    raise last


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


def render_svg(data, height=SVG_RENDER_H):
    """矢量渲染到指定高度。优先 rsvg-convert, 回退 cairosvg, 两者都缺即报错。"""
    exe = shutil.which("rsvg-convert")
    if exe:
        proc = subprocess.run([exe, "-h", str(height), "-f", "png"], input=data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not proc.stdout:
            raise RuntimeError("rsvg-convert 失败: " + decode_maybe(proc.stderr)[:200])
        im = Image.open(io.BytesIO(proc.stdout))
        im.load()
        return im.convert("RGBA")
    try:
        import cairosvg
    except ImportError:
        raise RuntimeError("渲染 SVG 需要 rsvg-convert 或 cairosvg, 两者都没有")
    png = cairosvg.svg2png(bytestring=data, output_height=height)
    im = Image.open(io.BytesIO(png))
    im.load()
    return im.convert("RGBA")


def ink_mask(im, work_h=512):
    """二值 alpha 图 + 工作图→原图的坐标缩放比。降采样后再二值, 避免细笔画被平均掉。"""
    w, h = im.size
    mask = im.getchannel("A").point(lambda a: 255 if a > ALPHA_INK else 0)
    if h <= work_h:
        return mask, (1.0, 1.0)
    nw = max(1, round(w * work_h / h))
    mask = mask.resize((nw, work_h), Image.BOX).point(lambda v: 255 if v > ALPHA_INK else 0)
    return mask, (w / nw, h / work_h)


def components(mask):
    """不透明像素的连通块, 返回 [(bbox, strokes)], strokes=[(y, x0, x1)] 右闭。

    行行程 + 并查集, 纯 PIL 无额外依赖; strokes 用于把某一块单独抠出来。
    """
    nw, nh = mask.size
    data = mask.tobytes()
    parent = []
    runs = []
    prev = []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for y in range(nh):
        row = data[y * nw:(y + 1) * nw]
        cur = []
        x = 0
        while x < nw:
            if row[x]:
                start = x
                while x < nw and row[x]:
                    x += 1
                rid = len(runs)
                parent.append(rid)
                runs.append((y, start, x - 1))
                cur.append(rid)
            else:
                x += 1
        i = j = 0
        while i < len(prev) and j < len(cur):
            py, px0, px1 = runs[prev[i]]
            cy, cx0, cx1 = runs[cur[j]]
            if px1 < cx0:
                i += 1
            elif cx1 < px0:
                j += 1
            else:
                union(prev[i], cur[j])
                if px1 < cx1:
                    i += 1
                else:
                    j += 1
        prev = cur

    boxes = {}
    for rid, (y, x0, x1) in enumerate(runs):
        root = find(rid)
        old = boxes.get(root)
        if old:
            boxes[root] = ((min(old[0][0], x0), min(old[0][1], y),
                            max(old[0][2], x1), max(old[0][3], y)),
                           old[1] + [(y, x0, x1)])
        else:
            boxes[root] = ((x0, y, x1, y), [(y, x0, x1)])
    return [((b[0], b[1], b[2] + 1, b[3] + 1), strokes)
            for b, strokes in boxes.values()]


def ink_ratio(box):
    w, h = box[2] - box[0], box[3] - box[1]
    if w <= 0 or h <= 0:
        return 1e9
    return max(w, h) / min(w, h)


def mark_parts(im, work_h=512):
    """定位横版 logo 里的方形 mark。

    返回 (box_px, strokes, work_size): box_px 是原图像素坐标的 mark bbox,
    strokes 是 mark 那块连通块的行程(用于抠掉文字/® 等非 mark 像素),
    判定不出 mark 时返回 (None, None, None)。
    """
    mask, (sx, sy) = ink_mask(im, work_h)
    whole = mask.getbbox()
    if not whole:
        return None, None, None
    ink_h = whole[3] - whole[1]
    parts = components(mask)
    if not parts:
        return None, None, None
    tall = [p for p in parts if p[0][3] - p[0][1] >= TALL_BLOCK_RATIO * ink_h]
    pool = tall or parts
    box, strokes = max(pool, key=lambda p: ((p[0][2] - p[0][0]) * (p[0][3] - p[0][1]),
                                            -(p[0][0])))
    if ink_ratio(box) > MARK_RATIO:
        # 最大块与文字粘连成一条, 退化成左侧方窗; 此时没有可分离的 strokes
        window = (whole[0], whole[1], whole[0] + ink_h, whole[1] + ink_h)
        log(f"  最大块宽高比 {ink_ratio(box):.2f} 不像方形, 改用左侧方窗 {window}")
        return (tuple(round(v * s) for v, s in zip(window, (sx, sy, sx, sy))),
                None, None)
    return (tuple(round(v * s) for v, s in zip(box, (sx, sy, sx, sy))),
            strokes, mask.size)


def mark_bbox(im, work_h=512):
    return mark_parts(im, work_h)[0]


def clear_others(im, strokes, work_size):
    """把 strokes 之外的不透明像素抹成透明, 只留 mark 本体。"""
    keep = Image.new("L", work_size, 0)
    draw = ImageDraw.Draw(keep)
    for y, x0, x1 in strokes:
        draw.rectangle((x0, y, x1, y), fill=255)
    keep = keep.resize(im.size, Image.NEAREST).filter(ImageFilter.MaxFilter(3))
    out = im.copy()
    out.putalpha(ImageChops.multiply(im.getchannel("A"), keep))
    return out


def square_box(box, pad=0.03, limit=None):
    """把 bbox 扩成带留白的正方形裁框; 给了 limit(画布尺寸)时缩到画布内并保持居中。"""
    x0, y0, x1, y1 = box
    side = max(x1 - x0, y1 - y0) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if limit:
        w, h = limit
        side = min(side, w, h)
        left = min(max(cx - side / 2, 0), w - side)
        top = min(max(cy - side / 2, 0), h - side)
    else:
        left, top = cx - side / 2, cy - side / 2
    return (round(left), round(top), round(left + side), round(top + side))


def parse_box(text):
    """--mark-box: 渲染图像素坐标 x0,y0,x1,y1; 四个值都 ≤1 时按画布比例解释。"""
    try:
        vals = [float(v) for v in re.split(r"[,\s]+", text.strip()) if v]
    except ValueError:
        raise ValueError("--mark-box 需要四个数 x0,y0,x1,y1")
    if len(vals) != 4:
        raise ValueError("--mark-box 需要四个数 x0,y0,x1,y1")
    return vals


def resolve_mark(im, box_arg):
    """(box, strokes, work_size); 手给 --mark-box 时按所见即所得处理, 不擦除任何像素。"""
    if box_arg is None:
        return mark_parts(im)
    vals = box_arg
    if all(0 <= v <= 1 for v in vals):
        w, h = im.size
        return ((round(vals[0] * w), round(vals[1] * h),
                 round(vals[2] * w), round(vals[3] * h)), None, None)
    return (tuple(round(v) for v in vals), None, None)


def save_png(im, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    im.save(out_path, "PNG")


def report(name, im, out_path, source, final):
    log(f"   {source}: {final}")
    print(f"icons/{name}.png\t{im.size[0]}x{im.size[1]}\t{os.path.getsize(out_path)}B")


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
    save_png(im, out_path)
    report(name, im, out_path, source, final)
    return True


def fetch_svg_mark(root, name, src, size=1024, pad=0.03, force=False, box_arg=None):
    out_path = os.path.join(root, "icons", f"{name}.png")
    if os.path.exists(out_path) and not force:
        log(f"exists: icons/{name}.png (use --force to overwrite)")
        return False

    try:
        if src.startswith("http"):
            data, final = get(src)
        else:
            with open(src, "rb") as fh:
                data = fh.read()
            final = src
    except Exception as exc:
        log(f"FAIL {name}: 读不到 SVG 源 ({type(exc).__name__})")
        return False

    try:
        full = render_svg(data)
    except Exception as exc:
        log(f"FAIL {name}: {exc}")
        return False

    box, strokes, work_size = resolve_mark(full, box_arg)
    if not box:
        log(f"FAIL {name}: 定位不到方形 mark (整图 ink bbox={full.getchannel('A').getbbox()})")
        log("   用 --mark-box x0,y0,x1,y1 手给裁框(像素坐标, 或四个 ≤1 的比例)")
        return False
    log(f"== {name}: mark bbox={tuple(round(v) for v in box)} 于 {full.size[0]}x{full.size[1]} 渲染图")
    if strokes is not None:
        full = clear_others(full, strokes, work_size)
        log("   已抹掉 mark 之外的不透明像素(文字 / ® 等)")

    crop = square_box(box, pad, limit=full.size)
    if min(crop[2] - crop[0], crop[3] - crop[1]) < MIN_SIDE:
        log(f"FAIL {name}: 裁框只有 {crop[2]-crop[0]}x{crop[3]-crop[1]}")
        return False
    im = full.crop(crop)

    side = min(im.size)
    if side > size:
        im = im.resize((size, size), Image.LANCZOS)
    else:
        log(f"   裁出 {side}px 不超过目标 {size}px, 保持原分辨率不放大")
    if min(im.size) < MIN_SIDE:
        log(f"FAIL {name}: {im.size[0]}x{im.size[1]} < {MIN_SIDE}, 换更大的渲染高度")
        return False

    save_png(im, out_path)
    report(name, im, out_path, "svg-mark", final)
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

    two = Image.new("L", (60, 20), 0)
    two.paste(255, (0, 0, 10, 20))
    two.paste(255, (40, 0, 50, 20))
    check("components 分出两个不相连的块", len(components(two)) == 2)
    check("ink_ratio 对正方形为 1", ink_ratio((0, 0, 10, 10)) == 1)
    sq = square_box((0, 0, 100, 100), 0.03)
    check("square_box 留白后仍是正方形",
          (sq[2] - sq[0]) == (sq[3] - sq[1]) and sq[2] - sq[0] > 100)
    tight = square_box((48, 48, 2000, 2000), 0.03, limit=(2048, 2048))
    check("square_box 遇画布不足时仍正方形且在画布内",
          (tight[2] - tight[0]) == (tight[3] - tight[1])
          and tight[0] >= 0 and tight[1] >= 0
          and tight[2] <= 2048 and tight[3] <= 2048)
    check("parse_box 收四个数",
          parse_box("1 2 3 4") == [1.0, 2.0, 3.0, 4.0])
    check("UA 被拦时有第二个 UA 可换", UA != ALT_UA and 429 in UA_RETRY_STATUS)

    # 横版 logo: 左侧 100×100 方块 + 右侧细竖条(模拟文字), mark 应识别为左边那块
    logo = Image.new("RGBA", (320, 100), (0, 0, 0, 0))
    logo.paste((200, 30, 40, 255), (0, 0, 100, 100))
    for x in range(140, 300, 20):
        logo.paste((60, 60, 60, 255), (x, 20, x + 6, 80))
    box = mark_bbox(logo)
    check("mark_bbox 认出左侧方形 mark",
          box is not None and abs(box[0]) <= 2 and abs(box[2] - 100) <= 2)
    check("mark_bbox 不吃右侧文字", box is not None and box[2] <= 105)

    # ® 这类矮附属符号与主干不相连时, 不能算进 mark
    with_reg = Image.new("RGBA", (320, 100), (0, 0, 0, 0))
    with_reg.paste((200, 30, 40, 255), (0, 0, 100, 100))
    with_reg.paste((120, 120, 120, 255), (106, 70, 130, 96))
    reg_box = mark_bbox(with_reg)
    check("分离的矮附属符号被排除",
          reg_box is not None and reg_box[2] <= 105)

    reg_box2, reg_strokes, reg_work = mark_parts(with_reg)
    cleaned = clear_others(with_reg, reg_strokes, reg_work)
    check("clear_others 把非 mark 像素抹成透明",
          cleaned.getpixel((118, 83))[3] == 0 and cleaned.getpixel((50, 50))[3] == 255)

    # 附属符号与主干像素相接时无法分离, 至少要退化成不歪的裁框(留给 --mark-box 兜底)
    welded = Image.new("RGBA", (320, 100), (0, 0, 0, 0))
    welded.paste((200, 30, 40, 255), (0, 0, 100, 100))
    welded.paste((120, 120, 120, 255), (100, 70, 130, 100))
    welded_box = mark_bbox(welded)
    check("焊接的附属符号不导致报错且裁框近方形",
          welded_box is not None and ink_ratio(welded_box) <= MARK_RATIO)

    # 粘连场景: 方块与竖条无空隙, 首段过宽时应退化成左侧方窗
    stuck = Image.new("RGBA", (320, 100), (0, 0, 0, 0))
    stuck.paste((200, 30, 40, 255), (0, 0, 100, 100))
    stuck.paste((60, 60, 60, 255), (100, 20, 300, 80))
    stuck_box = mark_bbox(stuck)
    check("粘连时退化到左侧方窗",
          stuck_box is not None and stuck_box[2] - stuck_box[0] <= 110)

    renderer = shutil.which("rsvg-convert")
    if not renderer:
        try:
            import cairosvg  # noqa: F401
            renderer = "cairosvg"
        except ImportError:
            renderer = None
    if renderer:
        tiny = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            b'<rect width="10" height="10" fill="#c00"/></svg>'
        )
        try:
            im = render_svg(tiny, height=64)
            check(f"render_svg 可用({renderer})且按高度渲染", im.size[1] == 64)
        except Exception as exc:
            check(f"render_svg 渲染内联 SVG ({exc})", False)
    else:
        log("  skip render_svg: 没有 rsvg-convert / cairosvg(不算失败)")

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
    ap.add_argument("--svg-mark", help="横版 logo 的 SVG(URL 或本地路径), 自动裁出方形 mark")
    ap.add_argument("--size", type=int, default=1024, help="--svg-mark 的输出边长, 默认 1024")
    ap.add_argument("--pad", type=float, default=0.03, help="--svg-mark 的裁框留白比例, 默认 0.03")
    ap.add_argument("--mark-box", help="--svg-mark 手给裁框 x0,y0,x1,y1(像素或 ≤1 的比例)")
    ap.add_argument("--batch")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()

    if args.version:
        print("fetch_icon.py 1.1.1")
        return 0
    if args.selftest:
        return selftest()
    if args.batch and args.name:
        log("--batch 与单个 name 互斥")
        return 2
    if args.svg_mark and args.site:
        log("--svg-mark 与 site 位置参数互斥(只给一个图源)")
        return 2

    try:
        box_arg = parse_box(args.mark_box) if args.mark_box else None
    except ValueError as exc:
        log(str(exc))
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
            elif arg.startswith("svg:"):
                ok += fetch_svg_mark(root, name, arg.split(":", 1)[1], size=args.size,
                                     pad=args.pad, force=args.force, box_arg=box_arg)
            elif arg:
                ok += fetch(root, name, site=arg, force=args.force)
            else:
                ok += fetch(root, name, force=args.force)
        log(f"{ok}/{len(jobs)} fetched")
        return 0 if ok == len(jobs) else 1

    if not args.name:
        ap.error("需要 name（或用 --batch / --selftest / --version）")
    if args.svg_mark:
        ok = fetch_svg_mark(root, args.name, args.svg_mark, size=args.size,
                            pad=args.pad, force=args.force, box_arg=box_arg)
    else:
        ok = fetch(root, args.name, site=args.site, appstore_id=args.appstore,
                   country=args.country, force=args.force)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
