# pdn

## 翻译范围

- 本轮只改 `winroad/pdn.py`、`winroad/pdn/*` 和 `docs/pdn.md`。
- 参考本机 OpenROAD `src/pdn`：
  - `include/pdn/PdnGen.hh`
  - `src/domain.h`
  - `src/grid.h`
  - `src/grid_component.h`
  - `src/rings.h`
  - `src/straps.h`
  - `src/connect.h`
  - `src/via.h`
  - `src/sroute.h`
  - `src/renderer.h`
  - `src/power_cells.h`
  - `src/pdn.tcl`
- Python 侧只建立顶层对象、函数边界、参数保存和对象关系，不写 OpenDB，不生成示例几何。

## Package 拆分

- `winroad/pdn.py` 只保留兼容转发：`from .pdn import *`。
- `winroad/pdn/types.py`：枚举、`Rect`/`Halo`、`SplitCut`、`Shape` 和共享 helper。
- `winroad/pdn/via.py`：`Via`、db via wrapper、via generator、`Connect`。
- `winroad/pdn/component.py`：`GridComponent`、ring/strap/followpin/pad/repair channel。
- `winroad/pdn/grid.py`：`Grid`、`CoreGrid`、`InstanceGrid`、`BumpGrid`、`ExistingGrid`。
- `winroad/pdn/domain.py`：`VoltageDomain`、`PowerCell`、`GridSwitchedPower`。
- `winroad/pdn/sroute.py`：`SRoute`。
- `winroad/pdn/renderer.py`：`PDNRenderer`。
- `winroad/pdn/pdngen.py`：`PdnGen` 和 Tcl 风格顶层函数。
- `winroad/pdn/__init__.py` 聚合导出，`import winroad.pdn` 仍可直接访问原 `pdn.py` 中的公开类和函数。

## 已实现边界

- 枚举/基础类型
  - `ExtensionMode`
  - `StartsWith`
  - `PowerSwitchNetworkType`
  - `GridType`
  - `GridComponentType`
  - `ShapeType`
  - `FailedViaReason`
  - `SplitCut`
  - `Rect`
  - `Halo`

- 顶层入口
  - `PdnGen`
  - `make_pdn_gen()`
  - `initPdnGen()`
  - `makePdnGen()`
  - `deletePdnGen()`
  - `pdngen()`
  - `report_power_grid()`
  - `check_power_grid()`
  - `repair_pdn_vias()`
  - `ripup_power_grid()`
  - `write_power_grid()`

- `PdnGen` 方法边界
  - `init()`
  - `reset()`
  - `resetShapes()`
  - `report()`
  - `findSwitchedPowerCell()`
  - `makeSwitchedPowerCell()`
  - `getDomains()`
  - `findDomain()`
  - `setCoreDomain()`
  - `makeRegionVoltageDomain()`
  - `buildGrids()`
  - `findGrid()`
  - `getGridByName()`
  - `findGridForInstance()`
  - `findGridContainingRect()`
  - `makeCoreGrid()`
  - `makeInstanceGrid()`
  - `makeExistingGrid()`
  - `makeRing()`
  - `makeFollowpin()`
  - `makeStrap()`
  - `makeConnect()`
  - `writeToDb()`
  - `ripUp()`
  - `setDebugRenderer()`
  - `rendererRedraw()`
  - `setAllowRepairChannels()`
  - `filterVias()`
  - `checkSetup()`
  - `repairVias()`
  - `addSrouteConnect()`
  - `createSrouteWires()`
  - `trimShapes()`
  - `updateVias()`
  - `cleanupVias()`
  - `checkDesign()`
  - `ensureCoreDomain()`
  - `updateRenderer()`
  - `importUPF()`

- Voltage domain
  - `VoltageDomain`
  - 已保留 power / switched power / always-on power / ground / secondary nets / region / grids 关系
  - 已建立 `getNets()`、`addGrid()`、`resetGrids()`、`clearGrids()`、`removeGrid()`、`findGrid()`、`getGridByName()`、`report()`、`checkSetup()`

