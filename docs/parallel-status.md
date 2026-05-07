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
| `drt` | `019e0272-b660-7592-8b09-9a2bb79c8798` | Parfit | 已完成 | `winroad/drt.py`, `docs/drt.md` |

### 第三轮已完成摘要

- `gpl`：补 initial placement、RouteBase congestion/report、TimingBase timing-driven、Nesterov snapshot/debug/report 等边界。
- `rsz`：补 RepairDesign limit/counter、MoveTracker 报告、RepairSetup endpoint、RepairHold/RecoverPower 计数与报告边界。
- `cts`：补 TechChar LUT 数据、TreeBuilder blockage/legalization、TritonCTS clock root/tree/report/repair/balance 等边界。
- `pdn`：补 GridComponent build/report、Connect split-cut/via、Grid lookup/build/report、SRoute、PDNRenderer、PdnGen lookup/repair/write 边界。
- `grt`：补 GSegment 轻量序列化、guide 读写、Net alpha/beta/gamma、resource snapshot、tile congestion、wirelength/report 边界。
- `drt`：完成第一轮详细布线顶层边界，包含 TritonRoute、FlexDR/FlexGR/FlexGridGraph/FlexPA/FlexGCWorker、frDesign/frNet/frVia/frLayer 等对象。

## 2026-05-07 第四轮

本轮 6 线程不继续堆单文件，统一把非 ODB 模块拆成 package。旧 `winroad/<module>.py`
只保留兼容转发。

| 模块 | 线程 id | 昵称 | 状态 | 负责范围 |
| --- | --- | --- | --- | --- |
| `gpl` | `019e027c-905f-75f2-9f9c-d084040b40d5` | Boyle | 已完成 | `winroad/gpl.py`, `winroad/gpl/*`, `docs/gpl.md` |
| `grt` | `019e027c-908f-79b3-ab04-0504f1cac627` | Plato | 已完成 | `winroad/grt.py`, `winroad/grt/*`, `docs/grt.md` |
| `rsz` | `019e027c-90c4-7380-a8fd-21af83d8ca54` | Lorentz | 已完成 | `winroad/rsz.py`, `winroad/rsz/*`, `docs/rsz.md` |
| `cts` | `019e027c-90dd-7ec0-ac33-f1b33c3f1c07` | Maxwell | 已完成 | `winroad/cts.py`, `winroad/cts/*`, `docs/cts.md` |
| `pdn` | `019e027c-9177-7a40-910f-1cf2ec4905db` | Curie | 已完成 | `winroad/pdn.py`, `winroad/pdn/*`, `docs/pdn.md` |
| `drt` | `019e027c-9132-7c41-810f-cb35373d0ba5` | Beauvoir | 已完成 | `winroad/drt.py`, `winroad/drt/*`, `docs/drt.md` |

### 第四轮已完成摘要

- `gpl`：拆为 `common/options/placer_base/initial_place/nesterov/route_base/timing_base/graphics/replace`。
- `grt`：拆为 `types/guide/congestion/grid/fast_route/global_router`。
- `rsz`：拆为 `common/buffered_net/moves/repair_design/repair_setup/repair_hold/recover_power/resizer`。
- `cts`：拆为 `types/clock/options/tech_char/tree_builder/clustering/latency/triton_cts`。
- `pdn`：拆为 `types/via/component/grid/domain/sroute/renderer/pdngen`。
- `drt`：拆为 `types/fr/grid_graph/flex_dr/flex_gr/flex_pa/gc/triton_route`。

## 2026-05-07 第五轮

本轮继续 6 线程并行。非 ODB 模块已经拆成 package，本轮开始在 package 内继续补可落地功能：
状态管理、report、snapshot/revert、lookup、参数校验和纯数据关系。真实 EDA 核心算法仍保持
同名入口并抛 `NotImplementedError`。

