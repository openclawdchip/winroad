# gpl

## 包结构

`winroad.gpl` 已从原先的单文件实现拆分为 package，公开 API 仍通过
`import winroad.gpl` 统一转发：

- `options.py`：`PlaceOptions`
- `placer_base.py`：`PlacerBaseVars`、`Die`、`Instance`、`Pin`、`Net`、`PlacerBaseCommon`、`PlacerBase`
- `initial_place.py`：`InitialPlaceVars`、`InitialPlace`
- `nesterov.py`：`FloatPoint`、`GCell*`、`GPin`、`GNet`、`Bin*`、`NesterovBase*`、`NesterovPlace*`、`nesterovDbCbk`
- `route_base.py`：`RouteBaseVars`、`Tile`、`TileGrid`、`RouteBase`
- `timing_base.py`：`TimingBase`
- `graphics.py`：`AbstractGraphics`、`GraphicsNone`
- `replace.py`：`Replace`、`isValidSigType()`、`make_replace()`
- `common.py`：包内共享类型与 ODB 兼容辅助函数

旧 `winroad/gpl.py` 仅保留兼容转发，不再保存完整实现。

## 已实现

- `PlaceOptions`
  - 对应 OpenROAD `gpl::PlaceOptions`
  - 保留默认参数、`skipIo()`、`validate()`
  - 第四轮补充更完整的参数范围校验与 `report()` 状态导出

- 顶层入口 `Replace`
  - 对应 OpenROAD `gpl::Replace`
  - 已翻译构造、`setGraphicsInterface()`、`reset()`、`addPlacementCluster()`
  - 第二轮补充 `clearPlacementClusters()`、`getTotalPlaceableInsts()`、`resetRoutabilityResources()`、`resetTimingResources()` 与若干 C++ 风格配置 setter
  - 已建立 `doPlace()`、`doIncrementalPlace()`、`doInitialPlace()`、`doNesterovPlace()`、`initNesterovPlace()`、`getUniformTargetDensity()`、`setDebug()` 的入口边界
  - 内部对象关系按 C++ 保留：`pbc_ / nbc_ / pbVec_ / nbVec_ / rb_ / tb_ / ip_ / np_ / clusters_`

- PlacerBase 对象层
  - `PlacerBaseVars`
  - `Die`
  - `Instance`
  - `Pin`
  - `Net`
  - `PlacerBaseCommon`
  - `PlacerBase`
  - 已建立实例、线网、HPWL、die/core、place/fixed/dummy 分类等基础字段与访问函数

- InitialPlace 边界
  - `InitialPlaceVars`
  - `InitialPlace`
  - 已保留 `doBicgstabPlace()`、`placeInstsInitialPositions()`、`setPlaceInstExtId()`、`updatePinInfo()`、`createSparseMatrix()`、`updateCoordi()` 边界
  - 第三轮补充初始布局状态：place inst ext id、强制居中初始化、pin 坐标刷新、坐标向 DB 回写、solver/debug 状态与 `reportStatus()`
  - 第六轮补充可复用 sparse matrix / RHS / solution 向量占位容器，`createSparseMatrix()` 现在建立可验证的单位对角占位形状，真实 B2B stamping 与 BiCGSTAB 求解仍在 solver 边界抛错

