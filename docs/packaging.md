# 打包流程

每个包独立放在 `pkgbuilds/<pkgbase>/`；包目录应能复制到单独工作区后构建。开始前先读 [调研结论](research.md)，完成后按 [测试流程](testing.md) 验证、按 [发布流程](publishing.md) 贡献。

## 1. 查重并记录来源

检查 Arch 官方仓库、AUR、Omarchy 包仓库和厂商下载页。已有维护良好的包优先收录或参与维护。新增软件在 `catalog.json` 记录上游入口、既有包、确认过的架构、维护归属和状态。

确定每个架构的实际产物、版本、文件名、许可证、运行依赖及自更新行为。优先使用上游固定版本 URL；发布清单用于发现版本，不应让已提交的配方在每次构建时悄悄选择 `latest`。

## 2. 写独立配方

基本内容：

- `pkgname`、`pkgver`、`pkgrel`、`pkgdesc`、`url`、`license`、`arch`。
- 按功能声明 `depends`、`makedepends`、必要时 `optdepends`；只有真实冲突时添加 `conflicts`。
- 二进制使用 `source_x86_64`、`source_aarch64` 及各自的校验和数组，下载本地文件名带上版本和架构。
- `prepare()` 整理来源，`build()` 只在需要编译时使用，`package()` 只向 `$pkgdir` 安装文件。
- 修改同一上游版本的配方时增加 `pkgrel`；更新 `pkgver` 时将 `pkgrel` 重置为 `1`。

原生二进制不能标记为 `arch=('any')`。`aarch64` 声明需要实际的上游 ARM64 产物或能验证的源码构建流程；只改 `CARCH` 不会转换指令集。`provides` 不会解决文件重名或建立二进制兼容。

[PKGBUILD 手册](https://man.archlinux.org/man/PKGBUILD.5.en)、[架构来源和校验和](https://man.archlinux.org/man/alpm-package-source-checksum.7.en)

## 3. 重打包官方产物

DEB、RPM、tarball、AppImage 都可以是输入，输出统一为 Arch 包。先列出归档和元数据，再只安装需要的文件。不要执行 DEB/RPM 的安装维护脚本；其中的依赖与路径按 Arch 语义检查后显式处理。

不要在构建或安装钩子里运行厂商的一键安装脚本。脚本可能启动后台服务、登录账号或修改用户目录；这些步骤应由用户首次运行时主动完成。`PKGBUILD` 是可执行代码，审阅后使用非 root 用户构建。

通常 CLI 放在 `/usr/bin`，只读资源放在 `/usr/lib/<软件名>` 或 `/opt/<软件名>`。明确处理文件权限、符号链接和现有命令冲突。GUI 添加或修正 `.desktop`、图标及 MIME/协议声明；只有用户实际需要时才增加启动包装器。

后台软件默认不在安装时登录、启动或启用自启动。确有服务需求时优先提供用户级 service，并说明如何启用。卸载不删除用户数据。

## 4. 固定完整性与依赖版本

逐架构检查官方清单里的版本、下载地址和 SHA-256，再用实际下载结果核对。普通二进制来源不使用 `SKIP`。若上游提供签名，记录签名验证方法；校验和只确认下载内容与配方一致，不单独证明厂商身份。

本地启动器、补丁也列入 `source` 和校验和。若软件要求特定辅助程序版本，把依赖约束写清楚；不能用未受约束的“最新版”代替厂商兼容要求。需要内置辅助程序时固定其独立版本、校验和及私有路径，并说明为何没有使用共享依赖。

上游自更新应逐包处理：核对是否会写入 pacman 管理的文件、能否通过厂商支持的设置关闭，并测试包装器行为。不要在安装时批量改写用户已有配置。

## 5. 生成元数据并提交

本仓库工具使用 Python 3.9+ 标准库。在仓库根目录运行：

```bash
tools/check-package
tools/check-package qoderwake-bin
tools/check-updates qoderwake-bin
```

`check-package` 检查语法、元数据和仓库约束；在有 `makepkg` 的 Linux 环境还核对 `.SRCINFO`。`check-updates` 只读官方发布清单，核对版本、架构和校验和，不自动改配方。两者都不能代替构建与运行测试。

在 Arch Linux（ARM 使用合适的 Linux ARM 构建环境）中：

```bash
cd pkgbuilds/<pkgbase>
makepkg --verifysource
makepkg --printsrcinfo > .SRCINFO
makepkg -s
namcap PKGBUILD
namcap ./*.pkg.tar.zst
```

以上是开发检查；依赖隔离及每个架构的构建仍须按 [测试流程](testing.md) 完成。`makepkg -s` 可能请求 sudo 安装依赖，不要把整条命令用 sudo 执行。[makepkg 手册](https://man.archlinux.org/man/makepkg.8.en)、[namcap 手册](https://man.archlinux.org/man/namcap.1.en)

`.SRCINFO` 由 `makepkg --printsrcinfo` 生成。提交前核对其与 `PKGBUILD` 一致，不手工维护第二份版本信息。不要提交 `src/`、`pkg/`、下载缓存或 `.pkg.tar.zst`。

## 6. 更新来源

本仓库的更新检查首先提出待审阅变更，不能让未经检查的下载清单自动发布二进制。若提交 Omarchy，新包按它当时的规范使用 `.omarchy/package.json` 的 `upstream.watch`；无稳定可用的更新发现方式时，明确关闭同步并说明原因。版本发现、文件校验通过之后仍需重新测试依赖、安装布局和运行兼容性。[Omarchy 上游更新规范](https://github.com/omacom/omarchy-pkgs/blob/master/docs/upstream-sources.md)
