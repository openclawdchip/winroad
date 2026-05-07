# WinRoad

WinRoad 是一个面向 Windows 的 Python 物理设计工程仓库，目标是把 OpenROAD / OpenDB 的 C++ 能力逐步翻译成 Python 模块。

## 目标

- 以 OpenROAD 源码为准做等价翻译
- 先完成非 ODB 顶层模块，再回到 `odb`
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

## 代码组织规则

当前早期翻译阶段允许用 `winroad/<module>.py` 承接 C++ 类边界，但这只是临时落点。
从下一轮开始，顶层模块必须逐步拆成 package，避免单文件无限膨胀。

目标结构示例：

- `winroad/gpl/`：`replace.py`、`placer_base.py`、`nesterov.py`、`route_base.py`、`timing_base.py`
- `winroad/grt/`：`global_router.py`、`fast_route.py`、`grid.py`、`guide.py`、`congestion.py`
- `winroad/rsz/`：`resizer.py`、`buffered_net.py`、`repair_design.py`、`repair_setup.py`、`repair_hold.py`、`recover_power.py`
- `winroad/cts/`：`triton_cts.py`、`options.py`、`clock.py`、`tree_builder.py`、`tech_char.py`、`clustering.py`
- `winroad/rcx/`：`ext.py`、`spef.py`、`measure.py`、`rc_model.py`、`corner.py`、`bench.py`
- `winroad/pdn/`：`pdngen.py`、`grid.py`、`component.py`、`via.py`、`domain.py`、`renderer.py`
- `winroad/drt/`：`triton_route.py`、`flex_dr.py`、`flex_gr.py`、`grid_graph.py`、`gc.py`、`fr.py`

每个 package 的 `__init__.py` 负责导出兼容接口。旧的 `winroad/<module>.py`
在迁移期只做兼容转发，迁移完成后再删除。

## 模块地图

WinRoad 先按 OpenROAD 的源码边界建模。当前主线调整为：`odb` 放到最后，
优先推进不直接依赖完整 OpenDB 细节的顶层算法模块。

| OpenROAD 模块 | WinRoad 目标 |
| --- | --- |
| `gpl` | 全局布局 |
| `grt` | 全局布线 |
| `rsz` | resize / timing repair |
| `cts` | 时钟树综合 |
| `rcx` | 寄生参数提取 |
| `pdn` | 电源网络生成 |
| `drt` | 详细布线 |
| `odb` | OpenDB 数据库与对象模型，最后补完整 |

## 文档规则

- 每个模块单独一个文档
- 每个文档只记录该模块已经实现的功能和未实现的空白
- 不写 demo 口径，不写架构设想，只写翻译结果

## 约定

1. 不做自造 demo 接口。
2. 不做架构创新。
3. 只做源码复刻和必要的 Python 适配。
