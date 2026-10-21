# cosh / herdr / AW 会话工作台 PoC

2026-10-21，插件 0.7.0。cosh 是 AI Shell 入口；herdr 保留真实终端与进程，
AW 在 Qoder 首次启动前装配 Hook。Panel 查询会话和策略证据，不启动 Agent。

## 安装与使用

本 PoC 要求 Linux、`/proc`、用户的 `XDG_RUNTIME_DIR`、foot 等终端，以及已安装的
cosh、herdr、AW Preview 和 Qoder CLI。本机验证组合为 ARM64 Omarchy、
cosh 0.27.0、herdr 0.9.1、AW 0.1.0.preview20261020-2、Qoder CLI 1.1.73。
未新增厂商二进制分发或声称 x86_64 桌面验收通过。

在普通桌面用户终端部署：

```bash
./omarchy-tools panel --replace
# 首次使用：创建专用配置，并安装 herdr 官方 Qoder 会话身份 Hook。
# Qoder 原生配置目录需要已经存在；不读取或代填 PAT。
aw-session setup
```

AW 首次配置未完成时先运行 `aw-launch`。其现有首次配置、可选安全授权、
Qoder 原生目录信任、登录和工具权限均保留。完成后可退出这个独立初始化会话。
日常从应用菜单 **cosh · AI Shell** 或管控面 **打开 AI Shell**（cosh） 进入：

```bash
# 在真正的 cosh 提示符下执行；当前目录就是本次 Agent 项目。
aw run --agent qoder
```

Qoder 在新 herdr 工作区中经 AW 启动。无需配置 cosh 自身模型才能管理或返回 Qoder；
使用 cosh 自身的 AI 功能仍需其原生 `/auth`，与 Qoder 的登录独立。

- 在 cosh 完整界面中，`Ctrl+B` 后按 `W`：使用 herdr 原生工作区选择器，在 AI Shell 与 Qoder 之间切换。
  Panel 的“返回”打开专用 Qoder 终端，返回 AI Shell 请点击“打开 cosh”。
- `Ctrl+B` 后按 `Q`，或关闭 Foot 窗口：离开界面，保留后台终端与 Qoder。
- 再次打开 cosh：默认回到 AI Shell，不新建 Qoder。通过运行视图或 Panel 的 **返回**
  连接已有会话；返回失败不会偷偷启动一个替代进程。
- 需要终止时，在 Qoder 原生界面 `/exit`，或使用 herdr 原生关闭工作区/窗格的确认操作。
  关闭 Panel 仅停止查询。

这是独立的桌面启动衔接，未修改 cosh 厂商二进制，也不声称新增了 cosh 内核 Qoder adapter。
AI Shell 与运行视图当前使用真实终端和 herdr 原生选择器，不伪装成新的 cosh 原生标签栏。
旧的软件目录保留原生直连入口，直连进程会标为未托管。

## 统一的 aw run 入口

本 PoC 的日常用户命令是 **cosh 内的 `aw run --agent qoder`**。该插件在自己的 cosh
Bash 后台加载局部 `aw` 函数；不创建 PATH 上的 aw 替身、不修改厂商二进制、
`~/.bashrc` 或其他终端。函数将 Qoder run 交给 herdr 创建终端，再在其中执行固定
绝对路径的原生 AW，保留原生登录、目录信任和工具权限。

省略 `--config` 时使用 `$XDG_CONFIG_HOME/aw/preview.yaml`。显式 `--config FILE`
用于该会话的配置快照；`--native-settings`、原生 profile/state-dir 选项及 `--` 后的
Agent 参数按参数数组保留，仍由原生 AW 验证。未知或缺值的受管启动参数报错，
不会静默退回未托管 Qoder。启动适配函数不会传入 Qoder 的工具子进程。

其他 AW 子命令原样交给原生 AW；其他 Agent 目标暂不声称完成 herdr 托管。
在普通终端执行的是原生 AW，仍需它要求的 `--config`，也不自动登记为本 PoC 的会话。
`aw-session` 只保留管理员 setup/list 及旧入口兼容，不再出现在日常启动流程。
从旧 PoC 升级时，旧 cosh 后台不会因关闭窗口而重启；管理员可在闲置的 AI Shell
中 `source ~/.config/omarchy/plugins/anolisa.agent-entry/cosh-aw.bash` 刷新入口，
已有 Qoder 保持运行。本机 VM 的旧 cosh 后台已刷新。

