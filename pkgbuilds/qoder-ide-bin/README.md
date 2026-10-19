# Qoder IDE 候选包

本地配方：`qoder-ide-bin`，版本 `1.33.0-1`，仅 `x86_64`。已有 [AUR 同名包](https://aur.archlinux.org/packages/qoder-ide-bin)，这里维护可审阅的候选及共存适配；不创建重复 AUR 包。不要将该 IDE 与新版 Qoder 桌面工作台合并为一个包。

## 固定来源

- 发现入口：[官方下载页](https://qoder.com/download) 的 Qoder IDE → Linux x64。
- [官方固定版本 DEB](https://download.qoder.com/release/1.33.0/qoder-ide_amd64.deb)，配方不使用 `latest`。
- 完整 DEB 版本：`1.33.0-1791815607`，包名 `qoder-ide`，架构 `amd64`。
- 下载大小：180,124,116 字节。
- 实际下载 SHA-256：`193582f86ddbd77f615ecffb160d5ba13667d6c354b12ce706e2634e7043154e`。
- 2026-10-17 检查；尚未确认官方 Linux ARM64 产物，不声明 `aarch64`。

`pkgver` 使用产品版本 `1.33.0`；厂商构建标记单独记录在 `_debbuild`，`prepare()` 核对完整 DEB 版本。若厂商重发相同产品版本，重新检查构建标记和哈希，并增加下游 `pkgrel`，不静默替换已发布包的字节。

## 布局、入口与协议

保留厂商 `/usr/share/qoder-ide` 中的 Electron/Chromium、原生依赖和资源，不修改 `product.json` 或替换运行时。Arch 依赖结合厂商 DEB 与主 ELF 直接依赖表声明，仍待 Linux 动态链接验证。

`qoder-ide` 指向厂商的 `/usr/share/qoder-ide/bin/code`，用于明确启动 IDE。厂商另一个 `bin/qoder` 桥接器会优先执行用户的 `~/.qoder/entry/qoder`，可能转交其他产品；因此不把该桥接器注册为系统 `qoder`。Qoder 桌面包使用 `qoder` / `qoder-desktop`，CLI 包使用 `qodercli`。

保留官方图标、AppStream、workspace MIME、`qoder-ide.desktop` 和 URL handler；协议包含 `qoder-ide:` 与旧 `qoder:`。安装不改变用户默认处理程序；新版桌面也注册 `qoder:`，需要在实际登录流程中确认所选处理程序。删除系统范围内原本补全 `qoder` 的 IDE Bash/Zsh 补全入口，避免桌面命令收到错误的补全；厂商内部资源不改。

不执行 Debian 维护脚本或 alternatives 操作。`chrome-sandbox` 设为 `0755`，使用目标系统的用户命名空间；不增加 `--no-sandbox`。安装不登录、启动或修改用户配置。

尚待实测 IDE 自更新是否仅提示下载、会否覆盖 pacman 文件；初期手动更新配方，`.omarchy/package.json` 设置 `sync: false`。没有为尚未验证的更新逻辑猜测环境变量或修改签名资源。

## 验证记录

2026-10-17，在 Darwin arm64 维护机完成：固定来源下载及 SHA-256、完整 DEB 元数据、归档布局、桌面/协议/图标、主 ELF 的 x86_64 架构和直接依赖表，以及厂商 CLI 桥接器/原生启动器检查。`.SRCINFO` 是配方导出的候选元数据，待 Linux `makepkg --printsrcinfo` 核对。`tools/check-package` 静态检查已通过。

`prepare()` / `package()` 在临时目录进行了归档装配检查；针对宿主缺少 Linux `readelf` 和 GNU `install -D` 使用读取真实 ELF 头及等价目录创建适配器，未执行厂商二进制。装配后的文件与桌面候选没有文件路径冲突，命令及许可证软链接指向包内文件。该检查不代表 Linux 构建、安装或运行通过。

待完成：Linux 构建/依赖检查，pacman 安装、升级、卸载，`qoder-ide --version`/文件打开，Hyprland 桌面启动，缩放/输入法（fcitx5 环境配置见[中文输入法记录](../../docs/chinese-input.md)，本项仍需 IDE 自身实测），`qoder-ide:` 与旧 `qoder:` 登录回调，和桌面版/CLI/已有用户 dispatcher 共存、沙箱与自更新。详见 [测试流程](../../docs/testing.md)。

在 Arch Linux x86_64 中审阅配方后执行：

```bash
makepkg --verifysource
makepkg --printsrcinfo > .SRCINFO
extra-x86_64-build
```

以上仍待 Linux 环境执行。完成验证后按 [发布流程](../../docs/publishing.md) 向现有 AUR/Omarchy 维护者提供修复。

厂商条款在 `LICENSE.upstream`；Chromium 及第三方 notices 保留在包内。公开下载本身不代表可再次托管上游二进制；本仓库和 CI 不上传该安装包。
