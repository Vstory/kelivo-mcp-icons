# kelivo-mcp-icons

Kelivo（及 fork）MCP 服务器自定义图标的托管仓库，按应用分文件。

图标存副本而不是直接引用原站，是因为第三方站点的图片地址会随改版失效；这里换图标只需改仓库里的文件，MCP 里的链接不用动。

仓库必须公开 —— Kelivo 拉图标不带 token，私有仓库给不了可访问地址。

## 用法

MCP 服务器 → 编辑 → 图标 → 链接，填下表的地址。

```
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/amap.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/dida365.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/mt-manager.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/github.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/legado.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/deepwiki.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/huggingface.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/exa.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/cloudflare.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/context7.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/firecrawl.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/tavily.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/stripe.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/feishu.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/canva.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/dropbox.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/discord.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/google-maps.png
https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/google-developer-knowledge.png
```

raw 走不通时换 jsDelivr（同一份文件，CDN 加速）：

```
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/amap.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/dida365.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/mt-manager.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/github.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/legado.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/deepwiki.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/huggingface.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/exa.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/cloudflare.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/context7.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/firecrawl.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/tavily.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/stripe.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/feishu.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/canva.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/dropbox.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/discord.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/google-maps.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/google-developer-knowledge.png
```

## 图标

| 文件 | 应用 | 尺寸 | 原地址 |
|------|------|------|--------|
| `icons/amap.png` | 高德地图 | 512×512 | App Store 接口 `itunes.apple.com/lookup?bundleId=com.autonavi.amap` 的 `artworkUrl512`，把结尾 `512x512bb.jpg` 改成 `.png` 取无损版 |
| `icons/dida365.png` | 滴答清单 | 180×180 | `https://cncdn.dida365.com/web/static/img/apple-touch-icon.png` |
| `icons/mt-manager.png` | MT管理器 | 600×600 | `https://mt.cc/logo.png` |
| `icons/deepwiki.png` | DeepWiki | 256×256 | `deepwiki.com` 的 favicon（站点有 Vercel 挑战墙，直连 429，取自 Google favicon 服务） |
| `icons/huggingface.png` | Hugging Face | 1024×1024 | 官方品牌资源 `huggingface.co/datasets/huggingface/brand-assets` 的 `hf-logo.png` |
| `icons/exa.png` | Exa | 1024×1024 | `https://exa.imgix.net/logo_cream.png?w=1024`（imgix 从官方源图渲染） |
| `icons/cloudflare.png` | Cloudflare | 400×400 | `https://github.com/cloudflare.png?size=512`（官方 GitHub 头像，橙云 mark） |
| `icons/context7.png` | Context7 | 512×512 | 官方 `context7-logo-dark.svg`（116×28）里那个 28×28 的方形 mark，按矢量渲染；站点所有 `apple-touch-icon`/`icon-*.png` 路径都返回 SPA 页面，没有位图可用 |
| `icons/firecrawl.png` | Firecrawl | 180×180 | `https://www.firecrawl.dev/apple-touch-icon.png`（站点 `favicon.png` 只有 48×48） |
| `icons/tavily.png` | Tavily | 512×512 | PWA manifest `/manifest.webmanifest` 里的 `app-icons/icon-512.png` |
| `icons/stripe.png` | Stripe | 512×512 | `images.stripeassets.com/.../favicon.png?w=512&h=512`（站点 apple-touch-icon 同源，尺寸可调） |
| `icons/feishu.png` | 飞书 | 512×512 | App Store 官方图标（id `1401729613`，`artworkUrl512` 换 `.png`）；官网 `apple-touch-icon.png` 404、`favicon.ico` 仅 48×48 |
| `icons/canva.png` | Canva | 512×512 | App Store 官方图标（id `897446215`）；官网 `apple-touch-icon.png` 404 且首页 403 反爬 |
| `icons/dropbox.png` | Dropbox | 512×512 | App Store 官方图标（id `327630330`）；官网 `apple-touch-icon.png` 404 |
| `icons/discord.png` | Discord | 256×256 | 官网 `apple-touch-icon` 指向的 ico（`cdn.prod.website-files.com`），转 PNG |
| `icons/google-maps.png` | Google Maps | 512×512 | PWA manifest 的 `logo_maps_2025_color_1x_web_512dp.png`；manifest 自带的 round 版会带白圈，改用方形版 |
| `icons/google-developer-knowledge.png` | Google Developer Knowledge | 180×180 | `developers.google.com` 的 `touchicon-180-new.png` |
| `icons/legado.png` | Legado（阅读） | 192×192 | `LegadoTeam/legado` 的 `app/src/main/res/mipmap-xxxhdpi/ic_launcher.png`（Android 最高密度；原作者仓库 gedoor/legado 已清空，只剩公告） |
| `icons/github.png` | GitHub | 512×512 | `https://github.com/fluidicon.png`（站点 `rel="fluid-icon"`，深色圆盘 + 白猫，圆外透明） |

## 收录标准

- 边长 ≥ 180（36dp 头像在 5 倍屏上是 180px，再小就糊）；
- 原样保存，不重绘、不裁切、不加底色；透明底优先，满画布的实底图也能用；
- 优先官方来源：站点自带的 `apple-touch-icon` / PWA `manifest` / 品牌 logo 文件，官网没有才退回应用商店接口。

## 图标换了，怎么刷新

仓库里的文件替换后，Kelivo 不会自动发现。按顺序做：

1. **等 5 分钟**。raw 的响应头是 `cache-control: max-age=300`，刚推完 CDN 还在发旧文件，这时候清缓存会原样拉回旧图。
2. **设置 → 存储空间 → 头像缓存 → 清理头像缓存**。
3. **划掉后台的 Kelivo**（或在系统里强制停止），再重新打开。

第 2 步只删磁盘上的文件；第 3 步清的是 Flutter 进程内的图片解码缓存。少了第 3 步，文件虽然重下了，列表里还是旧图。

不要用系统的「应用信息 → 存储 → 清除缓存」：它删的是 `/data/user/0/<包名>/cache`，而图标缓存在 `<包名>/app_flutter/cache/avatars`，够不着。系统的「清除数据」倒是能删掉，但会连配置一起抹掉。

## 缓存文件名是什么意思

```
mcp_acbf86f0210e1d522e5a88ba7eb435f147d8684decd2d205e7e5f7f411bccf08.img
    └──────────────────┬───────────────────────────┘   └┬┘
      图标链接字符串的 SHA-256（64 位十六进制）          内容类型
```

| 段 | 含义 |
|---|---|
| `mcp_` | MCP 图标专用前缀，与模型头像等其它缓存区分 |
| 64 位十六进制 | **图标链接字符串**的 SHA-256，不是图片内容的哈希 |
| `.svg` | 矢量图标，原样存 |
| `.png` | 下载到的是 `.ico`，已解出其中一帧转成 PNG |
| `.img` | 其它位图（png / jpg / webp / gif / bmp），原样存，统一叫 `.img` |

关键在于**文件名只跟链接走，跟图片内容无关**：同一个链接换了内容，文件名不变，客户端看到文件在就直接用。这就是换图必须清缓存的原因。

想确认某个缓存文件对应哪条链接，把候选 URL 逐个算一遍 SHA-256 比对：

```bash
printf '%s' 'https://raw.githubusercontent.com/Vstory/kelivo-mcp-icons/main/icons/amap.png' | sha256sum
```

输出（64 位十六进制）与本机那个文件名一致的就是它。上例的 `acbf86f0…` 只是示例，不是本仓库任何一条地址的哈希。
