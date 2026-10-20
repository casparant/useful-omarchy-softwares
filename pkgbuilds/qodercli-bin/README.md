# Qoder CLI：`qodercli-bin`

状态：本地候选配方，版本 `1.1.73-2`，支持 `x86_64` 和 `aarch64`。已完成上游归档校验和、ELF 架构/动态依赖静态检查，以及双架构 `package()` 目录装配检查（在 macOS 上适配 `install` / `readelf`，核对文件、权限和原始二进制哈希）；另在 Omarchy ARM64 完成 makepkg、安装、包完整性及经默认入口连接 AW 的真实模型、压缩、安全拒绝、RTK 重试、原生禁用、外部 After Hook、后台失联阻断和包升级验证；x86_64 运行、网页登录和中文输入尚待实测。本目录是供现有 AUR/Omarchy 维护流程评审的候选，不向 AUR 新建重复包，不发布二进制。

## 安装与入口

在相应架构的 Arch Linux / Arch Linux ARM 环境中：

```bash
cd pkgbuilds/qodercli-bin
makepkg --verifysource
makepkg -s
sudo pacman -U ./qodercli-bin-1.1.73-2-*.pkg.tar.zst
qodercli --version
qodercli --help
```

一个构建目录只用于一个架构，不要复用另一架构解包后的 `src/`。如配置了 makepkg 的调试包产物，安装时明确选择主包。

- 用户入口为 `/usr/bin/qodercli`；供应商原生程序放在 `/opt/qodercli/qodercli`。官方文档中的 CLI `qoder` 命令，在本包中改用 `qodercli`。
- 不创建 `/usr/bin/qoder`，为 Qoder 桌面应用保留同名命令，避免两个组件相互覆盖。
- 不要求 Node.js；这里使用官方原生可执行文件，不是 npm 发行版。包启动器依赖系统 Python，供应商程序字节保持不变。
- QoderWake 使用自己固定版本的私有 CLI，本包不为它提供或替换后端。
- 包构建、安装均不登录、不运行厂商安装脚本、不启动后台程序、不修改用户配置。登录和开始会话由用户运行程序触发。

## 版本来源与双架构输入

