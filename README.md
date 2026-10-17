# Useful Omarchy Softwares

为 Arch Linux / Omarchy 维护实用软件的标准包配方、适配记录与测试流程。先把包做成独立可审阅的 `PKGBUILD`，再参与 AUR 维护或向 Omarchy 官方包仓库贡献。

当前以 QoderWake 为首包，扩展到 Qoder CLI、桌面版和 IDE；钉钉复用已有 Omarchy 配方。这里保存配方和自己编写的辅助代码，第三方软件在构建时从官方地址下载。

## 软件目录

| 软件 | 本地配方 | 架构 | 进度 |
| --- | --- | --- | --- |
| QoderWake 1.1.12 | [qoderwake-bin](pkgbuilds/qoderwake-bin/README.md) | x86_64 / aarch64 | 已验证来源、ELF 和暂存布局；待 Linux 构建与运行 |
| Qoder CLI 1.1.73 | [qodercli-bin](pkgbuilds/qodercli-bin/README.md) | x86_64 / aarch64 | 本地候选；参与现有 AUR 包维护 |
| Qoder Desktop 0.4.8 | [qoder-bin](pkgbuilds/qoder-bin/README.md) | x86_64 | 本地候选；待 Linux/Wayland 验证 |
| Qoder IDE 1.33.0 | [qoder-ide-bin](pkgbuilds/qoder-ide-bin/README.md) | x86_64 | 本地候选；待 Linux/Wayland 验证 |
| 钉钉 | [安装与调研](docs/software/dingtalk.md) | 上游配方声明双架构 | Omarchy 已有 dingtalk-bin，不重复打包 |

完整来源、维护归属和验证状态见 [catalog.json](catalog.json)。`aarch64` 指 Linux ARM64；不会将 x86 软件改标为 ARM。GUI 两包目前没有确认官方 Linux ARM 产物。

## 在 Arch Linux 上构建首包

先审阅 [QoderWake 配方](pkgbuilds/qoderwake-bin/PKGBUILD) 和[包说明](pkgbuilds/qoderwake-bin/README.md)，再使用普通用户执行：

```bash
sudo pacman -S --needed base-devel git python
cd pkgbuilds/qoderwake-bin
makepkg --verifysource
makepkg -s
sudo pacman -U ./qoderwake-bin-1.1.12-1-*.pkg.tar.zst
```

安装只放置文件，不会登录或启动 Wake。首次运行、可选用户服务、私有配套 CLI、自更新限制见包说明。系统依赖由 pacman 管理；用户数据保留在软件自己的用户目录。

宿主机不是 Arch 时，可在有 Docker/Podman 的 Linux 环境或 Omarchy 官方构建仓库中构建，见[测试流程](docs/testing.md)和[发布流程](docs/publishing.md)。本轮开发环境是 macOS ARM；没有把本地暂存检查写成 Linux 构建或实际可用性验证。

## 检查与维护

仓库工具使用 Python 3.9+ 标准库：

```bash
tools/check-package
python3 -m unittest discover -s tests -v
tools/check-updates
```

- `check-package [pkgbase]` 检查语法、元数据、固定来源和本地文件校验；有 makepkg 时额外比对 `.SRCINFO`。`--require-makepkg` 用于要求 Arch 元数据验证的环境。
- `check-updates [pkgbase]` 只读官方发布清单，核对版本、架构、下载地址和哈希，不自动改配方或发布。
- `export-aur <pkgbase> <新目录>` 在有 makepkg 的环境导出 AUR 文件；不覆盖现有目录，也不推送。已有 AUR 包先与维护者协作。

[静态 CI](.github/workflows/check.yml) 与[双架构构建 CI](.github/workflows/build.yml)随仓库提供；首次推送后才能产生远端结果。构建 CI 复用固定提交的 Omarchy 官方构建工具，只保留日志，不上传专有软件包。

## 仓库结构

```text
catalog.json               软件、来源、维护归属、验证状态
pkgbuilds/<pkgbase>/        独立 PKGBUILD、.SRCINFO、辅助文件、包说明
  .omarchy/package.json    Omarchy 上游更新配置，候选阶段手动 hold
tools/                     检查、只读更新发现、AUR 导出、CI 辅助
tests/                     工具行为测试，不模拟软件运行成功
docs/                      调研、打包、测试、发布及软件适配记录
```

新增软件先查 Arch、AUR、Omarchy。已有合适的软件包时只增加目录项和适配记录；确需新增或改进时才维护本地配方。向 Omarchy 导入后以其维护流程为准，不能假定它会自动同步这里或 AUR 的更改。

## 文档

- [调研结论与分发选择](docs/research.md)
- [编写和维护配方](docs/packaging.md)
- [测试与证据要求](docs/testing.md)
- [首次落地验证记录](docs/validation.md)
- [AUR、Omarchy 与自建源发布流程](docs/publishing.md)
- [钉钉官方 Arch 支持及现成 Omarchy 配方](docs/software/dingtalk.md)

本仓库原创代码与说明采用 [0BSD](LICENSE)。Qoder 等第三方程序保留其各自许可证；候选配方不代表获得了二进制再分发授权，也不代表 Qoder、钉钉或 Omarchy 官方背书。
