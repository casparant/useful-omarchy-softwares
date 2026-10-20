# Agent 管控面 PoC

这是用于讨论交互的原型，不是 cosh/herdr 集成或 AW 热更新的正式交付。
桌面默认保留一个低干扰的 Agent 入口；点击打开右上角摘要，
再进入详细管控页。软件目录仍保留安装和原生应用入口。

## 交互分工

- **cosh 是应用入口**：AI Shell 用于交互，计划通过快捷方式切换到运行视图。
  运行视图由 herdr 提供终端托管和 Agent 运行状态，不要求用户先登录模型。
- **herdr 是运行视图的支撑组件**：不在桌面另做一个并列的应用入口。
  查看、切换和关闭视图不应重新启动或终止 Agent。
- **AW 提供组件与策略管控能力**：Panel 展示 Hook、Provider 状态及活动；
  用户的任务输入和权限确认继续在原生 Agent 中完成。

当前 PoC 能打开已经安装的 `cosh` / `cosh-shell` / `cosh-ng`，但不安装它们，
也不实现 cosh 内部模式切换。详情中的「运行视图」明确标为待接入。
本地启动入口被发现，不等于版本兼容、登录完成或会话正在运行。

## 真实查询与展示边界

复用已发布预览包的只读命令：`aw-package config show`、`aw inspect --json`
及 sec-core Provider 的 health 查询。查询不开启后台、不发模型请求、
不执行安全扫描或压缩。沿用输出大小、超时、路径信任和健康回执校验。

| 展示 | 来源与含义 |
| --- | --- |
| Hook 链 | 文件中的 Before / After 步骤顺序，保留关闭步骤、条件、异常动作和自定义步骤 |
| Tokenless | 最多 200 条组件历史记录的估算收益；不等于会话账单或模型采用 |
| sec-core | 后台认证可达性；不等于本次调用准入或安全结论 |
| 最近活动 | 当前 AW 服务代次最近 5 条步骤记录；不绑定到猜测的 Agent/PID |
| 策略与会话 | 明示运行时版本和会话绑定未接入；不从配置或进程存在推导“已生效” |

只投影 Hook 类型、启用状态和错误处理动作，不输出配置值、自定义名称、
命令、工具内容或认证数据。自定义步骤保留在原位置；本原型不修改实际 Hook。
展示配置顺序不代表所有 Adapter 的原生回调总顺序：例如 OpenClaw 的原生完成
观察存在独立时序；Qoder 的 AW After 串行不应影响外部 Hook 调度。

## 热更新边界

[ANOLISA #8460](https://github.com/agentic-os-org/ANOLISA/pull/8460)
当前提供 `aw validate --config CANDIDATE --against BASELINE` 的离线范围比较，
不提供运行时激活。PoC 不调用该尚未进入预览包的命令，也不提供伪热更新开关。
正式产品需要等待实例策略版本、空闲边界激活和明确的失败回退。
Provider 独立交付同样保留其独立生命周期；本 PR 不修改包配方或运行版本。

## 试用与回退

在支持 Quickshell 插件的 Omarchy 会话中，从本 PR checkout 运行：

```bash
./omarchy-tools panel --replace
```

替换前安装器会备份现有插件，保留应用配置、认证和权限。
不加 `--autostart` 不会新增登录后弹出行为。若已有用户主动启用的自动打开设置，
本次保留。关闭摘要后停止周期查询；右上角位置是本 PoC 的简化选择，
多显示器、竖向顶栏以及 Omarchy 弹窗统一键盘导航尚待工程化。

桌面登录状态、AW Provider 和 cosh 是独立依赖。查看本地组件状态无需 Qoder PAT；
实际模型请求仍由 Agent 的原生认证流程负责。
从 cosh 的终端使用现有 `aw-launch` 可继续启动预览包的受控 Qoder，
原生目录信任、权限确认及安全检查保持；直接运行 `qodercli` 不会自动接入 AW。

返回上一版：checkout 原版本后再次运行 `./omarchy-tools panel --replace`。
卸载仅插件：`./omarchy-tools panel --uninstall`，不删除应用或账户数据。

## 验证

```bash
tools/check-package
tools/check-plugin
python3 -B -m unittest discover -s tests -v
python3 -B -m unittest discover -s plugins/agent-entry/tests -v
# 安装 tests/requirements-qt.txt 所列依赖后：
QT_QPA_PLATFORM=offscreen python3 plugins/agent-entry/tests/render_control.py .cache/control-plane
```

覆盖真实配置投影、Before/After 顺序、自定义和关闭步骤、异常阻断与扣留结果、
隐私过滤、原生 cosh 命令发现、双语、窄屏、错误后清除旧状态和入口动作。
Qt fixture 是界面测试数据，不是现场运行或模型采用证明。

原型不要求改 Omarchy 主仓库或复制内置 Agents 插件的账户逻辑。
参考 [Omarchy 插件手册](https://github.com/omacom/omarchy/blob/quattro/manual/32-shell-plugins.md)
和 [顶栏交互](https://github.com/omacom/omarchy/blob/quattro/manual/05-the-top-bar.md)。
