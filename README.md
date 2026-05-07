# WinRoad

WinRoad 是一个面向 Windows 的 Python 物理设计工程仓库，目标是把 OpenROAD / OpenDB 的 C++ 能力逐步翻译成 Python 模块。

## 目标

- 以 OpenROAD 源码为准做等价翻译
- 让 `odb / grt / gpl / rsz / cts / rcx / pdn / drt` 逐层可调用
- 保留中文注释和模块说明，方便持续协作
- 让项目最终可以直接作为 GitHub 仓库开源

## 当前状态

- 仓库骨架已重建
- 代码将按 OpenROAD 源码边界逐模块翻译
- 每个模块单独维护文档，记录已实现内容和未实现内容
- 仓库已初始化为 Git 仓库，并已通过 SSH 推送到 GitHub

## 发布记录

- 远端地址：`git@github.com:openclawdchip/winroad.git`
- 当前主分支：`main`
- 初始提交：`59136ca`
- 提交说明：`init winroad skeleton`
- SSH 配置：复用本机已存在的 `~/.ssh/config` 中 GitHub 身份
- 本地仓库路径：`D:\winroad_py`

## 目录

- `winroad/`：Python 实现
- `docs/`：模块文档
- `examples/`：示例入口
- `runs/`：运行输出

## 约定

1. 不做自造 demo 接口。
2. 不做架构创新。
3. 只做源码复刻和必要的 Python 适配。