- Nesterov 对象层
  - `FloatPoint`
  - `GCellChange`
  - `GCell`
  - `GPin`
  - `GNet`
  - `Bin`
  - `BinGrid`
  - `NesterovBaseVars`
  - `NesterovBaseCommon`
  - `NesterovBase`
  - `NesterovPlaceVars`
  - `NesterovPlace`
  - `nesterovDbCbk`
  - 已建立 gcell/gpin/gnet、bin grid、target density、overflow、filler、callback 相关字段和函数边界
  - 第二轮补充 WA exp sum 读写口、GNet WA 累计量访问口、Bin/Grid 密度范围入口、NesterovBaseCommon changed-gcell/timing-weight 容器、NesterovBase SLP 坐标/梯度向量与 snapshot/revert 状态
  - 第二轮补充 `NesterovPlace::init()`、`initWireLengthCoef()`、`update*SLPCoordi()`、`update*Gradient()`、`updateOverflow()`、`checkConvergence()`、`checkDivergence()`、`updateTiming()`、`updateRoutability()` 等主循环阶段边界
  - 第三轮补充 `NesterovPlace` 的 debug graphics 入口触发、last iter、timing/routability 迭代计数、snapshot 保存标志、snapshot revert 后 DB 回写、`reportStatus()` / `getLastReport()`
  - 第六轮补充 `GCell` 面积/密度盒纯数据访问与更新、`Bin` utilization/overflow/reset 数据口、`BinGrid.reportStatus()`、`NesterovBase.refreshState()` 与 base 级报告

- Routability / Timing 边界
  - `Tile`
  - `TileGrid`
  - `RouteBaseVars`
  - `RouteBase`
  - `TimingBase`
  - 已保留 RUDY、global router、timing-driven net reweight 的 C++ 函数入口
  - 第二轮补充 RouteBase 的 tile metric 容器、RC/overflow/utilization 状态、`initRouteBase()`、`updateRoute()`、`updateRudyRoute()`、`updateInflationRatio()`、`updateGCellSize()`、min-RC snapshot/revert 边界
  - 第二轮补充 TimingBase 的 timing-driven net 容器、原始权重缓存、overflow checkpoint 访问口、`resetTimingDrivenNets()`、`updateGNetWeights()`、`runResizerForTiming()`、`resetFillerCells()` 边界
  - 第三轮补充 RouteBase 的 RC/overflow/utilization 历史、min-RC gcell size 快照/恢复、inflation 总量与拥塞报告 `reportCongestion()`
  - 第三轮补充 TimingBase 的一次性 overflow checkpoint 调度、timing-driven 迭代状态、原始 timing weight restore、`timingDrivenNets()` 与 `reportTimingDriven()`
  - 第六轮补充 RouteBase congestion snapshot 历史容器与清理/报告入口；TimingBase 补充按 gnet identity 的权重快照、恢复计数和报告字段

- 图形调试接口
  - `AbstractGraphics`
  - `GraphicsNone`
  - 默认入口与 OpenROAD 一样使用无图形后端
  - 第三轮补充 `GraphicsNone` 的 debug/status/iter/routability/timing 事件记录，便于无 GUI 环境验证调试边界

- 辅助接口
  - `isValidSigType()`
  - `make_replace()`
  - 第三轮补充 `Replace` 的 `getInitialPlace()`、`getNesterovPlace()`、`getRouteBase()`、`getTimingBase()` 与分项/总览 `report*()` 入口
  - 第四轮补充入口统一配置校验、reset 总数清理、cluster 拷贝保存、总览报告中的 base/common 状态

## 未实现

- `InitialPlace::createSparseMatrix()` 的 B2B 模型 stamping 与真实矩阵系数构建、BiCGSTAB 求解；可复用矩阵/向量占位容器、坐标容器与回写入口已建立
- `NesterovBaseCommon` 的 weighted-average wirelength force / gradient / preconditioner
- `NesterovBase` 的 FFT 电势场、density gradient、Nesterov 坐标更新、收敛/发散判定；snapshot/revert 与 bin 状态容器已建，真实 min-overflow 选择逻辑未译
- `NesterovPlace::doNesterovPlace()` 主循环、backtracking、wirelength coefficient 更新、timing/routability 迭代调度
- `RouteBase` 的 RUDY tile 计算、FastRoute/global router 结果读取、routability-driven inflation/revert
- `TimingBase::executeTimingDriven()` 的 STA slack 读取、关键网权重更新、resizer journal 交互
- `runMBFF()` 对应的 MBFF 聚类流程
- 完整 OpenDB ITerm/BTerm/Region/Group/Row 支撑依赖

