# rcx

## 已实现

- 已建立 OpenROAD `rcx::Ext` 对外入口的 Python 对应类：`Ext`，并提供别名 `OpenRCX`
- 已补齐 `Ext` 的关键入口边界：`extract()`、`write_spef()`、`read_spef()`、`diff_spef()`、`bench_wires()`、`bench_wires_gen()`、`define_process_corner()`、`define_derived_corner()`、`get_ext_db_corner()`、`get_corners()`、`delete_corners()`、`adjust_rc()`
- 已复刻 rcx Tcl/接口层选项结构：`BenchWiresOptions`、`ExtractOptions`、`SpefOptions`、`ReadSpefOpts`、`DiffOptions`、`PatternOptions`
- 已复刻核心主控对象骨架：`extMain`
- 已补齐 corner 状态管理：`extCorner`、`extMain.define_process_corner()`、`extMain.define_derived_corner()`、`extMain.get_ext_db_corner()`、`extMain.get_corners()`、`extMain.delete_corners()`
- 已补齐 RC 模型与规则表骨架：`extRCModel`、`extMetRCTable`、`extDistWidthRCTable`、`extDistRCTable`、`extDistRC`
- 已补齐 `extDistRC` 基础访问接口：`Reset()`、`setLogger()`、`set()`、`getFringe()`、`getFringeW()`、`getCoupling()`、`getDiag()`、`getRes()`、`getSep()`、`getTotalCap()`、`setCoupling()`、`setFringe()`、`setFringeW()`、`setRes()`、`addRC()`
- 已补齐耦合测量流对象边界：`extMeasure`、`extMeasureRC`、`CouplingState`、`CouplingDimensionParams`、`SegmentTables`
- 已建立 SPEF 对象边界：`extSpef`
- 已保留 OpenROAD C++ 命名风格字段和函数名，并在 Python 中用中文注释说明对象职责

## 未实现

- `extMain::extract` 的真实 RC 网络构建、wire 遍历、cap node / rseg / ccseg 写库流程
- `extMeasureRC` 的 coupling flow、邻居搜索、对角耦合、电阻测量细节
- `extRCModel` 的规则文件解析、插值、工艺表读写和 solver pattern 生成
- `extSpef` 的真实 SPEF 读写、name map、增量 SPEF、diff / calibrate 流程
- bench DEF / Verilog / pattern 生成的实际数据库写入
- OpenROAD rcx 源码中更细的 `GridTable`、`Wire`、`Track`、`SEQ`、`extSegment`、`extViaModel`、`dbUtil` 等内部对象翻译