## 日常标准 POC 流程

以下是在软件、AW 策略和 Qoder 登录已配置后的基础闭环；不要每次重新安装或登录。

1. 点击顶栏 AW → **打开 AI Shell**，进入 cosh。先确认目录，必要时执行
   `cd /home/you/project`。cosh 的“尚未配置 AI /auth”只涉及它自身模型，与 Qoder 独立。
2. **新建**：在 cosh 提示符执行一次 `aw run --agent qoder`。herdr 新建终端，AW 固定
   配置并启动 Qoder。**继续已有会话**：在 herdr 左侧/工作区选择器选已有 Qoder，
   或点击 Panel 的“返回”；不再执行 run。
3. 等待 Qoder 原生界面就绪。首次登录、目录信任和权限在这里完成；已经登录则直接继续。
   Panel 应出现真实 Qoder 活会话及 AW Hook 绑定。若未确认或后台不可达，先查详情。
4. 在 **Qoder 对话输入框**发送“只运行 pwd，不修改文件，完成后回复 POC_FLOW_OK”。
   若出现权限确认，检查实际命令后选择 **Allow once**。Tokenless 可能要求用 RTK
   包装重试；这不是 sec-core 拒绝，不要永久放行 env。等待真实结果与回复。
5. 关闭 cosh/Foot 窗口，保持 VM 与 herdr 后台运行。重新“打开 AI Shell”，再选原 Qoder
   或 Panel“返回”。应保留原对话和结果；详情中的对话 ID、PID、窗格、策略版本和 AW
   运行代次不变。`Ctrl+B` 松开后按 `W` 打开选择器；这里是 Control，不是 Mac Command。
6. 真正结束在 Qoder 内执行 `/exit`。Panel 应显示已退出；之后的 `aw run --agent qoder`
   是新会话。关闭窗口、退出 Qoder、关闭 VM 是三种不同操作。

管理员可在另一个普通终端运行 `aw-session list` 对比身份；不要把这个命令输入 Qoder
对话框后当作本机诊断。压缩数字是组件历史估算，不要求每次小任务都产生正收益，
也不能替代当前会话的 Hook 绑定证据。VM 重启恢复不属于这次基础闭环。

### 输错命令与网络排查

本机安装的原生 CLI 命令为 `qodercli`，没有 `qoder` 命令。基础 POC 使用
`aw run --agent qoder`，直接执行 `qodercli` 会绕过本托管入口。输入缺失命令时可能看到
mise 的版本查询、下载重试或限流；这不表示 AW Hook 已执行。
2026-10-21 本机对 `mise-versions.jdx.dev` 的正常 TLS 校验失败，属于独立网络信任问题；
未关闭 TLS 校验、未导入未知证书。已安装工具的标准 POC 不需要这些版本查询。

## 生命周期和策略证据

专用 herdr 会话名为 `anolisa-cosh`；不会连接用户的 default 或其他命名会话。
配置位于 `$XDG_CONFIG_HOME/anolisa/cosh-herdr.toml`。首次显式打开才启动专用后台，
只读查询不会安装软件、启动后台、读取终端文本、发模型请求或修改策略。
`aw-session setup` 是显式配置动作，使用 herdr 官方集成修改 Qoder settings；
厂商软件仍由各自包管理器维护。

每次新建会话在 `$XDG_RUNTIME_DIR/anolisa-cosh/<随机ID>/` 创建 0700 私有目录，
保存 0600 配置快照及脱敏运行收据。保留全部 Provider、事件步骤、条件与异常动作，
仅隔离 daemon 的 state_dir 与 endpoint。每个会话使用独立 AW 实例；组件 Tokenless 存储仍沿用
用户原来选择的持久目录，因此全局压缩数字继续标为组件历史估算，不是会话账单。

Panel 的 **AW Hook 已绑定** 必须同时满足：

1. 专用 herdr 中仍有对应终端，监督进程 PID 和启动时间匹配，Qoder 是该进程的活后代。
2. 私有配置快照的摘要没有变化，`aw inspect` 返回在线实例及配置版本、运行代次。
3. Qoder 的原生 `--settings` 内存描述符中，Before/After 的 AW Hook 步骤和异常动作完整匹配。
4. 每个 Hook 的私有 binding 都指向本会话 socket，原生 identity 的版本和运行代次与在线实例一致。