## 说明

- 当前翻译目标是建立 OpenROAD gpl 的核心对象、入口类和关键函数边界。
- 未翻译算法不会用估算 demo 代替，相关函数显式抛出 `NotImplementedError`。
- 字段名尽量贴近 C++ 成员名，保留尾部 `_`，方便后续逐文件继续对照源码翻译。

## 第四轮补充

- 配置验证
  - `PlaceOptions.validate()` 现在覆盖初始布局、Nesterov、timing/routability、bin grid、pad 等关键参数范围。
  - `Replace` 的主要入口与 C++ 风格 setter 会调用校验，避免把非法状态带入后续对象。

- PlacerBase 关系状态
  - `PlacerBaseCommon` 会从当前 ODB 骨架的 `iterms`、`bterms`、`bpins` 关系创建可验证的 `Pin`，并同步 Instance/Net 反向关系。
  - 新增 `addDbInst()` / `removeDbInst()` / `addDbNet()` / `removeDbNet()`，供 package 内 DB callback 状态更新使用。

- Nesterov 状态层
  - `NesterovBaseCommon` 补齐 `GNet` 映射、`GPin` 构建、`rebuildPinRelationships()`、gcell/gnet 增删和 `reportStatus()`。
  - `NesterovPlace` 的 create/destroy/move/resize callback 现在更新 package 内对象关系、面积 delta、changed gcell、pin/net box，并在 snapshot revert 后回写 DB。
  - `BinGrid` 补充 bin index 范围计算、non-place 面积统计、gcell/filler density 面积统计与 overflow 状态刷新；这只是状态/报告数据，不替代 FFT/solver。

- Route/Timing 状态层
  - `RouteBase.initRouteBase()` 可从 Nesterov bin grid 建立 tile grid，`revertGCellSizeToMinRc()` 恢复 target density 并记录 revert 次数，拥塞报告包含历史序列。
  - `TimingBase` 补齐 `Sequence` 类型导入，保持 timing-driven 核心重权重仍显式未实现。

## 第六轮补充

- InitialPlace 状态层
  - 新增 `sparseMatrix_`、`rhsVecX_/rhsVecY_`、`solutionVecX_/solutionVecY_`、matrix nonzero/reuse 计数。
  - `createSparseMatrix()` 建立与 place inst 数量一致的可复用单位对角占位矩阵和坐标 RHS，便于 smoke 与后续 B2B stamping 接入。
  - `doBicgstabPlace()` 仍在 solver 调用边界抛出 `NotImplementedError`，不伪造求解结果。

- PlaceOptions/report 完整性
  - `PlaceOptions.report()` 覆盖 initial place、Nesterov、timing、routability、bin grid、pad、phi/wirelength/density 系数等主要配置。

- Nesterov 纯数据更新
  - `GCell` 补充 area/density area/location/density-box 更新口，resize 同步 density size。
  - `Bin` 补充 place area、available area、overflow area、utilization 与 area/electro reset。
  - `BinGrid` 补充 total/average/max density 数据、area/electro reset 与 `reportStatus()`。
  - `NesterovBase` 补充 `refreshState()` 与 base 级 `reportStatus()`，仍不触碰 FFT、gradient、坐标迭代 solver。

- Route/Timing 状态层
  - `RouteBase` 新增 congestion snapshot 历史容器，统一保存 rc/overflow/utilization/tile/inflation 样本，并在报告中导出。
  - `TimingBase` 新增按对象 identity 保存的 timing weight 快照、恢复计数、last restored 数量；真实 STA slack 读取和 net reweight 仍显式未实现。

## 第七轮补充

