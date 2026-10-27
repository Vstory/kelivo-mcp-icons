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
```

raw 走不通时换 jsDelivr（同一份文件，CDN 加速）：

```
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/amap.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/dida365.png
https://cdn.jsdelivr.net/gh/Vstory/kelivo-mcp-icons@main/icons/mt-manager.png
```

## 图标

| 文件 | 应用 | 尺寸 | 原地址 |
|------|------|------|--------|
| `icons/amap.png` | 高德地图 | 512×512 | App Store 接口 `itunes.apple.com/lookup?bundleId=com.autonavi.amap` 的 `artworkUrl512`，把结尾 `512x512bb.jpg` 改成 `.png` 取无损版 |
| `icons/dida365.png` | 滴答清单 | 180×180 | `https://cncdn.dida365.com/web/static/img/apple-touch-icon.png` |
| `icons/mt-manager.png` | MT管理器 | 600×600 | `https://mt.cc/logo.png` |

## 收录标准

- 边长 ≥ 180（36dp 头像在 5 倍屏上是 180px，再小就糊）；
- 原样保存，不重绘、不裁切、不加底色；透明底优先，满画布的实底图也能用；
- 优先官方来源：站点自带的 `apple-touch-icon` / PWA `manifest` / 品牌 logo 文件，官网没有才退回应用商店接口。