- Grid 对象层
  - `Grid`
  - `CoreGrid`
  - `InstanceGrid`
  - `BumpGrid`
  - `ExistingGrid`
  - 已保留 rings / straps / connect / pin layers / via / switched power cell 关系
  - 已建立 `addRing()`、`addStrap()`、`addConnect()`、`removeStrap()`、`getNets()`、`getGridComponents()`、`getShapes()`、`getVias()`、`findComponent()`、`findConnect()`、`build()`、`resetShapes()`、`ripup()`、`report()`、`checkSetup()`

- Grid component / shape
  - `GridComponent`
  - `Shape`
  - `RingLayer`
  - `Rings`
  - `Straps`
  - `FollowPins`
  - `PadDirectConnectionStraps`
  - `RepairChannelStraps`
  - 已保留 shape list、net 顺序、start-with-power、ring layer/offset/pad-offset、strap pitch/width/spacing/extend/snap/start/end、pad direct connection、repair channel area/repair nets 等字段
  - `GridComponent.build()` 保留 C++ build 顺序边界：layer check、make/refine/cut；实际几何仍在 `makeShapes()`/`cutShapes()` 抛 `NotImplementedError`
  - `Rings.report()`、`Straps.report()`、`PadDirectConnectionStraps.report()`、`RepairChannelStraps.report()` 会展开参数边界

- Connect / via
  - `Connect`
  - `Via`
  - `Enclosure`
  - `DbVia`
  - `DbBaseVia`
  - `DbTechVia`
  - `DbGenerateVia`
  - `DbSplitCutVia`
  - `DbArrayVia`
  - `DbGenerateStackedVia`
  - `DbGenerateDummyVia`
  - `ViaGenerator`
  - `GenerateViaGenerator`
  - `TechViaGenerator`
  - 已保留 cut pitch、fixed vias、max rows/columns、ongrid、split cuts pitch/stagger、via list、failed via report 等边界字段
  - `Connect` 已建立 `getSplitCut()`、`getSplitCutPitch()`、`isSplitCutStaggered()`、`getVias()`、`addVia()`、`clearFailedVias()`、参数化 `report()`
  - `DbBaseVia.getViaReport()` 和 `DbGenerateStackedVia.getViaReport()` 已建立计数报告边界；真实 via 生成继续抛 `NotImplementedError`

- Power switch / sroute / renderer
  - `PowerCell`
  - `GridSwitchedPower`
  - `SRoute`
  - `PDNRenderer`
  - `SRoute.addSrouteConnect()`/`getSrouteConnects()` 只保存 `add_sroute_connect` 参数；`createSrouteWires()` 保留同名算法入口并抛 `NotImplementedError`
  - `PDNRenderer` 保存 enabled/block/logger/grids/selected，支持 `setBlock()`、`setLogger()`、`setGrids()`、`select()`、`clear()`、`report()`；`redraw()` 保留入口并抛 `NotImplementedError`

## 未实现

- `PdnGen::buildGrids()` 的真实 PDN 图形生成、trim、via 更新、cleanup 流程
- `PdnGen::writeToDb()`、`Grid::writeToDb()`、`Shape::writeToDb()`、`Via::writeToDb()` 的 OpenDB 写入
- `Grid::makeShapes()`、`Grid::makeVias()`、`GridComponent::makeShapes()`、`Shape::cut()` 的几何生成/裁剪算法
- `Connect::makeVia()`、`ViaGenerator::build()`、`ViaGenerator::generate()` 及所有 db via wrapper 的真实 via 构造
- `RepairChannelStraps::repairGridChannels()`、`PdnGen::repairVias()` 的 repair channel / repair via 算法
- `SRoute::createSrouteWires()` 的 add_sroute_connect 实现
- `PowerCell::appliesToRow()`、`GridSwitchedPower::build()` 的 power switch 放置和控制网连接
- `ExistingGrid::populate()` 对已有 SPECIALNET 的读取
- `VoltageDomain::getDomainArea()`、`VoltageDomain::getRows()` 的 core/region 几何读取
- UPF 导入、debug renderer redraw、pad direct connection refine/cut 等细节

## 说明