- PlacerBase 对象关系/报告
  - `Instance.report()`、`Pin.report()`、`Net.report()`、`PlacerBase.reportStatus()` 补齐稳定字典导出。
  - `PlacerBaseCommon.rebuildPinRelationships()` 可重新扫描当前 ODB 骨架的 ITerm/BTerm，并同步 Instance/Net 反向关系。
  - `removeDbInst()` / `removeDbNet()` 删除时会断开相关 pin 的实例端或线网端，避免 Python 对象图保留悬挂引用。
  - `reportConnectivity()` 汇总 inst/pin/net 数量、dangling pin、HPWL、macro area，并可返回少量对象样本。

- InitialPlace 报告
  - 新增 `reportMatrix()` 和 solution vector 访问口，导出 sparse matrix/RHS/solution 容器形状。
  - `createSparseMatrix()` 仍只建立可验证占位形状；真实 B2B stamping 和 BiCGSTAB 求解继续保留未翻译边界。

- Nesterov 对象关系/报告
  - `GCell.report()`、`GPin.report()`、`GNet.report()` 补齐对象关系、bbox、density box、权重和 WA 累计状态。
  - `BinGrid.reportBins()` 支持导出 bin 样本，`NesterovBase.reportStatus()` 增加 snapshot/SLP/gradient 容器尺寸。
  - `NesterovBaseCommon.reportObjects()`、`reportChangedGCells()` 补齐 gcell/gpin/gnet 样本和 callback changed-gcell 队列报告。
  - 新增 `setCustomNetWeight()`、`resetCustomNetWeights()`，只维护权重状态，不执行 timing/STA 优化。

- Route/Timing/Replace 状态入口
  - `Tile.report()`、`TileGrid.getTile()`、`TileGrid.reportStatus()` 补齐 tile grid 几何和样本报告。
  - `RouteBase.reportCongestion()` 现在包含 tile grid、min-RC 保存 cell/region 数。
  - `TimingBase.addTimingDrivenNet()`、`clearTimingDrivenNets()`、`reportTimingNets()` 补齐 timing-driven net 容器状态；真实 STA slack 筛选、resizer 交互仍抛 `NotImplementedError`。
  - `Replace` 新增 cluster 拷贝读取、debug 报告、cluster 报告，以及 timing/routability/bin/pad/timing weight 配置 setter。

## 第八轮补充

- 对象生命周期
  - `Instance.removePin()`、`Net.removePin()`、`Pin.clearInstance()`、`Pin.clearNet()` 补齐双向关系断开入口。
  - `PlacerBaseCommon.addDbITerm()`、`addDbBTerm()`、`removeDbTerm()` 可按当前 ODB 骨架增删 term pin，并同步 Instance/Net 反向关系。
  - `NesterovBaseCommon.removeGCellForInstance()` / `removeGNetForNet()` 删除对象时会清理 GPin 反向引用；callback 创建/删除 inst/net 后会重建 GPin 关系。

- Placer state snapshot/restore
  - 新增 `GCellSnapshot`，保存/恢复 gcell 位置、density box、density scale、梯度和 change 类型。
  - `NesterovBase.saveSnapshot()` / `revertToSnapshot()` 现在恢复完整 gcell 状态、overflow 和 target density，并在 gcell 数量变化时显式抛 `RuntimeError`。
  - `NesterovPlace.revertToSnapshot()` 修正空 base 误判成功的问题，恢复成功后刷新 DB 与 overflow；新增 `clearSnapshot()` / `reportSnapshot()`。

- 参数校验与报告边界
  - `PlaceOptions.validate()` 增加有限浮点检查，timing-driven 模式要求 timing overflow checkpoint 非空。
  - `Replace` 的 place/nesterov 入口统一校验 `threads` 为正整数，`start_iter` 为非负。
  - `NesterovBase.reportStatus()` 和 `NesterovPlace.reportStatus()` 现在包含 snapshot 细节。

- 未翻译算法边界
  - WA wirelength、FFT density、Nesterov 主循环、routability inflation、STA/resizer 交互等真实数值优化入口继续保留同名函数并抛 `NotImplementedError`，没有加入 demo 或估算替代。
