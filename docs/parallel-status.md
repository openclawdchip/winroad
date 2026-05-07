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

## 2026-05-07 第二轮

主线调整：`odb` 放到最后，本轮 6 线程全部推进非 ODB 顶层模块。

| 模块 | 线程 id | 昵称 | 状态 | 负责文件 |
| --- | --- | --- | --- | --- |
| `gpl` | `019e0265-9fb7-7110-99bf-cd751e15a6e3` | Noether | 已完成 | `winroad/gpl.py`, `docs/gpl.md` |
| `grt` | `019e0265-9fee-7121-9e65-c34c32aa251e` | Nash | 已完成 | `winroad/grt.py`, `docs/grt.md` |
| `rsz` | `019e0265-a043-78e3-867e-46fcfb90aa5d` | Euclid | 已完成 | `winroad/rsz.py`, `docs/rsz.md` |
| `cts` | `019e0265-a144-7e81-b75a-508275295e8d` | Tesla | 已完成 | `winroad/cts.py`, `docs/cts.md` |
| `rcx` | `019e0265-a165-76c2-a6d0-4e834d8fe200` | Hooke | 已完成 | `winroad/rcx.py`, `docs/rcx.md` |
| `pdn` | `019e0265-a192-7470-ac88-3e4f7fe5784c` | Mencius | 已完成 | `winroad/pdn.py`, `docs/pdn.md` |

### 第二轮已完成摘要

- `gpl`：深化 `Replace`、`NesterovPlace`、`RouteBase`、`TimingBase` 的函数边界和状态容器。
- `grt`：深化 `FastRouteCore` 容量、usage、overflow、adjustment、congestion、NDR 等边界。
- `rsz`：新增 `BaseMove` 派生 move 边界，并补 `Resizer`、`RepairDesign`、`RepairHold`、`RecoverPower` 状态字段。
- `cts`：深化 `CtsOptions`、`TechChar`、`TreeBuilder/HTreeBuilder`、`SinkClustering`、`LatencyBalancer`、`TritonCTS` 的函数边界。
- `rcx`：深化 RC table/model、corner/config、measure、SPEF、extMain、bench/pattern 边界。
- `pdn`：完成第一轮 PDN 顶层对象边界，包括 grid、strap、ring、via、domain、connect、report/check 等。

## 2026-05-07 第三轮

继续保持 6 线程并行。`odb` 仍然后置，本轮引入 `drt` 第一轮翻译。

| 模块 | 线程 id | 昵称 | 状态 | 负责文件 |
| --- | --- | --- | --- | --- |
| `drt` | `019e026d-f1f3-7031-a5d5-fa7aa7126a29` | Averroes | 失败 | `winroad/drt.py`, `docs/drt.md` |
| `pdn` | `019e026d-f223-7863-9fa5-f13aa88d4f73` | Sagan | 已完成 | `winroad/pdn.py`, `docs/pdn.md` |
| `gpl` | `019e026d-f257-7943-9e57-d14d1c303272` | Singer | 已完成 | `winroad/gpl.py`, `docs/gpl.md` |
| `grt` | `019e026d-f285-7752-8910-e5bec9c7e3ed` | Ohm | 已完成 | `winroad/grt.py`, `docs/grt.md` |
| `rsz` | `019e026d-f2a0-7b21-8ed6-8bf2e48d46fe` | Bacon | 已完成 | `winroad/rsz.py`, `docs/rsz.md` |
| `cts` | `019e026d-f2bc-79a3-a0db-c39bd079a437` | Wegener | 已完成 | `winroad/cts.py`, `docs/cts.md` |

补位线程：

| 模块 | 线程 id | 昵称 | 状态 | 负责文件 |
| --- | --- | --- | --- | --- |
| `drt` | `019e0272-b660-7592-8b09-9a2bb79c8798` | Parfit | 运行中 | `winroad/drt.py`, `docs/drt.md` |

### 第三轮已完成摘要

- `gpl`：补 initial placement、RouteBase congestion/report、TimingBase timing-driven、Nesterov snapshot/debug/report 等边界。
- `rsz`：补 RepairDesign limit/counter、MoveTracker 报告、RepairSetup endpoint、RepairHold/RecoverPower 计数与报告边界。
- `cts`：补 TechChar LUT 数据、TreeBuilder blockage/legalization、TritonCTS clock root/tree/report/repair/balance 等边界。
- `pdn`：补 GridComponent build/report、Connect split-cut/via、Grid lookup/build/report、SRoute、PDNRenderer、PdnGen lookup/repair/write 边界。
- `grt`：补 GSegment 轻量序列化、guide 读写、Net alpha/beta/gamma、resource snapshot、tile congestion、wirelength/report 边界。
