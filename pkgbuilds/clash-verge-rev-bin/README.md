# Clash Verge Rev 候选包

本地配方：`clash-verge-rev-bin`，版本 `2.5.8-1`，声明 `x86_64` / `aarch64`。此配方把官方固定版本 DEB 暂存为 Arch 包，供 Omarchy / Arch 用户审阅与验证；不运行 Debian 维护脚本，也不安装、启动或启用 root 服务。

已有维护中的 [AUR 同名包](https://aur.archlinux.org/packages/clash-verge-rev-bin)，[官方安装文档](https://www.clashverge.dev/install.html)也推荐通过 AUR 安装。本仓库维护本地候选与适配记录，以现有维护者为协作对象，不创建重复 AUR 提交。

这份本地候选额外核对 DEB 身份、版本、架构和六个 ELF，并把服务卸载保留为用户显式操作；与现有 AUR 的 `pre_remove()` 自动调用服务卸载器有所区别。改进以现有包为协作目标，继续按本仓库的候选验证流程推进。

## 安装与启动

在 Omarchy 图形会话的普通用户终端，进入本仓库根目录，先审阅 [PKGBUILD](PKGBUILD) 后执行：

```bash
./omarchy-tools install clash-verge-rev
```

也接受完整包名 `clash-verge-rev-bin`。入口会检查当前机器架构、准备构建依赖，使用当前 checkout 中固定的版本构建，再交给 pacman 安装；只在系统包操作时调用 sudo。不要用 sudo 运行整个脚本。安装完成后，从应用菜单打开 Clash Verge，或在普通用户终端执行：

```bash
clash-verge
```

如果希望直接使用现有 AUR 维护渠道，可改用以下命令；它是另一种安装来源，不需要与本地配方重复安装：

```bash
yay -S clash-verge-rev-bin
```

本地 `update` 使用仓库固定版本，先拉取配方更新再安装；不会自动把版本改成 GitHub 的 `latest`：

```bash
git pull --ff-only
./omarchy-tools update clash-verge-rev
```

安装不导入订阅、不修改系统代理或 DNS、不打开 TUN，也不设置应用自启动。首次连接、代理端口和 TUN 选项由用户在应用中配置，参考[官方快速入门](https://www.clashverge.dev/guide/quickstart.html)。应用自身的更新行为仍待 Linux 验证；配方没有猜测“禁用更新”环境变量或修改上游资源，更新软件文件应继续通过所选的软件包维护渠道完成。

## 固定来源

2026-10-20 核验：[官方最新稳定 Release](https://github.com/clash-verge-rev/clash-verge-rev/releases/tag/v2.5.8) 为 `v2.5.8`，发布于 **2026-10-09 02:43:45 UTC**（北京时间 10:43:45）。[官方 Release API](https://api.github.com/repos/clash-verge-rev/clash-verge-rev/releases/latest)记录的资产如下，配方固定到该 tag 的 HTTPS URL，不把 `latest` 用作下载来源。

| Arch 架构 | 官方 DEB | 大小（字节） | SHA-256 |
| --- | --- | --- | --- |
| `x86_64` | [Clash.Verge_2.5.8_amd64.deb](https://github.com/clash-verge-rev/clash-verge-rev/releases/download/v2.5.8/Clash.Verge_2.5.8_amd64.deb) | 104179124 | `ceeb7578c6f030b33ddf6346486db24013cf4557cc340de5f312f98a924a8546` |
| `aarch64` | [Clash.Verge_2.5.8_arm64.deb](https://github.com/clash-verge-rev/clash-verge-rev/releases/download/v2.5.8/Clash.Verge_2.5.8_arm64.deb) | 100300512 | `acf83a1c9cd4e812b3efc33c7e5d3bfc86b4af37495010c91935c876c7d3ba2e` |

上表 SHA-256 与大小最初取自该次 Release API 的资产 `digest`，两个 DEB 的实际下载结果均与之相符；ELF 和暂存检查的证据单独记录于下方。该发行版另外提供 RPM 和 ARMv7 DEB，本配方只支持上述两个架构，没有把 ARMv7 或 x86 软件改标为 ARM64。官方 [Linux bundle 配置](https://github.com/clash-verge-rev/clash-verge-rev/blob/v2.5.8/src-tauri/tauri.linux.conf.json)和本次 Release 都提供 DEB / RPM，没有 AppImage。

**旧 x86 CPU 边界：** 上游 [prebuild.mjs](https://github.com/clash-verge-rev/clash-verge-rev/blob/v2.5.8/scripts/prebuild.mjs)为 Linux x64 的稳定版和 Alpha Mihomo 内核都选择 `mihomo-linux-amd64-v2`。因此声明 `x86_64` 不代表兼容所有旧 x86-64 处理器；内置内核需要 x86-64-v2 指令集。本包不替换内核来改变这一要求，旧 CPU 兼容性需另行处理和验证。

## 文件布局与可选服务

保留官方主程序、图标、桌面入口、资源及随附二进制；`clash-verge` 与 `clash-verge-service`、`clash-verge-service-install`、`clash-verge-service-uninstall`、`verge-mihomo`、`verge-mihomo-alpha` 保持上游预期的相邻关系。不改变用户默认协议处理程序，不设置 setuid 或额外文件 capabilities。Arch 运行依赖结合官方 DEB 元数据与 ELF 直接依赖表确定，仍须在目标 Linux 中验证动态链接。

当前上游固定依赖 [clash-verge-service-ipc v2.7.6](https://github.com/clash-verge-rev/clash-verge-rev/blob/v2.5.8/src-tauri/Cargo.toml)。需要服务模式时，由用户在应用设置中明确选择安装服务并通过 polkit / sudo 授权。该[上游安装器](https://github.com/clash-verge-rev/clash-verge-service-ipc/blob/v2.7.6/src/bin/install_service.rs#L828)会把服务及允许执行的内核复制到受保护的 `/var/lib/clash-verge-service/bin` 和 `/var/lib/clash-verge-service/cores`，创建 `/etc/systemd/system/clash-verge-service.service`，然后启用并启动服务；这些属于用户后续选择，不能放进 `package()`。

升级软件包后，已安装的服务 / 内核副本也需通过应用提供的服务更新或重装流程确认版本一致，并显式授权；单独更新 `/usr` 中的包文件不会刷新 `/var/lib` 中的副本。

安装器按调用用户身份选择服务组，不能套用旧版 `clash-meta` 组或历史 systemd 单元。配方不创建另一套 systemd 单元，不调用厂商安装器或卸载器，也不在安装时自动开启 TUN。Hyprland 中的授权提示、服务 IPC、代理恢复和 TUN 路由都需要实机验收。

## 服务与卸载

先在应用中关闭 TUN / 系统代理并确认网络恢复。如果曾安装过服务，**在卸载软件包前**用应用设置卸载该服务；也可以在普通用户终端显式调用仍由软件包提供的卸载器：

```bash
sudo /usr/bin/clash-verge-service-uninstall
```

该[上游卸载器](https://github.com/clash-verge-rev/clash-verge-service-ipc/blob/v2.7.6/src/bin/uninstall_service.rs#L151)会停止和禁用服务，移除它创建的 `/etc` 单元及受保护的服务 / 内核副本。随后退出应用，再从本仓库根目录卸载包：

```bash
./omarchy-tools remove clash-verge-rev
```

也可使用 `sudo pacman -R clash-verge-rev-bin`。pacman 仅移除它管理的文件，不能假定会清理此前由 GUI 创建的 root 服务及 `/var/lib` 副本；本地候选不增加静默运行厂商卸载器的安装钩子。用户配置、订阅与日志不会由本仓库安装入口主动删除。

## 验证记录

2026-10-20，已核验官方 Release 的版本、发布时间、架构资产、API digest、标签内 Linux 打包配置、许可证和服务安装 / 卸载源码。配方声明双架构与上游提供双架构资产是来源证据，不代表运行验收。

两架构官方 DEB 已实际下载，文件大小和 SHA-256 均与上表一致。两者 control 都声明 `Package: clash-verge`、`Version: 2.5.8`，架构分别为 `amd64` / `arm64`，并使用 `control.tar.gz` 与 `data.tar.gz`。各 data 归档检查了 30 个条目，未发现越界路径、逃逸软链接或 setuid 文件。

每个 DEB 的 6 个 ELF 都为 ELF64，x86_64 的 machine 值为 62、aarch64 为 183。主程序直接依赖 WebKitGTK 4.1 / GTK3 及相关 GLib、图形和网络库，3 个 Rust 服务程序直接依赖 `libgcc_s` / glibc；两个 Mihomo 内核无 `PT_INTERP` / `DT_NEEDED`。两架构主程序中扫描到的 GLIBC 版本字符串最高为 2.35，服务程序为 2.34；这是静态引用线索，不能代替系统兼容性与运行验证。

当前维护环境是 macOS ARM，未在此执行厂商 Linux 二进制或维护脚本；未进行 Linux `makepkg` 构建或运行验收。

两架构已用真实归档执行 `prepare()` / `package()` 暂存检查：各自的 15 个厂商文件内容和权限完全保持，新增文件只有包许可证。将 amd64 control 与 ARM64 data 错配后，ELF 检查按预期拒绝。宿主缺少 Linux `readelf` 和 GNU `install -D`，检查分别使用读取实际 ELF 头的 Python 适配器及等价文件安装适配器；这项结果不是 Linux `makepkg` 构建。两个主程序的 `.gnu.version_r` 还明确要求 `libm.so.6` 的 `GLIBC_2.35`，配方据此声明 `glibc>=2.35`，不据此宣称整个应用的运行兼容性已验收。

仓库包与插件静态检查通过；根目录测试 **84 项**、插件测试 **37 项**，合计 **121 项通过**。CI 已为本包分别调度两个原生架构，并区分动态程序的 `ldd` 检查与静态 Mihomo 的 `readelf` 检查；这表示验证流程已接入，尚未把远端运行状态记为通过。

待完成：两架构 Linux `makepkg` 构建、`.SRCINFO` 对照、依赖与安装文件检查，pacman 安装 / 升级 / 卸载，Omarchy / Hyprland 应用菜单和终端启动、托盘、缩放、输入法、协议处理、订阅导入、系统代理及恢复、polkit 授权、服务安装 / 卸载与 IPC、TUN / DNS / 路由和应用自更新行为。下载及静态暂存通过不能代替这些检查，详见[仓库测试流程](../../docs/testing.md)。

在目标 Arch Linux 中，以普通用户运行对应架构的原生环境检查：

```bash
tools/check-package clash-verge-rev-bin --require-makepkg
cd pkgbuilds/clash-verge-rev-bin
makepkg --verifysource
makepkg --printsrcinfo
makepkg -s
```

与已提交 `.SRCINFO` 对照，再按测试流程进行安装和生命周期验收。候选 `.omarchy/package.json` 保持 `sync: false`；验收后再向现有 AUR / Omarchy 维护者提供改进，发布策略见[发布流程](../../docs/publishing.md)。

## 许可证与分发

主程序 [Cargo.toml](https://github.com/clash-verge-rev/clash-verge-rev/blob/v2.5.8/src-tauri/Cargo.toml)声明 `GPL-3.0-only`，[上游 LICENSE](https://github.com/clash-verge-rev/clash-verge-rev/blob/v2.5.8/LICENSE)随配方固定校验并安装。随附 Mihomo、服务 helper 与其他第三方资源保留各自许可证；本仓库的 0BSD 不重新授权它们。

GPL 软件的二进制再分发需要满足相应许可证义务，包括与实际二进制对应的源码、版权和构建材料。仅链接一个项目主页或保留配方不足以说明这些材料已备齐。目前只发布配方与说明，构建时从官方固定地址下载；本仓库和 CI 默认不上传 DEB 或生成的 Arch 包，待整理相应材料及完成 Linux 验证后再评估二进制分发。
