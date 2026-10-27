# AGENTS.md

本仓库存放 Kelivo MCP 服务器的自定义图标，一个服务一个文件，`icons/<name>.png`。加图标、换图标前先读完本文件。

## 仓库约束

- **必须 public**：Kelivo 下载图标时**不转发任何凭据、不带 cookie**（`McpIconCache`），私有仓库的 raw 地址拿不到内容。
- **地址只用官方 raw 或 jsDelivr**，不加查询参数：

  ```
  https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/<name>.png
  https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/<name>.png
  ```

- **文件名即服务名，且一经发布不得变更**：小写、单词间连字符（`mt-manager`、`microsoft-learn`）。改名等于换地址，所有已填过的链接一起失效。

## Kelivo 怎么加载图标

这些约束直接来自客户端实现（`lib/core/services/mcp/mcp_icon_cache.dart`），是下面所有规矩的来源，改之前先看清楚：

| 行为 | 后果 |
|------|------|
| 磁盘缓存文件名 = `mcp_<sha256(URL)>.<svg\|png\|img>`，**无 TTL、无内容校验**，文件在就直接用 | 同一个 URL 换了图，客户端永远吃旧图 |
| 单文件上限 **2 MB**，超出直接判失败 | 图标不要放原尺寸大图 |
| 单次请求 **8 秒**超时 | 别指向响应慢的 CDN |
| **只跟随同源重定向**，跨域 302 抛 `Cross-origin icon redirect` | 会跳到别的域名的地址必须先在本地落盘再进仓库，见「踩过的坑」 |
| 不转发 MCP 的认证头、不带 cookie | 需要 token 的图床不能用 |
| 没填图标时回退到 Server URL 的 `/favicon.ico` | 列表里显示的是域名 favicon，不是「没有图标」 |

## 硬约束

| 项 | 要求 | 原因 |
|----|------|------|
| 尺寸 | 边长 ≥ 180 | 头像框 36dp，5 倍屏 180px；小于这个数会被插值拉糊 |
| 格式 | PNG；SVG 也能用（客户端认 `<svg`） | 有官方 SVG 且是方形 mark 时才用 |
| 背景 | 透明优先；满画布实底也能用 | 深色主题下透明底最稳 |
| 处理 | **原样保存**，不重绘、不裁切、不加圆角、不加底色 | 裁圆角会在方框里留一圈底色；重绘必然走形 |
| 体积 | ≤ 2 MB | 见上表 |

## 抓取顺序

按这个顺序找，前一步拿到合格的就停：

1. `<域名>/apple-touch-icon.png` —— 直连试，多数站点直接有。
2. 首页 `<link rel="apple-touch-icon">` / `<link rel="apple-touch-icon-precomposed">` 指向的地址。
3. 首页 `<link rel="manifest">` 的 `icons` 数组里尺寸 ≥180 的那张。
4. 官方品牌资源库（如 `huggingface.co/datasets/huggingface/brand-assets`）。
5. 应用商店接口：`https://itunes.apple.com/lookup?bundleId=<包名>&country=cn` 的 `artworkUrl512`。
6. App 源码仓库里的启动图标（Android：`app/src/main/res/mipmap-xxxhdpi/ic_launcher.png`）。
7. 官方 GitHub 组织头像：`https://github.com/<org>.png?size=512`。
8. 最后才用 favicon 服务（Google `s2/favicons?domain=<域>&sz=256`），**必须交叉验证**（见坑表）。

**不要做的**：

- 不要拿 `favicon.ico` 放大 —— 里面只有 16/32 px。
- 不要用横版带字 logo（`logo.svg`、`xxx-logo.png` 这类）—— 当头像会缩成一团看不清。
- 不要用图标站、Logo 聚合站、AI 重绘的图 —— 与品牌方原图有出入。

## 抓图工具

`apple-touch-icon` 类直连探测：

```bash
curl -sI -m 15 -A "Mozilla/5.0" "https://<域名>/apple-touch-icon.png" \
  | tr -d '\r' | awk '/^HTTP/{c=$2} /[Cc]ontent-[Tt]ype/{t=$2} /[Cc]ontent-[Ll]ength/{l=$2} END{print c,t,l}'
```

看清站点自己声明了哪些图标：

```bash
curl -sL -m 20 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130" https://<域名>/ -o page.html
grep -Eoi '<link[^>]*(icon|manifest)[^>]*>' page.html
```

下载后一律先量尺寸，不要凭 `Content-Length` 猜：

```bash
python3 -c "from PIL import Image;i=Image.open('x.png');print(i.size,i.mode,i.format)"
```

## 踩过的坑