- 当前 Python 层不依赖具体 `odb` 类型，所有 ODB 对象均以 `Any` 保存引用。
- 可安全构建 `PdnGen -> VoltageDomain -> Grid -> Ring/Strap/Connect` 对象树并调用 `report()`、domain/grid lookup、connect/component lookup、sroute 参数保存。
- 涉及真实 PDN 算法、数据库写入或物理几何生成的同名入口会显式抛 `NotImplementedError`，避免误把 demo 行为当作算法结果。

## 第二轮补充重点

- grid component build/write/check/report
  - `GridComponent.build()`、`Grid.build()` 建立 C++ 调用顺序边界，实际 `makeShapes()`/`makeVias()`/`writeToDb()` 不实现。
  - 组件和 grid report 展开 ring、strap、connect、pin layer、repair channel、shape/via count。
- via repair
  - `PdnGen.repairVias()` 先执行 setup 检查，再保留同名算法入口并抛 `NotImplementedError`。
  - `Connect` 增加 failed via 清理和 split cut pitch/stagger 查询。
- sroute
- `PdnGen.addSrouteConnect()` 和 `SRoute.addSrouteConnect()` 只记录 Tcl 参数映射，`createSrouteWires()` 不生成线。
- renderer
  - `PDNRenderer` 增加状态保存和报告，`redraw()` 不绘制。
- domain/grid lookup
  - `VoltageDomain.findGrid()`、`getGridByName()`；`PdnGen.getGridByName()`、`findGridForInstance()`、`findGridContainingRect()`。
- connect/ring/strap 参数边界
  - ring report 包含 layer width/spacing、offset、pad offset、extend、allow out-of-die。
  - strap report 包含 layer、width、pitch、spacing、count、offset、snap、extend、start/end、direction。
  - connect report 包含 fixed vias、tech vias、cut pitch、max rows/columns、ongrid、split cuts、via/failure count。

## 第三轮补充重点

- 参数校验
  - 新增共享 rect/halo/正数/非负数校验 helper；`Shape`、ring offset、instance halo、repair channel area、via area、failed via rect 会做基础合法性检查。
  - ring layer 要求真实 layer 下 width 为正、spacing 非负；strap/followpin/connect 会检查 layer、width、pitch、spacing、cut pitch、max rows/columns 等纯参数。
  - domain/grid/cell/sroute 增加空对象、空名、重复 grid/domain/power switch cell、空 sroute 参数等检查。
- 状态管理
  - component、shape、via、connect 之间维护纯数据回链；重复 add 会去重，clear/reset 会断开 shape/via 关系。
  - grid/domain 添加对象时会校正归属关系并避免重复插入；`PdnGen.reset()` 同步清理 renderer 并按初始化状态重建 sroute 容器。
  - `Connect.filterVias()` 现在只在已指定固定 via 列表中按名称过滤，不触发真实 via 构造。
- report / lookup
  - `PdnGen.report()` 增加 domain/grid 计数；component report 展开 shape report；connect report 展开 via report；renderer report 展开 selected 名称。
  - `InstanceGrid.report()` 展开 instance、halo、boundary、replaceable、valid；`ExistingGrid.report()` 展开已有 shape 计数。
  - `Shape.report()`、`Via.report()`、`SRoute.report()` 提供纯数据报告。

## 验证

- `python -m py_compile` 已覆盖 `winroad/pdn.py` 和 `winroad/pdn/*.py`。
- smoke 覆盖 `PdnGen -> VoltageDomain -> CoreGrid -> Ring/Strap/Connect -> Shape/Via` 对象树、lookup、report、sroute 参数保存、renderer 状态，并确认 `buildGrids()` 仍抛 `NotImplementedError`。

## 第六轮补充重点

- PdnGen config/state export-import
  - `PdnGen.exportConfig()` 导出可复建的纯配置字典：domain、grid、ring/strap/followpin/repair/pad component、connect、sroute、renderer 开关与选择快照。
  - `PdnGen.importConfig()` 从上述配置复建 Python 对象树；引用对象默认按名称字符串保存，可传入 resolver 将名称恢复成本地对象。
  - `PdnGen.exportState()` 在 config 外追加 runtime 状态：component shapes、connect vias、failed vias、summary。
  - `PdnGen.importState()` 先导入配置，再恢复 shape/via/failure runtime 状态；不触发几何生成和 OpenDB 写回。
  - 增加 Tcl/Python 便捷包装：`export_power_grid_config()`、`import_power_grid_config()`、`export_power_grid_state()`、`import_power_grid_state()`。
