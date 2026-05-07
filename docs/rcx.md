# rcx

## 已实现

- 已建立 OpenROAD `rcx::Ext` 对外入口的 Python 对应类：`Ext`，并提供别名 `OpenRCX`
- 已补齐 `Ext` 的关键入口边界：`extract()`、`write_spef()`、`read_spef()`、`diff_spef()`、`bench_wires()`、`bench_wires_gen()`、`define_process_corner()`、`define_derived_corner()`、`get_ext_db_corner()`、`get_corners()`、`delete_corners()`、`adjust_rc()`
- 已复刻 rcx Tcl/接口层选项结构：`BenchWiresOptions`、`ExtractOptions`、`SpefOptions`、`ReadSpefOpts`、`DiffOptions`、`PatternOptions`
- 已复刻核心主控对象骨架：`extMain`
- 已补齐 corner 状态管理：`extCorner`、`extMain.define_process_corner()`、`extMain.define_derived_corner()`、`extMain.get_ext_db_corner()`、`extMain.get_corners()`、`extMain.delete_corners()`
- 已补齐 RC 模型与规则表骨架：`extRCModel`、`extMetRCTable`、`extDistWidthRCTable`、`extDistRCTable`、`extDistRC`
- 第二轮继续按 OpenROAD `src/rcx/include/rcx/extRCap.h` 深化 RC table 边界：
  `extRCTable`、`extViaModel`、`extMetRCTable.addViaModel()`、`getViaModel()`、
  `allocOverUnderTable()`、`allocDiagUnderTable()`、`extDistWidthRCTable` 的
  diag width/dist 表、`getDiagWidthIndex()`、`getDiagDistIndex()`、`getMetIndexUnder()`
- 已补齐 `extDistRC` 基础访问接口：`Reset()`、`setLogger()`、`set()`、`getFringe()`、`getFringeW()`、`getCoupling()`、`getDiag()`、`getRes()`、`getSep()`、`getTotalCap()`、`setCoupling()`、`setFringe()`、`setFringeW()`、`setRes()`、`addRC()`
- 已补齐 `extDistRCTable` 的第二轮表生命周期边界：`makeComputeTable()`、`findRes()`，
  以及规则读写/插值同名入口 `readRules()`、`readRules_res2()`、`writeRules()`、`interpolate()`
- 已补齐耦合测量流对象边界：`extMeasure`、`extMeasureRC`、`CouplingState`、`CouplingDimensionParams`、`SegmentTables`
- 第二轮继续扩展 `extMeasure` / `extMeasureRC`：补入当前金属层、上下文层、线宽/距离、
  diag/over/under/res 标志、RC model 引用、`calcRes()`、`calcDiagRC()`、
  `measureOverUnderCap()`、`FindCouplingCaps()`、`computeAndStoreRC()`、`OverSubRC()` 等 C++ 同名入口
- 已建立并深化 SPEF 对象边界：`extSpef` 现在保存输入/输出文件、gzip、name map、
  active corner、single pi、term junction xy、增量读取状态，并补齐
  `reinit()`、`setOutSpef()`、`setInSpef()`、`setGzipFlag()`、`setDesign()`、
  `getWriteCorner()`、`setCornerCnt()`、`readBlockIncr()`、`write_spef_nets()`、`writeNet()`
- 已保留 OpenROAD C++ 命名风格字段和函数名，并在 Python 中用中文注释说明对象职责
- 第二轮补齐 `extMain` 的更多顶层状态字段：model map、met RC table、min/max RC 统计表、
  merge/coupling/diagonal/context 标志、当前模型、SPEF 对象反向引用
- 第二轮补齐 `extMain` 的配置流边界：`setExtractionOptions_v2()` 同步 `corner_cnt`、
  `max_res`、`context_depth`、`cc_model`；`adjust_rc()` 同步 res/cc/gndc modify 标志；
  `bench_wires()` / `benchPatternsGen()` 会把公开 options 转成 `extMainOptions` 并解析数值表
- 第二轮补齐 `extMain` 的同名入口边界：`setupMappingTables()`、`makeNetRCsegs()`、
  `couplingFlow()`、`computeCapacitance()`、`getRseg()`、`overPatterns()`、
  `UnderPatterns()`、`OverUnderPatterns()`、`write_spef_nets()`、`getSpef()`、`setMinRC()`、`setMaxRC()`
- `Ext.init_rcx_model()` 现在会按 corner 名初始化 `extRCModel` 和每个 corner 的
  `extMetRCTable`；`Ext.write_spef_nets()` 会把 block/corner 状态下沉到 `extMain/extSpef`

## 未实现

- `extMain::extract` 的真实 RC 网络构建、wire 遍历、cap node / rseg / ccseg 写库流程
- `extMeasureRC` 的 coupling flow、邻居搜索、对角耦合、电阻测量细节
- `extRCModel` / `extDistRCTable` / `extDistWidthRCTable` / `extMetRCTable` 的规则文件解析、
  插值、工艺表读写和 solver pattern 生成；同名入口已保留并抛 `NotImplementedError`
- `extSpef` 的真实 SPEF parser/writer、name map 内容生成、增量 SPEF、diff / calibrate 流程；
  同名入口已保留并抛 `NotImplementedError`
- bench DEF / Verilog / pattern 生成的实际数据库写入；`extMainOptions` 配置边界已保留
- OpenROAD rcx 源码中更细的 `GridTable`、`Wire`、`Track`、`SEQ`、`extSegment`、`dbUtil` 等内部对象翻译
- 按本轮要求，未触碰 `odb` 翻译层，也未实现真实寄生提取、SPEF 解析写出或规则读取算法