| 域名 / 服务 | 现象 | 最终做法 |
|---|---|---|
| `amap.com` | Next.js SSR，整个 head 只有 `<link rel="icon" href="/ssr/img/favicon.ico">`；`apple-touch-icon.png`、`manifest.json` 全 302 回首页；官网唯一高清图是 `a.amap.com/pc/static/img/logo.png`（341×80 横版「图标+四字」） | 走应用商店接口：`lookup?bundleId=com.autonavi.amap` → `artworkUrl512`，把结尾 `512x512bb.jpg` 改成 `.png` 就是无损；`1024x1024bb.png` 也支持 |
| `mzstatic.com`（Apple CDN） | 默认给的 `512x512bb.jpg` 是有损 JPEG，直接不带尺寸参数访问会 404 | 只改结尾扩展名 `.jpg` → `.png`，尺寸前缀保留 |
| `github.com` | `apple-touch-icon-180x180.png` 是白底黑猫（满画布实底）；`fluidicon.png`（`rel="fluid-icon"`）是 512 透明底深色圆盘 + 白猫 | 用 `fluidicon.png`：更大、透明，不会被头像框整块盖住 |
| `cloudflare.com` | 站点 `favicon.ico` 只有 99×96；`logo.svg` 是 341×156 横版「云 + 字」；`apple-touch-icon` 全 404 | 用组织头像 `github.com/cloudflare.png?size=512`（400×400 橙云 mark）。**注意这个地址会 302 到 `avatars.githubusercontent.com`，跨域，直接填进 Kelivo 会被拒** —— 必须先落盘再进本仓库 |
| `exa.ai` | 官方只提供 148×148 的方形 mark（`apple-touch-icon` 404，`exa-logo-blue.svg` 是 413×129 横版带字） | `https://exa.imgix.net/logo_cream.png?w=1024` 让 imgix 从源图渲染到 1024。**本质仍是插值放大**，136dp 以下看不出，再大就有齿 |
| `deepwiki.com` | 整站套 Vercel 安全检查，所有路径（含 `favicon.ico`）都返回 429 的 `Vercel Security Checkpoint` 页；该页自己的 `<link rel="icon" href="data:,">` 是空值 | 只能走 favicon 服务取 256 版，并用 DuckDuckGo（`icons.duckduckgo.com/ip3/<域>.ico`）交叉验证是同一个图标 |
| `huggingface.co` | 站点没有 `apple-touch-icon`（404）；首页 `<link>` 里也没有可用图标声明 | 官方品牌库 `huggingface.co/datasets/huggingface/brand-assets/resolve/main/hf-logo.png`（1024，LFS 大文件） |
| `legado`（阅读） | 原作者仓库 `gedoor/legado` 已清空，`main` 分支只剩一份公告；`mipmap-xxxhdpi` 是最高的 192；`mipmap-anydpi-v26/ic_launcher.xml` 是 adaptive icon，前景层要单独取，拼不回去 | 从社区接手的 `LegadoTeam/legado` 取 `app/src/main/res/mipmap-xxxhdpi/ic_launcher.png`。**不要用 adaptive icon 的前景层**，那是被裁过的不完整图形 |

## 验收

每加一张，逐条过：

```bash
# 1. 尺寸、模式、体积（边长必须 ≥180，体积必须 ≤2MB）
python3 -c "
import os
from PIL import Image
f='icons/<name>.png'; i=Image.open(f)
print(f, i.size, i.mode, os.path.getsize(f), 'bytes')
assert min(i.size) >= 180 and os.path.getsize(f) <= 2*1024*1024"

# 2. raw 必须是 200 直出，且不能跳到别的域名
curl -sIL -m 15 "https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/<name>.png" | grep -Ei '^HTTP|^location'
```

第 2 条重点看 `location`：只要重定向到了别的 host，Kelivo 就会丢掉这张图标（同源限制）。

再人工看一眼：把图放在浅灰底上，确认主体没有贴边、没有多出来的白角。

## 新增一个图标，按这个顺序做

1. 按「抓取顺序」拿到源图，落到本地，量尺寸。
2. 尺寸不够（<180）先换源；换不到就在提交信息里写明实际尺寸和原因（如 Exa 那次）。
3. 原样复制到 `icons/<name>.png`，不改动像素。
4. 跑「验收」两条命令。
5. 更新 `README.md` 的地址列表（raw + jsDelivr）和来源表格。
6. 提交。提交信息非知识库仓库规矩：英文、一句话。

## 换图之后

**文件名固定，换图直接替换同名文件，不改名、不加查询参数。** 地址一旦发布就有人填进 Kelivo 了，改名等于让所有人的链接失效。

代价是客户端不会自己发现内容变了：缓存文件名是 URL 的 sha256，命中就直接用，没有 TTL、没有内容校验。

刷新只能靠清缓存，完整步骤与原理见 `README.md` 的「图标换了，怎么刷新」——等 CDN 过期 → 清理头像缓存 → 强制停止重开，三步缺一不可。改完图在交付说明里把这套步骤带上。