- report 汇总
  - `PdnGen.reportSummary()` 汇总 domain/grid/shape/via/failed-via/sroute/renderer。
  - `VoltageDomain.summary()`、`Grid.summary()` 提供 domain/grid 级聚合。
  - `PdnGen.report()` 增加 `summary`、结构化 `sroute` 报告和 renderer snapshot。
  - 增加 `report_power_grid_summary()`。
- via failure report
  - `Connect.failedViaReport()` 展开 reason/net/rect 明细。
  - `Grid.viaFailureReport()` 和 `PdnGen.viaFailureReport()` 按层级聚合 failure 总数和 reason 计数。
  - 增加 `report_pdn_via_failures()`。
- renderer selection snapshot
  - `PDNRenderer.selectionSnapshot()` 保存 selected item 的类型和名称。
  - `PDNRenderer.snapshot()` 保存 enabled/block/grids/selected，供 config/state 导出。
- sroute summary
  - `SRoute.summary()` 汇总 connect 数量、包含 net/layer 参数的 connect 数量和参数 key 集。
  - `SRoute.report()` 保留原始参数列表并追加 summary 字段。
- 真实算法边界
  - `buildGrids()`、`writeToDb()`、`repairVias()`、`createSrouteWires()`、renderer `redraw()`、真实 via/shape/db 构造继续显式抛 `NotImplementedError`。

## 第六轮验证

- `python -m py_compile` 已覆盖 `winroad/pdn/*.py`。
- smoke 覆盖 config/state export-import round trip、shape/via/failure 恢复、summary、via failure report、sroute summary、renderer selection snapshot，并确认 `buildGrids()` 仍抛 `NotImplementedError`。

## 第七轮补充重点

- 错误聚合
  - 新增 `PdnIssue`，保存 setup/report 阶段的 `path`、`message`、`severity`。
  - `PdnGen.collectSetupIssues()`、`VoltageDomain.collectSetupIssues()`、`Grid.collectSetupIssues()`、`GridComponent.collectSetupIssues()` 会聚合接口层错误；`checkSetup()` 仍保持原语义，在存在错误时抛 `ValueError`。
  - 新增 `report_pdn_setup_issues()`，可直接取得纯 Python setup 问题列表，不触发真实 PDN 生成。
  - `PdnGen.report()` 增加 `setup_issues`，`reportSummary()` 增加 `setup_issue_count`。

- 几何参数校验
  - 新增 `_validate_optional_rect()`，用于 shape obstruction 等可空几何字段。
  - `Shape` 现在校验 obstruction、iterm/bterm runtime connection 矩形，并在 report 中给出 connection 计数。
  - repair channel 的 `area`、`available_area`、`obs_check_area` 在导入配置时重新走矩形校验，避免绕过 dataclass 初始化检查。
  - `Grid.findShapeContainingRect()` 只查询已存在 runtime shape，不生成几何。

- via/connect 状态
  - 新增 `_normalize_failed_via_reason()`，兼容枚举、导出字符串和 Tcl 风格字符串。
  - `Via.markFailed()` 与 `Connect.addFailedVia()` 统一归一化失败原因。
  - `Connect.failedViaReport()` 同时聚合显式 `failed_vias` 和 runtime `Via.failed`，便于导入状态后保持失败统计一致。
  - `Connect.addVia()` 会补齐 shape 回链；`Grid.resetShapes()`/state import 前清理旧 runtime，避免重复导入产生悬挂或重复 via 关系。

- 导入导出
  - config/state 导入增加版本检查，当前只接受 version 1。
  - config 导入检查重复 voltage domain 和多个 core domain。
  - state 导入恢复 shape obstruction、iterm/bterm connections、via failed reason、failed via 明细，并全部走基础几何校验。
  - repair channel 导入恢复 target strap 索引。

