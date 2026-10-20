# AW Preview：一键安装与启动

在 Omarchy 图形会话的普通用户终端，从仓库根目录执行：

```bash
./omarchy-tools aw
```

这条命令准备 `binutils` / `fakeroot` 重打包工具，下载并校验适合当前架构的 Qoder CLI 和 AW 预编译包，通过 pacman 安装，部署或备份更新 Agent Entry 面板，然后进入 AW 首次配置。无需安装 Rust 或编译 ANOLISA。首次仍需确认 pacman 安装、选择安全策略，并在需要时完成原生登录与 sudo 授权；不使用免确认权限模式。

1. 接受默认 `/usr/bin/qodercli`，选择 Tokenless 或 Tokenless + sec-core。
2. 启用安全检查时，通过 sudo 启动专用系统服务，认证健康检查成功后才生成配置。
3. 已登录账号继续复用；未登录时进入 Qoder 原生登录。入口不保存令牌。
4. 进入 Qoder 后即可请求工具操作。之后点击 Panel 的 **AW** 卡片，或执行 `aw-launch`。

Panel 的 **Qoder CLI** 是原生直连入口；**AW** 才会使用所选 Provider。安装后也可从应用菜单打开 AW。Panel 不把“找到命令”显示成“安全检查已生效”。已有配置、用户 Hook 与原生权限保留；日常启动只检查、复用安全后台，失联拒绝启动，不自动关闭安全策略。

如果只需安装文件，执行 `./omarchy-tools install qodercli aw`；部署面板使用 `./omarchy-tools panel --replace`。一键入口要求支持插件接口的 Omarchy 图形会话、Python 3.9+、makepkg/pacman 和 sudo。模型账号、网络访问和必要的系统授权由使用者准备。

## 固定二进制与来源

