# cts

## 已实现

- 模块入口从空壳扩展为 OpenROAD `src/cts` 核心对象边界翻译。
- 第二轮继续按 OpenROAD `src/cts` 当前源码边界深化，范围仍限 CTS 顶层 Python 骨架，不翻译/引入 `odb` 实现。
- 翻译 `Util.h` 基础几何工具：
  - `fuzzyEqual`
  - `fuzzyEqualOrGreater`
  - `fuzzyEqualOrSmaller`
  - `Point`
  - `Box`
- 翻译 `Clock.h` 时钟网络数据模型：
  - `InstType`
  - `ClockInst`
  - `ClockSubNet`
  - `Clock`
  - sink region、sink/buffer/subnet 遍历、driver/net/pin 关联接口
- 翻译 `CtsOptions.h` 参数入口：
  - `NdrStrategy`
  - `MasterType`
  - `CtsOptions`
  - clock nets、buffer list、root/sink/tree buffer、DBU、聚类、特征化、dummy load、NDR、repair clock nets 等 set/get/reset 边界
  - 对齐 C++ 默认值：sink clustering、max slew、leaf sinks、characterization steps、fake LUT、leaf buffer、buffer distance ratio、obstruction aware、insertion delay、dummy load、NDR half 等默认状态
  - 补齐 skip nets、observer、metrics、fanout、diameter/cluster size、macro cluster、static layers、inferred flags、sink buffer max-cap derate、delay buffer derate、CTS library、buffer/dummy count 等接口
- 翻译 `TechChar.h` 特征化表核心容器：
  - `WireSegment`
  - `TechChar`
  - wire segment 创建、key 计算、按 key 遍历、基础 report 字段
  - 补齐 LUT/characterization 外层字段：length/load/slew bounds、actual min input cap、length unit、cap/res per DBU、master/wirelength/load/slew sweep、solution map、key-to-segment 索引
  - 补齐 `WireSegment` buffer location/master、power、delay、first/last wirelength 查询接口
- 翻译 `TreeBuilder.h` 树构建器边界：
  - `TreeType`
  - `TreeBuilder`
  - 子树关系、buffer 标记集合、blockage/合法化入口、insertion delay、top buffer/top input net/driving net 等字段接口
  - 补齐 leaf tree 判断、tree buffer level、first/second sink driver、tree-level buffer、bbox 判断、occupied loc commit/uncommit、sink insertion delay map、DB/logger/TechChar/top net/top buffer 字段入口
- 翻译 `HTreeBuilder.h` H-tree 入口：
  - `LevelTopology`
  - `SegmentBuilder`
  - `HTreeBuilder`
  - branching point、wire segment、sink region、sibling、candidate location 等关键接口
  - 补齐 `SegmentBuilder` build/force buffer/driving subnet/buffer level 边界
  - 补齐 branch point parent/subnet/sink location、output slew/cap、remaining length、current wirelength、wire segment unit、legalize/plot/cluster/refine/assign/computeMinDelaySegment 等同名入口
- 翻译 `SinkClustering.h` 聚类入口：
  - `Matching`
  - `SinkClustering`
  - point/cap 输入、matchings、solution、wirelength、scale/max diameter/max size 查询接口
  - 补齐 matching `getP0/getP1`、theta index、sink clusters、best solution、scale factor、normalize/theta/sort/plot/findBestMatching/limit check 边界
- 翻译 `LatencyBalancer.h` 延迟平衡入口：
  - `GraphNode`
  - `LatencyBalancer`
  - 补齐 graph node id、children ids、arrival、delay buffer count、input term 字段
  - 补齐 STA 初始化、leaf builder 查找、graph 构建、arrival/buffer delay 计算、delay buffer 插入、propagate clock、showGraph 等入口
- 翻译 `TritonCTS.h` 顶层入口类：
  - `TritonCTS`
  - `runTritonCts`
  - `reportCtsMetrics`
  - `getParms`
  - `getCharacterization`
  - `getBlock`
  - `setClockNets`
  - `setBufferList`
  - `setRootBuffer`
  - `getRootBufferToString`
  - `resetRootBuffer`
  - `setSinkBuffer`
  - builder 创建/遍历、characterization setup/check、NDR level 边界、clock 计数、clock network report 等接口
  - 补齐 root/sink buffer selection、buffer fanout limit、clock root/tree 初始化、macro/register 分树、DB 写回、NDR 写回、clock buffer/dummy load、ideal output cap、clock propagation、repair clock nets、macro/register latency balance 等同名入口

## 未实现

- `TechChar.cpp` 中真实 STA/Liberty/寄生参数特征化流程。
- `TreeBuilder.cpp` 中 blockage 初始化、merge、合法化检查与查找。
- `HTreeBuilder.cpp` 中 H-tree 拓扑构建、segment 插 buffer、聚类细化、legalize、plot。
- `SinkClustering.cpp` 中 theta 归一化、matching、容量/直径约束搜索。
- `LatencyBalancer.cpp` 中 STA 初始化、graph 构建、delay buffer 插入与传播。
- `TritonCTS.cpp` 中完整 run 流程、clock root 查找、DB 写回、NDR 写回、macro/register 分树、dummy load、clock net repair。
- 真实 CTS 构树、合法化、DB 写回、STA/OpenDB/Resizer 联动入口全部保留同名函数并显式抛出 `NotImplementedError`，避免伪造算法行为。

## 说明

- 当前实现不是 demo 估算，而是按 OpenROAD C++ 类、字段、入口函数边界建立 Python 版本。
- 尚未逐源码翻译的算法函数保留同名入口并显式抛出 `NotImplementedError`。
- 对外接口名尽量保持 C++ 命名，字段名保留尾下划线风格，便于后续继续对照源码翻译。
- 本轮只修改 `winroad/cts.py` 与 `docs/cts.md`；不触碰 `odb`，不回滚其他文件改动。
