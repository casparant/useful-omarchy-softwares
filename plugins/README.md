# Omarchy 插件

这里维护 Omarchy Quickshell 的桌面插件源码，每个插件独立放置，拥有自己的 manifest、插件 ID、配置和许可证。可安装软件的 Arch 配方仍放在 `pkgbuilds/`；插件负责桌面交互，不另建包管理器。

## 当前插件

| 插件 | ID | 功能 | 状态 |
| --- | --- | --- | --- |
| [Agent Entry](agent-entry/README.md) | `anolisa.agent-entry` | 顶栏快捷入口、终端与应用启动、自定义入口、软件安装说明 | 迁移候选；目标 Omarchy 会话待验收 |

[插件目录](catalog.json)只收录这里维护的公开源码。每个目录都能独立部署；插件之间通过已公开的命令接口协作，不依赖对方源码、私有配置或内部安装路径。

## 目录约定

```text
plugins/
├── catalog.json
├── README.md
└── agent-entry/
    ├── manifest.json       插件 ID、版本、kinds 与 QML 入口
    ├── *.qml               界面
    ├── agent_entry.py      本插件的动作与入口配置
    ├── install.py          普通用户本地部署与备份卸载
    ├── LICENSE / NOTICE    本插件独立许可证与声明
    ├── ORIGIN.md           来源提交与迁移改动
    ├── README.md           部署、使用与验证状态
    └── tests/              不依赖真实账户或软件安装的回归测试
```

`catalog.json` 中的 `files` 是部署与导出的逐文件白名单。新增辅助文件时同时更新该清单及插件安装器的文件清单，避免从目录中顺带发布缓存、测试产物或运行配置。

版本以各自 `manifest.json` 为准。插件 ID 是稳定身份，显示名称可以变；已有用户配置和备份路径迁移前明确处理。插件可含纯 QML/Python，声明双架构不代表所有外部程序都支持双架构或已完成两种设备验收。

## 本地部署

先读对应插件 README。Agent Entry 的本地部署命令，在本仓库根目录、目标 Omarchy 的普通用户终端中执行：

```bash
python3 plugins/agent-entry/install.py
# 可选：登录桌面后显示 Dashboard
python3 plugins/agent-entry/install.py --replace --autostart
```

安装器只部署插件及自身入口；软件安装按 `pkgbuilds` 文档另行完成。首次启动不自动安装应用、不代替应用登录。与此前相同 ID 的插件共用配置，覆盖升级会先备份旧插件。

开发时也可以按官方插件机制手工复制或软链接整个目录，再执行 rescan/enable；不要在插件目录内部创建指向外部文件的软链接。具体操作以 [Omarchy 官方手册](https://github.com/omacom/omarchy/blob/quattro/manual/32-shell-plugins.md)为准。

## 从单仓库维护到独立分发

Omarchy 的 `plugin add <Git URL>` 要求所克隆仓库的**根目录**有 `manifest.json`。本仓库根目录是软件维护项目，`plugins/agent-entry` 是源码子目录，所以不能把本仓库地址或 GitHub 的 `/tree/...` 页面直接作为它的安装源。

先导出一份完整、独立的目录：

```bash
tools/check-plugin agent-entry
tools/export-plugin agent-entry /tmp/agent-entry-export
```

输出路径必须尚不存在。导出只复制白名单文件，根目录包含 manifest、QML、Python、README、许可证和来源声明；不会创建远端仓库、执行 git push 或启用插件。

正式公开分发时，将导出目录发布到独立插件仓库。它的默认分支根目录保持上述布局，用户再通过 `omarchy plugin add <独立仓库Git地址> --enable` 安装；后续更新由那个仓库的 Git 历史和 `omarchy plugin update` 管理。统一源码仍在这里维护，发布时重新导出并审阅差异，避免同时手工维护两份实现。[官方安装命令实现](https://github.com/omacom/omarchy/blob/quattro/bin/omarchy-plugin-add)

## 检查与验收

```bash
tools/check-plugin
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s plugins/agent-entry/tests -p 'test_*.py' -v
# 目标 Omarchy 中执行
omarchy plugin validate plugins/agent-entry
```

仓库静态检查覆盖目录、manifest、ID、入口路径、逐文件白名单、Python 语法和许可证；根目录测试需与每个插件的 tests 分别运行；独立导出只包含运行文件，不携带测试。Python 单测使用临时配置与模拟进程，不启动 Agent、不读取凭据、不安装软件。CI 另执行固定提交的官方 manifest 验证器。

QtQuick 离屏渲染只检查通用界面，不能证明 Quickshell 面板加载成功。目标验收还需覆盖：顶栏打开/关闭、项目目录、各应用入口、注册入口、登录后显示、升级备份与卸载，以及 x86_64/aarch64 目标机上的实际依赖。结果按插件和版本记录，未验证的项目继续保留。

## 许可证

本目录各插件以自身 LICENSE/NOTICE 为准。`agent-entry` 从 ANOLISA 公开源码迁入，保留 **Apache-2.0** 及来源声明，不受仓库根目录原创代码的 0BSD 授权替换。其他插件应独立记录来源和许可证，不能仅因放在同一目录就重新授权。
