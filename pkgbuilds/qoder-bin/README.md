# Qoder 桌面版候选包

本地配方：`qoder-bin`，版本 `0.4.8-1`，仅 `x86_64`。这是新版 Qoder 桌面工作台，与 Qoder IDE 和 CLI 是不同产品。已有 [AUR 同名包](https://aur.archlinux.org/packages/qoder-bin)，这里用于审阅和参与上游维护，不另建重复 AUR 包。

## 固定来源

来源发现入口：[官方下载页](https://qoder.com/download)。页面的 Linux x64 链接使用可变的 `latest`；本配方改用官方下载响应头 `x-oss-meta-source-object` 指向的固定版本路径。

- [官方固定版本 DEB](https://download.qoder.com/qoder-app/releases/0.4.8/Qoder-linux-amd64.deb)
- 完整 DEB 版本：`1:0.4.8`，包名 `qoder`，架构 `amd64`。
- 下载大小：256,549,376 字节。
- 实际下载 SHA-256：`1e47b4de4d8c47235d52ada8a865630c2d4e193571062924cbe48c69719ac88d`，与官方对象头记录一致。
- 2026-10-17 检查；尚未确认官方 Linux ARM64 产物，因此不声明 `aarch64`。

DEB 的 `1:` 只作为 `_debepoch=1` 用于核对厂商完整版本；Arch 配方不引入 epoch。当前产品版本已能正常从既有 AUR 版本升级，无需作出永久的版本排序改变。

## 安装布局与共存

保留厂商 `/opt/Qoder` 中的 Electron/Chromium、原生库及应用资源，不换成系统 Electron，不修改 `app.asar`。依赖来自主程序 ELF 的 `DT_NEEDED` 和厂商 DEB 依赖；仍需 Linux 上的 `namcap` 和实际动态链接验证。

- `qoder`、`qoder-desktop` 均指向 `/opt/Qoder/qoder`。
- 本仓库 CLI 包使用 `qodercli`，IDE 包使用 `qoder-ide`，避免由三个包争抢同一命令。
- 保留官方 `qoder.desktop`、各尺寸图标及 `qoder:` / `qoder-app:` 注册。
- 安装不修改用户默认 URL 处理程序；IDE 也声明旧 `qoder:` 协议，双产品共存时由用户选择默认程序。
- 不执行 DEB `postinst`/`postrm`，不写 AppArmor 配置或 alternatives 数据库，不启动、登录或创建用户配置。
- `chrome-sandbox` 为 `0755`，依赖目标系统提供用户命名空间；不添加 `--no-sandbox`。

上游更新行为尚待实机确认，暂不改厂商应用资源或用户配置。使用 pacman 管理系统安装文件；发布前验证客户端“检查更新”不会自行覆盖它们。`.omarchy/package.json` 初期使用 `sync: false`，人工审阅更新。

## 验证记录

2026-10-17，在 Darwin arm64 维护机完成：固定来源下载、完整 SHA-256、DEB 身份/版本/架构、归档布局、桌面入口、图标、主 ELF 的 x86_64 架构及直接依赖表检查。包目录的 `.SRCINFO` 是配方导出的候选元数据，尚须 Linux `makepkg --printsrcinfo` 核对。`tools/check-package` 静态检查已通过。

`prepare()` / `package()` 在临时目录进行了归档装配检查；宿主缺少 Linux `readelf` 和 GNU `install -D`，使用了读取真实 ELF 头的适配器和等价目录创建适配器，未执行厂商二进制。装配后的全部文件与 IDE 候选没有文件路径冲突，命令及许可证软链接指向包内文件。这不是 Linux `makepkg` 构建或安装验证。

整包另包含厂商 Sharp 的 glibc/musl 平台变体；musl 变体的存在不等于主程序需要 musl。目标平台的实际变体选择仍须在 Linux 验证。

仍需完成：Linux 构建及依赖解析；`pacman -U` 安装、升级、卸载；Hyprland/Wayland 与 XWayland；中文输入、缩放和图形加速；浏览器登录回调；沙箱启动；自更新与命令/用户数据共存。详见 [测试流程](../../docs/testing.md)。

在受支持的 Arch Linux x86_64 环境中审阅配方后执行：

```bash
makepkg --verifysource
makepkg --printsrcinfo > .SRCINFO
extra-x86_64-build
```

以上是待执行的验收命令，不表示本次已经运行。遵循 [发布流程](../../docs/publishing.md) 向已有维护者提供修复。

`LICENSE.upstream` 是厂商条款入口；Electron 和 Chromium 许可证保留在包内。尚未确认厂商二进制重分发授权，不在本仓库或 CI 附件中托管安装包。
