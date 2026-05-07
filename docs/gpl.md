# gpl

## 已实现

- `PlaceOptions`
  - 对应 OpenROAD `gpl::PlaceOptions`
  - 保留默认参数、`skipIo()`、`validate()`

- 顶层入口 `Replace`
  - 对应 OpenROAD `gpl::Replace`
  - 已翻译构造、`setGraphicsInterface()`、`reset()`、`addPlacementCluster()`
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

- Routability / Timing 边界
  - `Tile`
  - `TileGrid`
  - `RouteBaseVars`
  - `RouteBase`
  - `TimingBase`
  - 已保留 RUDY、global router、timing-driven net reweight 的 C++ 函数入口

- 图形调试接口
  - `AbstractGraphics`
  - `GraphicsNone`
  - 默认入口与 OpenROAD 一样使用无图形后端

- 辅助接口
  - `isValidSigType()`
  - `make_replace()`

## 未实现

- `InitialPlace::doBicgstabPlace()` 的稀疏矩阵构建、B2B 模型、BiCGSTAB 求解与坐标回写
- `NesterovBaseCommon` 的 weighted-average wirelength force / gradient / preconditioner
- `NesterovBase` 的 FFT 电势场、density gradient、Nesterov 坐标更新、收敛/发散判定、snapshot/revert 细节
- `NesterovPlace::doNesterovPlace()` 主循环、backtracking、wirelength coefficient 更新、timing/routability 迭代调度
- `RouteBase` 的 RUDY tile 计算、FastRoute/global router 结果读取、routability-driven inflation/revert
- `TimingBase::executeTimingDriven()` 的 STA slack 读取、关键网权重更新、resizer journal 交互
- `runMBFF()` 对应的 MBFF 聚类流程
- 完整 OpenDB ITerm/BTerm/Region/Group/Row 支撑依赖

## 说明

- 当前翻译目标是建立 OpenROAD gpl 的核心对象、入口类和关键函数边界。
- 未翻译算法不会用估算 demo 代替，相关函数显式抛出 `NotImplementedError`。
- 字段名尽量贴近 C++ 成员名，保留尾部 `_`，方便后续逐文件继续对照源码翻译。
