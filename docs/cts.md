# cts

## 已实现

- 模块入口从空壳扩展为 OpenROAD `src/cts` 核心对象边界翻译。
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
- 翻译 `TechChar.h` 特征化表核心容器：
  - `WireSegment`
  - `TechChar`
  - wire segment 创建、key 计算、按 key 遍历、基础 report 字段
- 翻译 `TreeBuilder.h` 树构建器边界：
  - `TreeType`
  - `TreeBuilder`
  - 子树关系、buffer 标记集合、blockage/合法化入口、insertion delay、top buffer/top input net/driving net 等字段接口
- 翻译 `HTreeBuilder.h` H-tree 入口：
  - `LevelTopology`
  - `SegmentBuilder`
  - `HTreeBuilder`
  - branching point、wire segment、sink region、sibling、candidate location 等关键接口
- 翻译 `SinkClustering.h` 聚类入口：
  - `Matching`
  - `SinkClustering`
  - point/cap 输入、matchings、solution、wirelength、scale/max diameter/max size 查询接口
- 翻译 `LatencyBalancer.h` 延迟平衡入口：
  - `GraphNode`
  - `LatencyBalancer`
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

## 未实现

- `TechChar.cpp` 中真实 STA/Liberty/寄生参数特征化流程。
- `TreeBuilder.cpp` 中 blockage 初始化、merge、合法化检查与查找。
- `HTreeBuilder.cpp` 中 H-tree 拓扑构建、segment 插 buffer、聚类细化、legalize、plot。
- `SinkClustering.cpp` 中 theta 归一化、matching、容量/直径约束搜索。
- `LatencyBalancer.cpp` 中 STA 初始化、graph 构建、delay buffer 插入与传播。
- `TritonCTS.cpp` 中完整 run 流程、clock root 查找、DB 写回、NDR 写回、macro/register 分树、dummy load、clock net repair。

## 说明

- 当前实现不是 demo 估算，而是按 OpenROAD C++ 类、字段、入口函数边界建立 Python 版本。
- 尚未逐源码翻译的算法函数保留同名入口并显式抛出 `NotImplementedError`。
- 对外接口名尽量保持 C++ 命名，字段名保留尾下划线风格，便于后续继续对照源码翻译。