只输出会话 ID、项目、PID、原生对话 ID、摘要、代次及过滤后的步骤状态；不输出
binding 的 audit_key、原生 settings、工具内容、Provider 参数或认证数据。
这证明具体原生 Hook 的绑定；AW 公开 API 的 adoption 仍为 `unverified`，不改写为已采用。
后台健康与单次操作放行/拒绝分开，条件策略也不推断为所有调用都执行了检查。

组件是否绑定还要求固定快照中有启用的对应 Hook 步骤，不能只看 Provider enabled。
保存新配置不会影响已有会话；新会话读取新配置。没有热更新开关。
运行状态来自 herdr 的 Qoder 终端画面识别，无法分类时显示待确认；对话 ID 来自官方
SessionStart 集成。用户自己直接启动的 Qoder 只显示 PID/项目及未托管，不推断 AW 接入。

查询受时间、输出与记录数量限制。失败会清除旧绑定状态，进程退出后不会继续显示绿色。
多个终端客户端可连接同一后台；日常关闭窗口不会停止 herdr 服务。

## 本轮范围

目标是 **关闭客户端再重开，恢复同一活进程、同一对话和同一终端**。
本 PoC 将专用配置的 `resume_agents_on_restore` 设为 false，VM 或 herdr 服务重启续接
留待后续实现；不会用裸 `qodercli --resume` 绕过 AW，也不会将布局恢复称为进程恢复。
配置、快照、运行收据和账户数据不提交到仓库。

上游参考：[herdr Qoder 集成](https://herdr.dev/docs/integrations/#qoder-cli)、
[恢复边界](https://herdr.dev/docs/session-state/)、
[cosh 交互模式](https://agentic-os.sh/docs/user-guide/user-entrypoint/cosh-ng/quickstart/)。

## 验证与验收

```bash
tools/check-package
tools/check-plugin
python3 -B -m unittest discover -s tests -v
python3 -B -m unittest discover -s plugins/agent-entry/tests -v
QT_QPA_PLATFORM=offscreen python3 plugins/agent-entry/tests/render_control.py .cache/workbench
# 已有受管 Qoder 会话后，在 VM 桌面用户下显式运行；不请求模型或代答权限。
python3 plugins/agent-entry/tests/live_herdr.py MANAGED_ID .cache/herdr-live/lifecycle.json
```

运行现场恢复脚本前先关闭目标会话已有的专用返回窗口，避免两个直接连接争夺输入。
脚本只关闭它自己创建的 Foot 客户端，不终止 Qoder 或 herdr。
对比关闭前、关闭后、普通重开、直接返回四个节点的托管 ID、窗格、Qoder PID、
对话 ID、AW 配置版本及运行代次，并检查普通重开默认进入 cosh AI Shell。
单测另外覆盖绑定失配、步骤缺失/异常动作改变、配置篡改、PID 复用、失联清理、
私有文件权限与过期返回不重启。Qt 离屏检查是布局与交互测试，不冒充桌面截图。

2026-10-21 ARM64 本机 VM 已通过四节点身份一致性验收。随后同一对话完成真实模型的
`pwd`、`ls -la` 只读验收，返回 `HERDR_AW_RECOVERY_OK`；有安全、优化、完成观察、压缩
活动记录。Qoder 原生 RTK 重试只批准一次，自动更新仍关闭；未永久放行 env。
具体机器运行证据保存在本机私有测试目录，未作为公共 UI fixture。

## 卸载

`./omarchy-tools panel --uninstall` 移除插件自己部署的入口，保留应用、账户和用户配置。
先结束所有受管 Agent，再在明确要停止整个专用后台时运行：

```bash
HERDR_CONFIG_PATH="$HOME/.config/anolisa/cosh-herdr.toml" herdr --session anolisa-cosh server stop
```

不要为了更新面板而停止后台或删除运行目录。VM 本身正常关机即可结束本次运行；
本轮不承诺重启后恢复。herdr 官方集成如需移除，使用其 `integration uninstall qodercli`，
不要删除整个 Qoder settings 或认证目录。
