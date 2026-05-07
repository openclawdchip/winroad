# 并行线程状态

## 2026-05-07

本轮并行推进 6 个顶层模块。每条线程只负责自己的模块文件和文档，避免互相覆盖。

| 模块 | 线程 id | 昵称 | 状态 | 负责文件 |
| --- | --- | --- | --- | --- |
| `odb` | `019e0257-c03a-7b62-b8d6-31ca588a349f` | Franklin | 已完成 | `winroad/odb.py`, `docs/odb.md` |
| `gpl` | `019e0257-c470-7912-a15f-3447624ffad6` | Goodall | 已完成 | `winroad/gpl.py`, `docs/gpl.md` |
| `grt` | `019e0257-c48c-70d1-8ab1-6042baf15e89` | Cicero | 已完成 | `winroad/grt.py`, `docs/grt.md` |
| `rsz` | `019e0257-c559-7cd0-a546-c085f5afd87d` | Ptolemy | 已完成 | `winroad/rsz.py`, `docs/rsz.md` |
| `cts` | `019e0257-c575-7b83-97a2-082b60824cd0` | Russell | 已完成 | `winroad/cts.py`, `docs/cts.md` |
| `rcx` | `019e0257-c59c-7201-9a76-a76cb3b06abc` | Lovelace | 已完成 | `winroad/rcx.py`, `docs/rcx.md` |

## 已完成摘要

- `odb`：补了 `DbProperty`、`DbRow`、`DbBTerm`、`DbBPin`、`DbGuide`、`DbGroup`，并扩展 `DbBlock` 和 `DbDatabase` 的创建/容器接口。
- `gpl`：补了 `Replace`、placer/nesterov/routability/timing/graphics 等顶层对象边界，未翻译的数值算法显式保留为 `NotImplementedError`。
- `grt`：补了全局布线 pin/net/grid/route/congestion/FastRoute/GlobalRouter 等对象边界，主算法入口保留待翻译。
- `rsz`：补了 Resizer、BufferedNet、RepairDesign/Setup/Hold、RecoverPower、MoveTracker、BaseMove 等对象边界，真实 STA/修复算法保留待翻译。
- `cts`：补了 Clock、CtsOptions、TechChar、TreeBuilder、HTreeBuilder、SinkClustering、LatencyBalancer、TritonCTS 等对象边界，真实 CTS 构树和 DB 写回保留待翻译。
- `rcx`：补了 `Ext`、`OpenRCX`、`extMain`、RC 模型、测量、SPEF 和提取入口边界，真实提取算法保留待翻译。

## 查看方式

- 当前线程表：`D:\winroad_py\docs\parallel-status.md`
- 代码进展：`D:\winroad_py\winroad`
- 文档进展：`D:\winroad_py\docs`
