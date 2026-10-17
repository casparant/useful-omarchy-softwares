# 首次落地验证记录

日期：2026-10-17。维护环境：Darwin arm64，Python 3.9.6、Bash 3.2、系统 bsdtar。没有 makepkg、Docker/Podman 或 Linux 虚拟机；没有执行或触发远端 CI。

## 已完成

| 配方 | 固定版本 | 来源与架构 | 文件暂存 |
| --- | --- | --- | --- |
| qoderwake-bin | 1.1.12-1，私有 CLI 1.1.69 | 两个 Linux 归档实际下载，SHA-256、ELF 架构、动态依赖表、配套 CLI 一致性通过 | 两架构各 169 个文件，厂商二进制及资源保持原样 |
| qodercli-bin | 1.1.73-1 | x86_64 baseline / aarch64 实际下载、SHA-256、ELF 与动态依赖表通过 | 两架构的预期文件、权限及原始二进制哈希通过 |
| qoder-bin | 0.4.8-1 | x86_64 官方固定版本 DEB 实际下载，完整版本、SHA-256、ELF 与布局通过 | prepare/package 临时装配、入口和许可证链接通过 |
| qoder-ide-bin | 1.33.0-1 | x86_64 官方固定版本 DEB 实际下载，完整版本、SHA-256、ELF 与布局通过 | prepare/package 临时装配、入口和许可证链接通过 |

CLI 和 GUI 的 macOS 暂存检查使用等价的 GNU install -D 目录创建适配器，以及读取真实 ELF 头的 readelf 适配器；不是原生 makepkg 构建。GUI 两包的文件列表已比较，没有文件路径冲突；共享的 URL 协议仍需真实会话检查。

仓库检查结果：

- `tools/check-package`：四个包通过静态检查；明确输出 makepkg unavailable。
- `python3 -m unittest discover -s tests -v`：41 项通过。覆盖来源/元数据、导出不覆盖、manifest 变更、启动器参数与环境、CI 验证逻辑。启动器使用 inert stub，CI 逻辑使用 mock；这些单测不证明上游程序在 Linux 运行成功。
- Python 编译检查通过；两份 workflow 可解析为 YAML；全部 Markdown 相对文件链接可解析，文本空白检查通过。
- `tools/check-updates`：Wake 1.1.12、CLI 1.1.73 与当时官方清单一致，逐架构 URL/SHA-256 匹配；Wake 配套 CLI 为 1.1.69。
- `tools/build-matrix`：生成六个原生 Linux 任务，Wake/CLI 各两个架构，GUI 各一个 x86_64 任务。

各包的完整下载 URL、SHA-256、布局及限制见对应 README；钉钉已有配方的检查范围见 [钉钉记录](software/dingtalk.md)，没有把上游的构建结果算成本仓库实测。

## 待 Linux 环境执行

`.SRCINFO` 已按配方字段准备为候选元数据，仍需真实 `makepkg --printsrcinfo` 比对。未产生或安装真实 `.pkg.tar.zst`；尚未验证依赖解析、升级、卸载、认证、Wake portal/daemon/systemd、GUI/Hyprland、协议回调、自更新及老旧 CPU 兼容。

[构建 CI](../.github/workflows/build.yml)已配置，复用 Omarchy 官方构建仓库提交 `29c89f78d85e1c9330a1bc1614c04daecb219cc3`。首次推送后才会产生远端结果；CI 构建、安装和 CLI version/help 的预期范围见 workflow，不能把配置文件和 mock 测试当成已执行证据。CI 不上传专有二进制附件。

完成远端构建后记录运行 URL、提交、镜像/架构和每项实际结果，再按 [测试流程](testing.md)补齐实机验收。未验证项继续保留，避免把“构建通过”升级成“全部功能可用”。