本候选使用 [ANOLISA 696e1aa0](https://github.com/agentic-os-org/ANOLISA/tree/696e1aa0c02e9c6a6817bc68c2101f7034d52c59) 的同批 Preview 合同，交付 AW core、Tokenless/RTK 与 sec-core Provider/CLI/daemon。包内版本是 `0.1.0-preview.1`，Arch 快照版本是 `0.1.0.preview20261020-1`。不包含 Sight，不代表完整 Tokenless 或 sec-core 生命周期能力。

下载来自维护者的[固定演示 Release](https://github.com/kongche-jbw/anolisa/releases/tag/aw-demo-20261020-696e1aa0)，不是 ANOLISA 正式发行。x86_64 来自[通过的上游 Integration](https://github.com/agentic-os-org/ANOLISA/actions/runs/39338250584)，aarch64 使用同一源码、Rust 1.97.1、锁定依赖与 `aw-build --component all` 在 Ubuntu 24.04 ARM64 原生构建。目标需要 glibc >= 2.39。配方为每个架构固定 URL 和 SHA256，不使用 `latest` 或会过期的 Actions 下载链接。

`makepkg` 只做二进制重打包：上游原生安装器先校验清单，将文件放入私有构建暂存目录；`package()` 把暂存文件放入 pacman 包。系统安装由 pacman 管理，保留三份原始组件回执、文件哈希、权限、LICENSE/NOTICE 和 RTK 来源/补丁。不在包安装阶段启动服务或改用户配置，也不把 Qoder 厂商程序上传到本项目 Release。

系统前缀为 `/opt/aw-preview/0.1.0.preview20261020-1`，命令为 `/usr/bin/aw`、`/usr/bin/aw-package` 和 `/usr/bin/aw-launch`。不要对 pacman 管理的前缀另行执行 `aw-package install/uninstall`。Qoder 使用本仓库 `qodercli-bin 1.1.73-2`，默认包装器同时保留禁止自更新和 AW Hook。

## 首次配置与日常启动

以普通用户执行，`--qoder` 换成实际已安装的绝对路径。配置和状态放在用户拥有的目录。若已有用户目录中的 `aw` / `aw-package` 链接，先核对 `command -v aw`，避免 PATH 仍选择旧包；下例显式使用本包的 `/usr/bin` 入口，不覆盖旧链接：

```bash
AW_PREFIX=/opt/aw-preview/0.1.0.preview20261020-1
install -dm700 "$HOME/.config/aw" "$HOME/.local/state/aw-preview"
/usr/bin/aw-package configure --prefix "$AW_PREFIX" \
  --config "$HOME/.config/aw/preview.yaml" \
  --state-dir "$HOME/.local/state/aw-preview/runtime" \
  --provider tokenless --qoder /usr/bin/qodercli
/usr/bin/aw validate --config "$HOME/.config/aw/preview.yaml"
/usr/bin/aw inspect --config "$HOME/.config/aw/preview.yaml" --json
/usr/bin/aw run --config "$HOME/.config/aw/preview.yaml" --agent qoder
```

Tokenless 使用 PreTool 重试建议和 PostTool 单文本结果替换；PostTool 不依赖 RTK，PreTool 使用回执校验的受管理 RTK。失败结果保留原样，恢复能力为 `none`，不声称启用了 Tokenless 全部生命周期能力。[上游能力与限制](https://github.com/agentic-os-org/ANOLISA/blob/696e1aa0c02e9c6a6817bc68c2101f7034d52c59/docs/user-guide/zh/user-entrypoint/aw/tokenless.md)

`aw inspect` 只读，不启动 AW/sec-core 后台、不扫描、不压缩。Tokenless 展示是存储窗口内的估算统计；已配置、进程在线、Provider 准入、实际原生效果不是同一状态。保持原契约的 `unknown` / `unverified`，不把健康状态包装成安全覆盖证明。

## 可选 sec-core

优先连接已有可信 root sec-core 后台。只在需要本包独立后台时显式执行：

```bash
sudo systemctl enable --now aw-preview-sec-core.service
```

该独立 unit 使用专有 socket `/run/aw-preview-sec-core/daemon.sock`、数据 `/var/lib/aw-preview-sec-core` 和日志目录 `/var/log/aw-preview-sec-core`，不会覆盖已有 `agent-sec-core` 服务。策略配置参考 [skillsec.json](skillsec.json)；本候选关闭默认技能目录发现，避免与现有后台同时管理用户技能目录；AW 的显式代码检查仍走同一后台。若需要技能目录扫描，应单独配置归属并验收，不宣称已覆盖全部 sec-core 能力。

以普通用户显式诊断（只探测已运行后台）：

```bash
AW_PREFIX=/opt/aw-preview/0.1.0.preview20261020-1
"$AW_PREFIX/libexec/aw/providers/sec-core/aw-provider-sec-core" --health \
  --helper "$AW_PREFIX/libexec/aw/providers/sec-core/agent-sec-daemon-health" \
  --socket /run/aw-preview-sec-core/daemon.sock
```

需安全检查时，用新的配置文件执行上面的 `configure`，将 `--provider tokenless` 换成 `--provider sec-core+tokenless --socket /run/aw-preview-sec-core/daemon.sock`。初始化拒绝覆盖已有配置。生成配置中执行前安全扫描失败会阻断，随后才是 Tokenless 重试建议；建议命令作为新调用重新接受安全和原生权限检查。执行后保留 sec-core 完成观察，再压缩；OpenClaw 按原生 API 顺序先压缩，完成观察保留原始结果和完成字段。外部 Hook 的调度不由本包改写。

健康成功仅表示经过 root peer 认证的后台可达；`admission` / `check_result` 仍为 unknown，且诊断入口独立于 `aw inspect`。[上游诊断边界](https://github.com/agentic-os-org/ANOLISA/blob/696e1aa0c02e9c6a6817bc68c2101f7034d52c59/docs/developer-guide/zh/aw/sec-core.md)

## 升级、卸载与数据

这是人工维护的 Preview，`.omarchy` 保持 `sync=false`。每次源码或配方变化都发布新版本/`pkgrel`，前缀包含两者。升级前退出 Agent、用旧版本及旧配置执行 `aw stop --config ABS`，若启用了独立安全后台则 `sudo systemctl disable --now aw-preview-sec-core.service`，备份用户配置，然后用 pacman 升级。升级后重新生成并审阅配置，合并自己的策略，验证后再启用后台和启动 Agent。不要直接改写旧配置中的 RTK 哈希，或绕过校验。

pacman 会移除旧前缀；本候选不提供无缝迁移，不自动重写配置，旧配置可能因旧执行路径消失而拒绝运行。即便只变更 `pkgrel`，也必须执行上述迁移。回退安装保留的旧 `.pkg.tar.zst` 并恢复对应配置；新后台的数据兼容性需在升级前另外确认。

卸载前同样先停止 AW 和本包独立 unit，再执行 `sudo pacman -R aw-preview`。用户配置、统计、恢复数据和安全后台数据保留，由用户确认后清理；不停止其他 sec-core/Sight 服务。安装不启用 unit，卸载前手工停用是当前生命周期约束。

## 验证与许可

2026-10-20：宿主与 Omarchy ARM64 的 119 项根回归通过，38 项插件回归通过。VM 从固定 Release 下载并校验 ARM64 包，经统一入口完成安装、面板部署、首次配置与实际模型工具调用。默认 Qoder 包装器仅传入一份设置，关闭自动更新与 AW Hook 同时存在。JSON 压缩、安全拒绝、包内 RTK 建议重试、原生 Bash 禁用、后台失联阻断、外部 After Hook 和重复启动复用均通过。Panel 实际点击打开 AW 原生登录衔接；模型测试使用临时 PAT 环境，不声称完成了浏览器登录。自动化覆盖双架构下载/校验、安装回执、配置步骤顺序、只读 inspect、Qoder 设置合并、面板入口和一键流程失败中止。真实模型验证使用 Omarchy ARM64 VM；x86_64 笔记本需最终现场登录与运行确认。统计是工具样本的估算，不是账单节省承诺。

本仓库原创启动器保留 0BSD，ANOLISA/RTK 保留各自 Apache-2.0 许可与来源材料。该候选保持 `sync=false`，未自动发布到 AUR 或 Omarchy 官方源。