| 模块 | 线程 id | 昵称 | 状态 | 负责范围 |
| --- | --- | --- | --- | --- |
| `gpl` | `019e0286-8f94-79d1-b87c-ddc3a5b7d625` | Godel | 已完成 | `winroad/gpl/*`, `docs/gpl.md` |
| `grt` | `019e0286-8fce-7221-a0cc-cd687b087ae9` | Hypatia | 已完成 | `winroad/grt/*`, `docs/grt.md` |
| `rsz` | `019e0286-8ffc-7941-9a9a-f2c4cafb4a4c` | Archimedes | 已完成 | `winroad/rsz/*`, `docs/rsz.md` |
| `cts` | `019e0286-9035-7382-901a-a3eadc2fb2e8` | Hume | 已完成 | `winroad/cts/*`, `docs/cts.md` |
| `pdn` | `019e0286-907e-74e1-841e-01c0b496b226` | Hegel | 已完成 | `winroad/pdn/*`, `docs/pdn.md` |
| `drt` | `019e0286-90a7-7882-b67c-51796c34993c` | Harvey | 已完成 | `winroad/drt/*`, `docs/drt.md` |

### 第五轮已完成摘要

- `gpl`：补配置校验、report、ODB 骨架 pin/net/inst 关系同步、Nesterov 状态回调、bin overflow、snapshot/revert。
- `grt`：补 guide JSON/text round-trip、congestion/resource report、adjustment 管理、状态保存恢复。
- `rsz`：补 RepairDesign/Setup/Hold/RecoverPower 配置计数报告、MoveTracker、BufferedNet 纯数据树行为。
- `cts`：补 Clock/SubNet 遍历、CtsOptions reset/set/get、TechChar LUT、TreeBuilder blockage/legalization、TritonCTS bookkeeping。
- `pdn`：补 domain/grid/component/connect/via/sroute/renderer 参数校验、lookup、report、状态 reset。
- `drt`：补 frDesign/frBlock/frNet/frVia/frLayer 关系、FlexGridGraph 容器、RouterConfiguration、DRC/guide report。

## 2026-05-07 第六轮

本轮继续 6 线程并行。`rcx` 进入拆包队列，其余非 ODB package 继续补状态导出、
序列化、report、配置导入导出等可落地功能。

| 模块 | 线程 id | 昵称 | 状态 | 负责范围 |
| --- | --- | --- | --- | --- |
| `gpl` | `019e0295-9e56-77f1-8d94-f50dffe05dde` | Mendel | 已完成 | `winroad/gpl/*`, `docs/gpl.md` |
| `grt` | `019e0295-9f86-7c40-b917-f0cd156e7144` | Kuhn | 已完成 | `winroad/grt/*`, `docs/grt.md` |
| `rsz` | `019e0295-9fa2-73c3-a3ec-0d3b2180e1e7` | Mill | 已完成 | `winroad/rsz/*`, `docs/rsz.md` |
| `cts` | `019e0295-9fc7-7063-b5c7-9a59669cc05b` | James | 已完成 | `winroad/cts/*`, `docs/cts.md` |
| `pdn` | `019e0295-9fe0-7ae0-a4b5-15a1252327ac` | Gauss | 已完成 | `winroad/pdn/*`, `docs/pdn.md` |
| `rcx` | `019e0295-9ff9-7411-9339-b7daa5ea3e7a` | Faraday | 已完成 | `winroad/rcx.py`, `winroad/rcx/*`, `docs/rcx.md` |

### 第六轮已完成摘要

- `gpl`：补 InitialPlace 稀疏矩阵/向量占位容器、PlaceOptions 完整报告、Nesterov/GCell/BinGrid 纯数据状态、RouteBase 拥塞历史、TimingBase 权重快照恢复。
- `grt`：补 guide 批量读写、按 net 拆分、routing metrics、resource/congestion JSON schema、adjustment 条件查询删除、GlobalRouter state diff/merge。
- `rsz`：补 BufferedNet JSON/report、MoveTracker JSON/report、RepairDesign/Setup/Hold/RecoverPower 配置合并、reset 和 statistics 导出。
- `cts`：补 Clock network 序列化、CtsOptions profile 导入导出、TechChar LUT 导入导出、TreeBuilder candidate/legalization 报告、TritonCTS 顶层状态快照。
- `pdn`：补 PdnGen config/state 导入导出、domain/grid/component 汇总、via failure 聚合、renderer selection snapshot、sroute summary。
- `rcx`：从单文件拆成 package，保留旧 `winroad/rcx.py` 兼容转发，补 config/status/report、corner 校验和 options 状态。
