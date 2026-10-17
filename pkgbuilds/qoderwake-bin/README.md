# QoderWake (`qoderwake-bin`)

将官方 Linux 归档打成标准 Arch 包；同时声明 `x86_64` 与 `aarch64`。当前固定 **Wake 1.1.12 + 私有 CLI 1.1.69**，不是从 CLI 最新版动态取依赖。此配方尚未发布到 AUR 或 Omarchy 包源。

## 上游证据（2026-10-17）

- [官方 manifest](https://download.qoder.com/qoderwake/channels/manifest.json) 指定 Wake 1.1.12 与匹配的 CLI 1.1.69，并给出两个 Linux 架构的归档及 SHA-256。
- [官方安装脚本](https://download.qoder.com/qoderwake/install.sh) 会下载软件、改用户 PATH、登录、启动 daemon、打开浏览器；此配方仅安装文件。用户在安装后自行登录与启动。
- 实际下载并校验了两个 Wake 归档及对应 CLI 归档。每个 Wake 归档已有 `qoderwake`、`qodercli/qodercli-wake` 和 `resources/`，其中捆绑的 CLI 与独立 1.1.69 归档中的 CLI 内容一致。
- 静态 ELF 检查：Wake、CLI、`vec0.so` 分别是正确的 x86-64 / AArch64 机器码；`DT_NEEDED` 仅涉及 glibc 及其 loader。CLI 引用的最高 GLIBC 符号版本：x86_64 2.28，aarch64 2.34。Python 是官方安装脚本明确要求的运行时。ELF 机器类型只确认架构，不证明旧 CPU 指令兼容。
- 上游归档没有独立 LICENSE/EULA 文件。[服务条款](https://qoder.com/product-service)未据此确认二进制重分发授权；本仓库只分发配方。公开托管构建包前须完成许可证核对。

| Arch 架构 | 上游标识 | Wake 归档 SHA-256 |
| --- | --- | --- |
| `x86_64` | `linux_amd64` | `30416efe98cba69a89f99f3cddca07756074ba7bd797344d00d6af6f33f3ec1d` |
| `aarch64` | `linux_arm64` | `19c4c9bdd82cfb249806424b1278de9d93e49cc4d36839b9f9eba9730941e159` |

## x86 CPU 兼容范围

Wake 1.1.12 的 Linux amd64 归档捆绑的是标准版 CLI 1.1.69，不是本仓库独立 `qodercli-bin` 选择的 baseline 版本。2026-10-17 核对的[官方 CLI 安装器](https://qoder.com/install)要求 optimized Linux x64 CPU 同时具备 `sse4_2`、`popcnt`、`avx`、`avx2`、`bmi1`、`bmi2`、`fma`；缺失或无法核实时改选 `amd64-baseline`。该检查反映当前独立 CLI 的分发策略，不能据此断言 Wake 捆绑版本的精确 CPU 下限。

**旧 x86_64 CPU 上运行 Wake 及其私有 CLI 的兼容性尚未证实**，可能因上游所用指令集而出现 illegal instruction；`x86_64` 元数据、ELF `e_machine` 和 glibc 依赖检查均不能代替实机运行。Wake 的官方 manifest 没有提供 baseline 归档。本配方保留厂商配套组合，避免未经验证地替换成独立 CLI baseline；若需要支持旧 CPU，应先由上游确认 Wake 与 CLI 的 baseline 支持和配套版本，再增加配方与测试。

## 安装和首次运行

在相应架构的 Arch Linux 环境中，从此目录执行；首次正式发布前应完成仓库文档要求的干净 chroot 构建和实机验收。

```bash
makepkg --verifysource
makepkg -si
qoderwake --version
qoderwake --help
qoderwake login
qoderwake start --host 127.0.0.1 --port 19820
qoderwake status
qoderwake portal
```

可选的用户 systemd unit 随包安装，**默认不启用**。登录后如选择 systemd 管理，应先停止由 `qoderwake start` 启动的实例：

```bash
qoderwake stop
systemctl --user daemon-reload
systemctl --user enable --now qoderwake.service
journalctl --user -u qoderwake.service
```

之后用 `systemctl --user stop/restart qoderwake.service` 管理进程。不要同时让上游 daemon 命令和 systemd 管理同一实例。默认只监听 `127.0.0.1:19820`。unit 的前台启动参数取自上游安装脚本，仍待 Linux 实机验证。

## 文件布局与更新边界

```text
/usr/bin/qoderwake                              # 仓库启动器
/opt/qoderwake/qoderwake                        # 原样保留的上游 Bun 可执行文件
/opt/qoderwake/qodercli/qodercli-wake             # Wake 专用 CLI 1.1.69
/opt/qoderwake/resources/                        # 上游配套资源
/usr/lib/systemd/user/qoderwake.service          # 用户自行启用
/usr/share/licenses/qoderwake-bin/LICENSE.upstream
```

启动器设置 `QODERCLI_PATH` 为精确配套的私有 CLI，不占用 `qoder` / `qodercli` 命令，也不依赖独立 `qodercli-bin` 包。保持工作目录、参数和用户自己的 `QODER_ENV`；未设置时使用官方脚本的 `prod`。`QODERWAKE_HOME` 留给上游处理，默认用户数据目录仍是 `~/.qoderwake`。

升级使用 pacman / AUR helper。启动器拒绝 `update`、`upgrade`、`self-update` 子命令；包内 `/opt` 文件由 root/pacman 所有。**这不等于已禁用所有上游更新入口**：未找到可靠的全局禁用开关，portal 更新流程、后台检测以及持久化 daemon 是否绕过启动器仍须在实机验证。勿通过 sudo 启动程序或在 portal 内更新这个包。若现有 `~/.local/bin/qoderwake` 等用户安装路径排在 `/usr/bin` 前，先用 `type -a qoderwake` 确认入口并手动处理旧安装；此包不会改删用户文件。

上游 Bun 文件含有追加应用数据，使用 `!strip` 和 `!debug`，构建时不执行下载到的二进制。安装、升级、卸载都没有登录或启动服务的 hook。卸载前自行停止 daemon；用户数据保留在用户目录。

## 验证状态

已完成：两个归档的 SHA-256、路径安全和文件布局检查；两架构 ELF 依赖检查；捆绑 CLI 内容与官方匹配版本归档比较；启动器语法和暂存目录安装检查。

当前开发机是 macOS，没有 `makepkg`、Linux 容器或虚拟机。这里的 `.SRCINFO` 按配方字段生成，待 Arch 上用 `makepkg --printsrcinfo` 复核。**尚未完成真实 `.pkg.tar.zst` 构建、Linux 运行、登录、portal、daemon、systemd、升级与卸载测试；两种架构均不标记为实机通过。**

更新版本时同时核对 manifest 中 `qodercli.version` 和归档内 CLI，重新下载两个架构校验，更新 `pkgver`、校验和及本文记录。不要只更新 Wake 版本或换成独立 CLI 最新版。
