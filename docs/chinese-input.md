# 中文输入法（fcitx5 / 搜狗）在 Omarchy 上的配置记录

调研与落地日期：2026-10-19 至 2026-10-20。验证机器：Omarchy 4.0.5，Linux 7.2.8-9-omarchy，x86_64，Hyprland + Wayland（`WAYLAND_DISPLAY=wayland-1`），`LANG=en_US.UTF-8`。

## 结论先说

**基线用 `extra` 官方仓库的 `fcitx5-chinese-addons`，不要为了搜狗去动 fcitx4。** Omarchy 装机自带 fcitx5 框架、Qt/GTK 模块、systemd 用户环境变量和 xdg 自启，缺的只是中文引擎。

搜狗官方 Linux 版**在当前 Arch 上没有可用路径**：

| 路径 | 状态 | 依据 |
| --- | --- | --- |
| 官方 `sogoupinyin` 4.2.1.145（[下载页](https://shurufa.sogou.com/linux)） | 不可用 | 它是 **fcitx4** 模块，而 Arch 已把 fcitx4 从所有仓库移除（`pacman -Si fcitx` 无结果）；另需 `libidn.so.11`。AUR `fcitx-sogoupinyin`（112 票）因此在本机无法构建 |
| 经 IBus 桥接 | 不可用 | `sogouimebs` 已从 AUR 消失；`fcitx5-ibus` 在仓库与 AUR 均搜不到（0 结果） |
| AUR [`fcitx5-sogou`](https://aur.archlinux.org/packages/fcitx5-sogou) | 可行但需自担风险 | 重打包 openKylin 的 `sogou-ime-ng` 10.0.9.0.6（deb 构建于 2023-11-28）。下文有逐项验证结果 |

## 基线安装（官方仓库）

```bash
sudo pacman -S --noconfirm fcitx5-chinese-addons fcitx5-configtool
```

落地版本：`fcitx5-chinese-addons 5.1.15-2`、`fcitx5-configtool 5.1.16-3`、`fcitx5 5.1.23-1`，连带 `libime 1.1.17-1`、`opencc 1.4.1-1`、`marisa 0.3.1-1`。

已注册引擎位于 `/usr/share/fcitx5/inputmethod/`，除 `pinyin` 外还有 `shuangpin`（内置搜狗双拼方案）、`cangjie`、`erbi`、`wanfeng`、`zrm`、`qxm`、`wbpy` 等。`cloudpinyin`（云拼音）、`pinyinhelper`、`chttrans`（繁简）、`punctuation` 作为附加组件同时可用。

键盘布局 `us` 与 `keyboard-us` 保留在列表首位即可；`Ctrl+Space` 切换输入法，`Ctrl+Shift+F` 简繁，`Ctrl+Shift+H` 全半角。

## fcitx5 的 profile 有两个坑

1. **退出时回写覆盖。** fcitx5 在进程退出时会把内存中的输入法列表写回 `~/.config/fcitx5/profile`。手动编辑时若实例仍在运行，改动会被静默抹掉。可靠顺序只有两种：让 `fcitx5-configtool` 通过运行中的实例写入；或 `pkill -x fcitx5` → 改文件 → 启动。
2. **`pkill` 后可能被 D-Bus 立刻重新激活**，此时手动启动的第二个实例会因 `Unable to request dbus name` 自行退出并刷一屏 `Unloading addon`。这是正常竞争，不是配置错误。

## 诊断怎么读（都是踩过的）

- `fcitx5-remote -n` / `-s` 报告的是**当前聚焦客户端**的输入法。从没有聚焦窗口的 shell 调用它，永远显示默认项，**不能用来判断是否配置成功**。
- 权威证据用 D-Bus：

  ```bash
  busctl --user call org.fcitx.Fcitx5 /controller org.fcitx.Fcitx.Controller1 \
    InputMethodGroupInfo s Default
  ```

  返回 `sa(ss) "us" 3 "keyboard-us" "" "pinyin" "" "sogou-ime-ng-fcitx5-kylin-desktop" ""` 才算列表真的生效。
- `GetAddons` / `GetAddonsV2` 里的整数是**组件类别**（InputMethod=0、Frontend=1、Module=3、UI=4），**不是加载状态**，别拿它判断模块是否加载成功。
- `busctl` 没有 `list-names` 这个动词（正确的是 `list`）；查某个名字归谁用 `busctl --user status <name>`。
- `.pkg.tar.zst` 是 zstd，用 `tar -tzf`（gzip）会得到空输出，导致"没有敏感文件"这类**假阴性**；要用 `tar -tf`。

## AUR `fcitx5-sogou` 的验证结果

包基信息：`pkgver=10.0.9.0.6`、`pkgrel=2`、`arch=x86_64`、`license=(custom)`、`makedepends=(chrpath)`。7 个 source 全部来自 openKylin 镜像池（`https://mirrors.aliyun.com/openkylin/pool/pty/...`），逐个 SHA256 与 PKGBUILD 固定值一致，`.deb` 至今仍返回 HTTP 200。`prepare()`/`package()` 只做 `bsdtar` 解包和 `chrpath -d`，**不运行任何上游安装脚本**。

安装后：包 167 MB，净占用 **305.51 MiB**，1169 个文件条目，落点为 `/etc/cpis`（844）、`/usr/share`、`/usr/lib`、`/usr/bin`（7）、`/var/lib/cpis/users`。**不含** `profile.d`、`environment`、`pam.d`、`xdg/autostart`、系统级 systemd、cron、`ld.so.conf` 条目，也没有 setuid/setgid 文件——引擎与面板只由 **D-Bus 会话服务按需激活**（`/usr/share/dbus-1/services/com.cpis.{engine,panel}.service`），不需要配自启。

已证实可用的部分：

- 模块符号链接 `/usr/lib/fcitx5/libcpis-module-im-sogou-ime-ng-fcitx5-kylin-desktop.so` → `/usr/lib/x86_64-linux-gnu/cpis-module-im-fcitx5.so`，解析正常。
- 该模块 `ldd` 未解析依赖 **0** 项，且用 `ctypes.CDLL` 做了**真实 dlopen 测试并成功**；依赖的 `libFcitx5Core.so.7`、`libFcitx5Config.so.6`、`libFcitx5Utils.so.2` 与 fcitx5 5.1.23 的 soname 一致。
- 自带 `RUNPATH=/usr/lib/x86_64-linux-gnu`，所以 Debian multiarch 路径在 Arch 上也能自解析。
- IM 描述文件的 `Addon=sogou-ime-ng-fcitx5-kylin-desktop-addon` 与 addon 的**文件名 stem**（不是 `Name=`，那是显示名）匹配，结构自洽；`AddonForIM` 也确认解析成功。
- `cpis-engine-service`、`cpis-panel-service` 均可经 D-Bus 激活并存活、各自持有 `com.cpis.engine` / `com.cpis.panel` 名字，面板成功加载 `libcpis-ui-plugin-ime.so` 并进入 main loop；在 `DISPLAY=:0`（XWayland）下无报错。
- 7 个 `.scel` 词库文件完整进包。`makepkg` 期间的 `bsdtar: Can't translate pathname … to UTF-8`（GBK 文件名 vs UTF-8 环境）是**非致命警告**。

已知缺陷与风险：

1. **候选面板被硬编码走 X11。** `/usr/bin/com.cpis.panel.service.start.sh` 里 `export GDK_BACKEND=x11`、`QT_QPA_PLATFORM=xcb`。候选窗是 XWayland 窗口，在 Hyprland 上容易出现位置不跟随光标、分数缩放下字号异常。
2. **没有 Wayland 键盘状态后端。** `/etc/cpis/keyflow.ini` 引用 `libcpis-keyboard-status-manage-wayland.so`，但包里只发布了 `linux` 与 `x11` 两个变体，**wayland 那个不存在**。
3. **`libkylinenvverify.so` 缺失，但不影响打字。** `sogou_{asr,hw,kbd}.ini` 的 `[sogou_shell_runtime]` 都写了 `kylin_verify_libs=/usr/lib/x86_64-linux-gnu/libkylinenvverify.so`，该文件未随包发布。实测键盘插件 `libcpis-engine-plugin-sogou-kbd.so` 对它的 NEEDED 为 0、`ldd` 未解析项为 0、字符串里也未出现该名字，所以拼音输入不受影响；语音（asr）与手写（hw）则可能受影响。
4. **无人维护。** AUR 4 票、popularity≈0、已标记 out-of-date。上游 openKylin 曾收录 10.0.9.0.8 又整批删除，maintainer 在 README 里注明那版"不能用"并回退。fcitx5 下次 soname 升级（`libFcitx5Core.so.7` → `.so.8`）会让模块**静默失效**。
5. **闭源、联网、305 MB。** CPIS 引擎做云端候选词，属搜狗的遥测/账号同步面；`license=custom` 的重打包不构成为他人分发二进制的许可。

## 搜狗的实际配置面

**不在** `fcitx5-configtool` 里。可用的入口有三处：

```bash
sogou-ime-setting          # Qt5 图形设置程序（包内 /usr/bin）
vim /etc/cpis/keyflow.ini  # 需要 root
ls /etc/cpis/modules.d     # 语音 asr / 手写 hw / 键盘 kbd 三个模块
```

`/etc/cpis/keyflow.ini` 的 `[KEYFLOW_SETTING]` 是真正的日常开关：`pagesize = 6`（每页候选数）、`tradition`（简繁）、`fullshape`（全半角）、`chinese_punctuation`（中文标点）、`encn = cn`，以及 `shortcut.key.english/tradition/switch_pinyin_wubi`（`E`/`F`/`W`）。`ise.ini` 与 `isp.ini` 主要是 gdbus/thrift 传输与证书路径（引擎 TCP `127.0.0.1:9092`、面板 `9091`），不是外观项。

配置全在 root 所有的 `/etc` 下，**没有 per-user 覆盖目录**；用户词库与账号状态写入 `/var/lib/cpis/users/`（该路径由 pacman 拥有，升级时可能与运行时文件冲突）。日志很好找：`~/.com.cpis.engine.log` 和 `~/.com.cpis.panel.log`。

## 建议的组合

保留 `pinyin` 作主力（官方仓库、Wayland IMv2 原生、零风险），把搜狗当**第二个引擎**加装试验：`Ctrl+Space` 在 `keyboard-us` → `pinyin` → 搜狗（状态标签显示 `跨`）之间循环。搜狗不听话就删掉 profile 里那一段并重启 fcitx5，`pinyin` 完全不受影响。

只想要"搜狗手感"而不引入闭源二进制的话，本机已具备：`shuangpin`（搜狗双拼方案）、`cloudpinyin`（默认关闭，在 `fcitx5-configtool` → 附加组件 → 云拼音里开启）、以及 fcitx5 拼音的用户词库/自定义短语导入。

## 尚未证实的部分

以上都是**无头可验证**的结论。**真人实际打字的体验未验证**：需要聚焦一个真实窗口、按 `Ctrl+Space` 切到搜狗再敲 `nihao`，才能确认候选词是否正常出现、跟随光标定位是否正确。`com.cpis.engine` 的会话创建方法没有暴露在 gdbus 接口上（`AcquireResult` 对未注册会话返回 `-2`），无法在脚本里伪造输入上下文来完成端到端候选词测试。应用级兼容性（Electron/Chromium、Qt6、GTK4、钉钉等）也需逐个实测，不在本文结论内。

## 相关上游

- [Fcitx5 — Arch Wiki](https://wiki.archlinux.org/title/Fcitx5)
- [Using Fcitx 5 on Wayland](https://fcitx-im.org/wiki/Using_Fcitx_5_on_Wayland)
- [AUR：fcitx5-sogou](https://aur.archlinux.org/packages/fcitx5-sogou)（版本 10.0.9.0.6-2，deb 构建于 2023-11-28）
- [AUR：fcitx-sogoupinyin](https://aur.archlinux.org/packages/fcitx-sogoupinyin)（4.2.1.145，fcitx4，本机不可构建）
- [搜狗输入法 Linux 下载页](https://shurufa.sogou.com/linux)