- 真实算法边界
  - `buildGrids()`、`writeToDb()`、`repairVias()`、`createSrouteWires()`、renderer `redraw()`、真实 shape/via/db 构造、ODB 写回、DRC/repair 算法继续显式抛 `NotImplementedError`。

## 第七轮验证

- `python -m py_compile` 已覆盖 `winroad/pdn.py` 和 `winroad/pdn/*.py`。
- smoke 覆盖 core domain/grid/ring/strap/connect 构建、shape obstruction 与 iterm connection state round trip、via failed reason 聚合、explicit failed via 聚合、sroute 参数保存、renderer selection snapshot、setup issue 聚合，并确认 `buildGrids()`、`writeToDb()`、`repairVias()` 仍抛 `NotImplementedError`。

## 第八轮补充重点

- lifecycle / state
  - `SRoute.clear()` 清理 add_sroute_connect 参数缓存，不触发真实 special route ripup。
  - `Connect.resetRuntimeState()` 同时清理 runtime vias 和 failed-via 记录，保留 connect 配置。
  - `PDNRenderer.setGrids()` 现在通过 `addGrid()` 去重，新增 `removeGrid()` 并同步移除 selected 中的 grid。
  - `PdnGen.updateRenderer()` 在 redraw 前刷新当前 domain/grid 列表，但 `redraw()` 仍保留同名入口并抛 `NotImplementedError`。

- 配置/state round trip
  - `PdnGen.exportConfig()` 对 sroute 参数做递归纯数据导出：list/tuple/set/mapping 保持结构，普通标量保持原值，ODB/WinRoad 对象按 `_name()` 引用。
  - `PdnGen.importConfig()` 对 sroute 参数递归恢复；传入 resolver 时会把字符串引用恢复成本地对象。
  - renderer selected 导入会优先把 `CoreGrid`/`InstanceGrid`/`BumpGrid`/`ExistingGrid`/`VoltageDomain` 快照恢复为当前对象树中的对象，无法识别时保留名称。

- 参数校验与错误聚合
  - `Straps.__post_init__()` 和 `checkLayerSpecifications()` 统一检查 `strap_start <= strap_end`。
  - `PowerCell.collectSetupIssues()` 聚合 power switch master/control/switched/always-on/ground 缺失。
  - `GridSwitchedPower.__post_init__()` 校验 grid/cell 并归一化 network，`collectSetupIssues()` 聚合 control 缺失。
  - `Connect.collectSetupIssues()` 聚合空 layer、array cut pitch 缺失、split cut 空 layer/零 pitch。
  - `Grid.collectSetupIssues()` 纳入 connect 自身问题、重复 connect pair warning、switched power cell 问题。
  - `SRoute.collectSetupIssues()` 对缺少 net/layer 或 None 参数给 warning；`PDNRenderer.collectSetupIssues()` 对 selected grid 未注册给 warning。
  - `checkSetup()` 只因 severity 为 `error` 的 issue 抛 `ValueError`，warning 仍通过 report 暴露，避免只读提示阻断真实算法同名入口的边界检查。

- report
  - `SRoute.report()` 增加 `setup_issues` 并对常见 net/layer 单值字段做 `_name()` 展示。
  - `PdnGen.report()` 继续展示 sroute report；config 导出使用单独的 sroute config snapshot，避免 report 展示逻辑污染 round trip。

- 真实算法边界
  - `buildGrids()`、`writeToDb()`、`repairVias()`、`createSrouteWires()`、renderer `redraw()`、真实 shape/via/db 构造、ODB 写回、DRC/repair 算法继续显式抛 `NotImplementedError`。

## 第八轮验证

- `python -m py_compile` 已覆盖 `winroad/pdn.py` 和 `winroad/pdn/*.py`。
- smoke 覆盖 core domain/grid/ring/strap/connect、shape/via failed state、explicit failed via、sroute config round trip、renderer selected 恢复、setup issue error/warning 聚合，并确认 `buildGrids()`、`writeToDb()`、`repairVias()`、`createSrouteWires()` 仍抛 `NotImplementedError`。
