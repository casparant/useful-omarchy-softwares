# 调研结论与维护边界

调研日期：2026-10-17。软件版本、AUR 归属和 Omarchy 贡献规则会变化；新增或发布前重新检查对应来源。

## 仓库定位

这里维护 Arch Linux 标准软件包配方及必要的 Omarchy 适配，同时收录值得使用的上游软件。`PKGBUILD` 是配方，`makepkg` 生成的 `.pkg.tar.zst` 是安装包，pacman 软件源负责分发和升级。三者可以共用同一份配方。

| 入口 | 内容与职责 | 本仓库的做法 |
| --- | --- | --- |
| GitHub | 配方、补丁、文档和审阅记录 | 主维护仓库，不提交构建产物 |
| AUR | 每个 `pkgbase` 独立的 Git 仓库，发布构建文件 | 先查重；已有包优先参与维护 |
| Omarchy 包源 | 构建、签名并发布二进制 Arch 包 | 每个包单独贡献 PR |
| 自建 pacman 源 | 安装包、仓库数据库、签名与托管 | 暂不运营；需求明确后再增加 |

在 GitHub 放配方不会自动进入 AUR；把安装包上传到 Releases 也不会自动成为 pacman 源。自建源需要用 `repo-add` 生成数据库，配置托管和签名信任。[AUR 提交规则](https://wiki.archlinux.org/title/AUR_submission_guidelines)、[repo-add 手册](https://man.archlinux.org/man/repo-add.8.en)

`catalog.json` 记录软件及维护状态；`pkgbuilds/` 只收录这里实际维护的配方。不要为了充实目录复制已有的良好 AUR 包。上游闭源软件的许可证与本仓库配方的许可证分别记录。

## Omarchy 的入口

Omarchy 官方包仓库是 [omacom/omarchy-pkgs](https://github.com/omacom/omarchy-pkgs)。它采用每包一个 `pkgbuilds/<pkgbase>/` 目录及 `.omarchy/package.json`，支持 `x86_64` 与 `aarch64`，发布渠道依次为 `edge`、`rc`、`stable`。进入包源、进入精选菜单、默认预装是不同事项。

导入 AUR 是一次性导入；Omarchy 随后自行维护配方，不会自动继续同步 AUR。本仓库、AUR、Omarchy 出现多个副本时，在软件目录中记录维护归属和同步方向，避免认为改了这里就会更新所有入口。[Omarchy 贡献说明](https://github.com/omacom/omarchy-pkgs#contribute-a-package)、[上游更新机制](https://github.com/omacom/omarchy-pkgs/blob/master/docs/upstream-sources.md)

## 第一批软件

1. **QoderWake**：第一份双架构配方。按官方发布清单固定 Wake 及其要求的 CLI 版本，检查下载和安装布局。构建和运行结果分别记录。
2. **Qoder CLI**：审阅现有 `qodercli-bin`，核对命令入口、自更新和与 Wake 的关系，再决定向既有维护者贡献哪些修改。
3. **Qoder 桌面版、Qoder IDE**：已从官方固定版本 DEB 建立 [桌面候选](../pkgbuilds/qoder-bin/README.md) 和 [IDE 候选](../pkgbuilds/qoder-ide-bin/README.md)，仅声明 x86_64；先验证 Linux 构建、Wayland、登录 URL 回调和命令共存，再向既有 AUR 维护者提供修复。没有确认官方 ARM 产物时不声明 ARM 支持。
4. **钉钉**：官网已经提供 x86_64 Arch 包，Omarchy 已有 `dingtalk-bin` 双架构配方。优先验证现有渠道、参与上游维护，保留安装及桌面兼容测试；不创建重复包。官网历史页、AUR 和 Omarchy 配方的版本不同，来源与限制见 [钉钉接入记录](software/dingtalk.md)。

具体版本、已确认的架构和实施状态以 `catalog.json`、各软件文档和测试记录为准。以上顺序是本仓库的维护路线，不代表本仓库已完成后续软件的构建或发布；钉钉的既有上游入口单独记录。

官方入口：[Qoder 下载](https://qoder.com/download)、[Qoder CLI 安装文档](https://docs.qoder.com/cli/installation)、[Qoder CLI 发布清单](https://qoder-ide.oss-accelerate.aliyuncs.com/qodercli/channels/manifest.json)、[QoderWake 发布清单](https://download.qoder.com/qoderwake/channels/manifest.json)、[用户提供的钉钉下载页](https://page.dingtalk.com/wow/dingtalk/default/dingtalk/15akajjLwh2sHUAhru7)。

社区包入口：[qodercli-bin](https://aur.archlinux.org/packages/qodercli-bin)、[qoder-bin](https://aur.archlinux.org/packages/qoder-bin)、[qoder-ide-bin](https://aur.archlinux.org/packages/qoder-ide-bin)。AUR 页面可用性和维护状态应在实际贡献时复核。

## 从旧转换器继承什么

[ANOLISA 原型](https://github.com/casparant/ANOLISA/tree/feature/desktop/omarchy-agent-entry/experiments/omarchy-agent-entry) 已经采用“官方 DEB → PKGBUILD → Arch 包”的路线。后续可复用身份和架构校验、桌面入口、图标及协议回调处理。

正式配方应固定版本、官方 URL 和校验和，并能脱离原型的环境变量及手工下载文件构建。转换器可作为导入、检查或个人诊断工具；每个长期维护的软件仍需要清晰、可审阅的独立配方。

## 当前选择

先发布和审阅配方，再完成 Linux 构建与实机验证，然后分别提交 AUR/Omarchy。需要托管厂商二进制时核对该发行包的许可证和重分发条件；公开下载地址本身不等于重分发授权。公开配方默认从官方获取文件，不把上游闭源安装包直接提交到 Git。
