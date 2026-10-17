# 钉钉（DingTalk）接入记录

调研日期：2026-10-17。状态：**上游已有双架构 Omarchy 配方；本仓库先记录、验证和参与上游维护，不创建重复包。** 本次没有在 Linux/Omarchy 上运行客户端，也没有确认各发布通道当前可安装的版本。

## 已确认的分发入口

用户提供的是[钉钉官方 Linux 历史版本页](https://page.dingtalk.com/wow/dingtalk/default/dingtalk/15akajjLwh2sHUAhru7)。页面初始 HTML 的 `window.$data` 包含下载数据，可在不执行第三方安装脚本的情况下提取。

该页已经列出 **Arch 系列**：官方提供 `dingtalk-bin-8.2.8.260904001-1-x86_64.pkg.tar.zst`，更新说明明确提及支持 Omarchy。该项目不应再以“钉钉完全没有 Arch/Omarchy 入口”为前提。

| 来源 | 2026-10-17 查到的版本 | 架构及状态 |
| --- | --- | --- |
| 官方页面的 Arch 系列 | `8.2.8.260904001-1` | `x86_64`；未在该页发现官方 `aarch64` Arch 包 |
| 官方页面的 Debian 系列 | `8.3.1.260917001`，同时保留 `8.2.8.260904001` | `amd64`、`arm64`，另有本项目范围外的架构；页面标注测试预览版本 |
| [Omarchy 配方](https://github.com/omacom/omarchy-pkgs/tree/master/pkgbuilds/dingtalk-bin) | `8.3.1.261008001-1` | `x86_64`、`aarch64`，各取官方固定版本 DEB |
| [AUR `dingtalk-bin`](https://aur.archlinux.org/packages/dingtalk-bin) | `8.2.8.260904001-1` | 已有维护者；本次 AUR RPC 显示已被标记过期 |

AUR 的当前维护者为 `zhullyb`，共同维护者包括 `sukanka`、`yjun`、`witt.9099`、`Integral`；最后修改时间为 2026-09-19 UTC。数据可通过 [AUR RPC](https://aur.archlinux.org/rpc/v5/info?arg%5B%5D=dingtalk-bin) 重查。维护状态会变化，贡献前重新读取。

Omarchy 配方比官网历史页列出的版本更新，因此不能把历史页的第一项直接当作整个产品的最新版本。下表仅记录已查到的发布输入；版本变更时重新核实 URL、包内版本和架构。

## 为何官方点名 Omarchy：已知事实与尚未证实的部分

官方 Arch 版本的更新说明确实出现“支持 Omarchy 等系统”，所以厂商在发布信息中主动提到了该发行版。公开页面未解释业务动机，本次也未找到双方正式合作公告。

Omarchy 添加包的 [PR #1123](https://github.com/omacom/omarchy-pkgs/pull/1123)于 2026-10-15 由 `omarchybot` 创建并合并；正文描述重新打包官方 DEB，没有声明提交者为钉钉员工，也不能仅根据账号名称推断组织合作。[后续版本更新 PR #1170](https://github.com/omacom/omarchy-pkgs/pull/1170)是仓库的自动跟踪更新。

合理推测是：Omarchy 与其他 Arch 系统共享包格式，使厂商在提供 Arch 包时把它列入适用系统的成本较低；这只是对技术关系的推断，不是钉钉公开确认的支持动机。PR 还明确记录登录后的聊天、会议和共享未验证，ARM 包当时仅检查未启动；不要把已接入包源等同于所有功能经过验证。

## Omarchy 当前打包输入

来源：[上游 `PKGBUILD`](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/dingtalk-bin/PKGBUILD)。以下 SHA-256 来自该配方，本次未重新下载约 370 MB 的两个 DEB 独立复算，不能将其标记为“本仓库已验证”。

| Arch 架构 | 官方下载 URL | SHA-256（上游配方记录） |
| --- | --- | --- |
| `x86_64` | [amd64 DEB](https://dtapp-pub.dingtalk.com/dingtalk-desktop/xc_dingtalk_update/linux_deb/Release/com.alibabainc.dingtalk_8.3.1.261008001_amd64.deb) | `35ab680ded104abcdc53a67fcfcff2b56479997f16e8abfe11c41fbf58f5825e` |
| `aarch64` | [arm64 DEB](https://dtapp-pub.dingtalk.com/dingtalk-desktop/xc_dingtalk_update/linux_deb/Release/com.alibabainc.dingtalk_8.3.1.261008001_arm64.deb) | `19c31e3eddec37c5b5c8adc5b12a7dbb20b9cd0416b97872477a6f865acf8603` |

[官方 Arch 包下载](https://dtapp-pub.dingtalk.com/dingtalk-desktop/xc_dingtalk_update/linux_arch/Release/dingtalk-bin-8.2.8.260904001-1-x86_64.pkg.tar.zst)可以作为另一条用户安装入口，但不应与 Omarchy 当前配方混成同一个版本，也不能仅因扩展名相同就把未验证的二进制上传到自己的源。

## 接入决定

1. 优先在目标设备运行 `pacman -Si dingtalk-bin` 确认所用 Omarchy 通道确有该包，再按 Omarchy 当前命令使用 `omarchy pkg add dingtalk-bin`。
2. 若包源没有，先审阅现有 AUR 配方，再考虑 `omarchy pkg aur add dingtalk-bin`；不要再发布同名重复 AUR 包。
3. 补丁和架构支持优先贡献给 `omacom/omarchy-pkgs` 的现有目录。本仓库保留测试记录、问题复现和必要的导出补丁。
4. 只有明确存在上游无法解决的差异，才引入本地配方，并在目录说明分叉原因、来源提交和退出条件。

本次尝试读取 `pkgs.omarchy.org` 的仓库数据库返回 HTTP 403，故**“上游配方存在”不等于已证实 stable/edge 双架构二进制全部发布**。应以目标机 `pacman -Si` 和实际安装结果为准。

## 已有适配，后续不要丢失

Omarchy 当前的[启动器](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/dingtalk-bin/dingtalk.sh)强制使用 `QT_QPA_PLATFORM=xcb`：供应商打包的 Qt 没有 Wayland 平台插件，采用 XWayland。它设置自带 Qt 插件路径、按 `GDK_SCALE` 调整字体 DPI，并预载 `libcef.so`。

配方还移除会覆盖 Arch 当前图形/网络库的部分旧依赖、清理要求可执行栈的共享库，并检查版本、ELF 架构和异常权限。这些都是应在上游修复基础上继续维护的行为，不能退回“解开 DEB 后全量复制”的转换方式。

[desktop 文件](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/dingtalk-bin/dingtalk.desktop)已声明 `dingtalk:` 协议和窗口类。供应商的 DEB `postinst` 不能直接作为 Arch 安装钩子执行，包的安装也不应擅自登录、开启自启动或修改用户默认程序。

## 实机验收清单

双架构分别记录发行版/通道、包版本、Hyprland 版本和测试日期。以下均待实测，不代表已知故障：

- 安装、升级、降级和卸载；用户配置保留，系统文件由 pacman 管理；检查包内文件权限。
- Hyprland/XWayland 下冷启动、窗口类匹配、多屏、分数缩放、中文输入及复制粘贴；核实 fcitx5 插件与托盘。
- 手机扫码/账号登录、退出后重新登录、浏览器打开 `dingtalk:` 链接及已运行实例接收链接；使用测试账号，不在日志保存登录令牌。
- 消息通知、托盘菜单、关闭窗口后的驻留行为及重新打开。
- PipeWire、portal 下的屏幕共享/窗口共享、截图、多显示器选择；共享黑屏时区分客户端、XWayland 和 portal 的问题。
- 视频会议、摄像头、麦克风、扬声器和设备切换；不假定 DEB 在 UOS/麒麟上的表现等同于 Arch/Hyprland。
- 客户端内“检查更新”不会自行覆盖 `/opt/dingtalk` 或绕过 pacman；若上游没有可关闭自更新的开关，记录其实际行为后再决定补丁，不猜测环境变量。

钉钉是专有软件，[当前上游许可证说明](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/dingtalk-bin/LICENSE)指向[钉钉服务协议](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_dingtalk/suit_bu1_dingtalk202010200940_84493.html)。本仓库暂只收录文档和配方；未来发布二进制前核实相应授权。
