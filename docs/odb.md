# odb

## 已实现

- Python 入口文件已建立
- 已复刻核心对象骨架：`DbDatabase`、`DbChip`、`DbBlock`、`DbNet`、`DbInst`
- 已补齐基础底层对象：`DbTech`、`DbLib`、`DbMaster`、`DbBox`
- 已补齐连接层对象：`DbTechLayer`、`DbWire`、`DbVia`、`DbMTerm`、`DbITerm`
- 已提供基础创建接口：`create_database()`、`create_chip()`、`create_block()`
- 已提供工艺/库/连接对象创建接口：`create_tech()`、`create_lib()`、`create_tech_layer()`、`create_wire()`、`create_via()`、`create_mterm()`、`create_iterm()`
- 已提供基础状态接口：`is_schema()`、`is_less_than_schema()`
- 已提供实例坐标接口：`DbInst.set_origin()`
- 已提供 `DbBox.is_oct()`、`DbBox.get_type()`
- 已提供 `DbWire.length()`
- 已提供 `DbITerm.get_mterm()`、`DbITerm.get_inst()`

## 未实现

- OpenDB 完整类体系翻译
- 读写、序列化、迭代器和数据库持久化细节