[官方发布清单](https://qoder-ide.oss-accelerate.aliyuncs.com/qodercli/channels/manifest.json)在 2026-10-17 返回 `latest=1.1.73`，发布时间为 `2026-10-16T11:49:05.015Z`。浮动清单仅用于发现版本；PKGBUILD 固定版本 URL 和 SHA-256。

| Arch 架构 | 上游清单架构 / 文件 | 实际复算 SHA-256 |
| --- | --- | --- |
| `x86_64` | `amd64-baseline` / `qodercli-linux-x64-baseline.tar.gz` | `b8f5cddaa851c1847c8575e696e567703bf06c86cd736853cc65714580d4cbab` |
| `aarch64` | `arm64` / `qodercli-linux-arm64.tar.gz` | `aed01a40653c116bfd9a0bbf10e1c015e7fd7d2697512afe69d501e235aa6402` |

两个归档都只含 `qodercli` 主程序。x86 使用 baseline 产物以覆盖更广的 CPU，仍需在目标机器验证；不将选择 baseline 等同于已经测过所有老 CPU。

2026-10-17 静态检查确认两者均为 ELF64 little-endian，机器码分别为 AMD x86-64（62）和 AArch64（183），使用各自架构的 glibc loader，`DT_NEEDED` 为 glibc 及其兼容库（`libc`、`libpthread`、`libdl`、`libm` 和 loader）。可见的最高 GLIBC 符号版本分别为 2.28 和 2.34，配方声明相应的最低 glibc 版本。`package()` 再检查主程序架构；保留 Bun 可执行文件尾部应用数据，使用 `!strip` 和 `!debug`。

## 更新策略

官方[安装与升级文档](https://docs.qoder.com/cli/installation)说明自动更新默认开启，可通过 `general.enableAutoUpdate=false` 关闭；[配置优先级文档](https://docs.qoder.com/cli/settings)说明 `--settings` 的设置高于用户和项目文件，并进行深度合并。

启动器把包内 `/usr/share/qodercli/pacman-settings.json` 与调用方的一份 `--settings` 组合后，仅向原生 CLI 传入一个设置文件。`general.enableAutoUpdate=false` 始终保留，其余调用方字段（包括 AW 的 PreTool/PostTool 和用户 Hook、权限及其他 general 设置）保持原值；不改写用户文件，也不把配置内容放进进程参数。

支持 `--settings FILE`、`--settings=FILE` 及内联 JSON 对象；文件支持 JSON 注释和尾逗号。组合配置是本次启动的快照，放在权限 0600、已取消文件名链接的临时文件，通过 `/proc/self/fd` 交给同 PID 的原生程序；进程退出后由系统回收。文件缺失、非法配置或重复的调用方 `--settings` 会报错并停止，避免悄悄丢失 Hook。`--` 后的字面参数原样保留。

这修复了 1.1.73 的实际冲突：旧启动器前置一份设置，AW 再追加一份，而原生 CLI 对重复 `--settings` 只加载第一份，导致 AW Hook 被忽略。使用 AW 时直接选择默认 `/usr/bin/qodercli`，不需要绕过包入口。

常见的 `qodercli update` 仍返回提示，要求使用包管理器升级。程序树由 root/pacman 管理，普通用户不能覆盖其中的原生程序。该策略不等于对闭源更新器的完整审计；TUI 内更新、其他参数位置的手动更新及长时间运行仍需单独验收。不要以 root 身份运行 CLI 或供应商自更新命令。

`.omarchy/package.json` 使用 `sync: false`，无自动更新 hook。新增版本时先核对发布清单和两个平台的 URL，下载复算校验和，更新 `pkgver` / `pkgrel` / `sha256sums_*`，再在 Arch 中运行 `makepkg --printsrcinfo > .SRCINFO` 并完成双架构验收。

## 与现有 AUR 包的关系

本次通过 AUR 官方 Git 检查了 `qodercli-bin` 的提交 `0c6cd41b68e46e1f056ac71afb51c4a90cbe0ccc`（`1.1.73-1`）：它已支持双架构，使用普通 x64 产物并直接安装 `/usr/bin/qodercli`，附带 shell completion。不能将双架构支持描述为本仓库首创。

本地候选侧重 x64 baseline、架构检查、明确 glibc 依赖和包管理器更新策略；保留其 `qoderclibin` 兼容 provides 和与旧 `qoder-cli` 的冲突声明。本地暂未引入 shell completion。应把有价值的改动作为小补丁交给现有维护者，避免长期维护同名不同实现。

## Linux 验收与上游贡献

- 双架构分别构建并安装，运行 `qodercli --version`、`--help`，检查版本、命令归属和退出码。
- 验证网页登录、终端交互、中文输入、项目初始化及一次测试目录内的会话；不要把真实凭据写进测试输出。
- 与 Qoder 桌面、IDE、QoderWake 同时安装，确认 `/usr/bin/qoder` 未被覆盖、Wake 私有 CLI 未被替换。
- 用隔离用户目录核对自动更新、手动更新和设置合并；比较测试前后包文件的哈希，运行 `pacman -Qkk qodercli-bin`。
- 测试更新、卸载、重装；用户会话和设置保留，包内路径无残留。
- 先审[现有 AUR `qodercli-bin`](https://aur.archlinux.org/packages/qodercli-bin)，向其维护者提交修正或按 Omarchy 当前贡献流程提交单包 PR。此配方独立编写，没有复制未经审阅的 AUR 构建函数。

厂商归档仅包含主程序，未附独立许可证文本，`LICENSE` 记录[官方条款入口](https://qoder.com/product-service)。公开配方不等于已获得公开托管预构建二进制的授权。
