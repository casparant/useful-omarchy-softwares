# 发布与上游贡献

配方维护、AUR 发布和 Omarchy 二进制发布是独立入口。先完成 [打包](packaging.md) 和 [测试](testing.md)，记录版本、架构及未验证项目，再选择入口。本仓库初期只维护配方，不运营独立 pacman 源；CI 目前保留检查日志和摘要，不上传厂商二进制安装包。

## 提交前准备

确认包名未重复、来源固定、校验和匹配、版本递增、`.SRCINFO` 与配方一致。每个架构分别保存构建与安装证据。需要公开托管上游二进制时，检查发行包许可证是否允许相应重分发；配方许可证不能覆盖厂商文件。

一个发布变更应说明：用户会获得什么、上游版本、打包改动、架构、实际测试结果和已知限制。不要把配方声明的架构全部写成已实测。

## 发布到 AUR

已有包先联系或向维护者提供补丁，不重复创建同功能包。新包每个 `pkgbase` 对应一个 AUR Git 仓库，需要 AUR 账户和登记的 SSH 公钥。准备好后，在独立目录中操作：

```bash
git clone ssh://aur@aur.archlinux.org/<pkgbase>.git
```

在有 `makepkg` 的 Linux 环境中，使用本仓库工具生成一份全新的导出目录：

```bash
tools/export-aur <pkgbase> /tmp/<pkgbase>-aur-export
```

输出目录必须尚不存在。工具先验证 `.SRCINFO`，再导出 `PKGBUILD`、`.SRCINFO` 和配方 `source` 中的本地辅助文件。将导出内容复制到上面克隆的 AUR 仓库，审阅差异后提交、推送。不要复制构建产物、下载文件、`src/`、`pkg/` 或仅供 Omarchy 使用的 `.omarchy/` 元数据。推送会公开发布配方，因此应在完整审阅后进行。

生成元数据的命令在包目录运行：

```bash
makepkg --printsrcinfo > .SRCINFO
```

AUR 提交规则目前要求包至少能在 `x86_64` 构建，可同时提供 `aarch64`。ARM-only 软件不要为了通过这一入口虚报 `x86_64`。[AUR 提交规则](https://wiki.archlinux.org/title/AUR_submission_guidelines)、[AUR 上传说明](https://wiki.archlinux.org/title/AUR_submission_guidelines#Uploading_packages)

发布后在 `catalog.json` 记录 AUR 地址和维护者。上游新版本增加 `pkgver` 并重置 `pkgrel=1`；同版本打包修复增加 `pkgrel`，重新生成 `.SRCINFO`、测试并推送。

## 贡献到 Omarchy 包源

以下命令在 [omacom/omarchy-pkgs](https://github.com/omacom/omarchy-pkgs) 的 fork 中执行，不是在本仓库运行。以提交时的官方 README 为准。

1. 从 `master` 建分支，每个 PR 处理一个包。
2. 新建框架，或一次性导入已有 AUR 配方：

   ```bash
   bin/add-package <pkgbase> --local --scaffold
   # 已有 AUR 包时，选择下面这一种导入方式：
   bin/add-package <pkgbase> --source aur
   ```

3. 把审阅后的配方和附属文件放入 `pkgbuilds/<pkgbase>/`，填好 `.omarchy/package.json`。新包配置 `upstream.watch`，核对版本发现；若无法可靠自动更新，使用 `"sync": false` 并在 PR 说明原因。
4. 使用 Docker/Podman 构建，并在实际系统安装测试：

   ```bash
   python helpers/upstream-watch.py check pkgbuilds/<pkgbase>
   bin/build --package <pkgbase> --dry-run
   bin/build --package <pkgbase>
   bin/build --package <pkgbase> --arch aarch64
   ```

5. 将包文件和测试结论提交为 PR。上游本地构建输出位于 `build-output/edge/<arch>/`，是未签名的测试产物，不从本地 checkout 直接发布。

`--dry-run` 只显示计划。x86_64 主机上的 aarch64 本地构建可使用仿真，官方 CI 会原生构建 aarch64；本地未测 ARM 运行时应如实写出。源码 Git 来源按官方规则固定到 tag 或 commit。

新贡献者可能需要维护者批准 CI。通过并合并后由官方流程构建、签名和发布，默认进入 `edge`，随后随发行推广到 `rc`、`stable`；是否立即进入稳定渠道由上游评估。普通贡献者不需要自己的签名密钥或仓库托管。[官方贡献流程](https://github.com/omacom/omarchy-pkgs#contribute-a-package)

上游更新声明可以发现版本及更新校验和；依赖、架构、启动器和安装逻辑仍需维护。AUR 导入后不会继续自动同步 AUR，所以在两边发布修复时分别跟踪状态。[Omarchy 更新来源规范](https://github.com/omacom/omarchy-pkgs/blob/master/docs/upstream-sources.md)

## 桌面与菜单集成

包有正确的 `.desktop` 文件后，先确认启动器可发现。若希望出现在 Omarchy 精选安装菜单，另向 Omarchy 主仓库提交适配；默认预装需要单独讨论。不要把菜单改动和二进制配方贡献混为同一次发布。[Omarchy 菜单说明](https://github.com/omacom/omarchy/blob/quattro/docs/menu.md)

## 未来自建软件源

只有确实需要独立发布节奏时再加。需要覆盖安装包及数据库的签名、密钥分发和轮换、HTTPS 托管、按架构分库、保留旧版本及不可覆盖同版本文件的策略。`repo-add` 管理仓库数据库，GitHub 可以作为其中一部分托管设施，但不是 AUR 的替代名称。[repo-add 手册](https://man.archlinux.org/man/repo-add.8.en)

当前没有自动推送 AUR、创建上游 PR 或发布二进制的隐含步骤。仓库中的配方和验证记录准备就绪后，再执行明确的外部发布操作。
