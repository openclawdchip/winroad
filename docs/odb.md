# odb

## 已实现

- Python 入口文件已建立
- 已复刻核心对象骨架：`DbDatabase`、`DbChip`、`DbBlock`、`DbNet`、`DbInst`
- 已补齐基础底层对象：`DbTech`、`DbLib`、`DbMaster`、`DbBox`
- 已补齐连接层对象：`DbTechLayer`、`DbWire`、`DbVia`、`DbMTerm`、`DbITerm`
- 已补齐顶层 block 相关对象：`DbProperty`、`DbRow`、`DbBTerm`、`DbBPin`、`DbGuide`、`DbGroup`
- 已提供基础创建接口：`create_database()`、`create_chip()`、`create_block()`
- 已提供工艺/库/连接对象创建接口：`create_tech()`、`create_lib()`、`create_tech_layer()`、`create_wire()`、`create_via()`、`create_mterm()`、`create_iterm()`
- 已提供 block 侧创建接口：`create_row()`、`create_bterm()`、`create_bpin()`、`create_guide()`、`create_group()`、`create_property()`
- 已提供基础状态接口：`is_schema()`、`is_less_than_schema()`
- 已提供实例坐标接口：`DbInst.set_origin()`
- 已提供 `DbBox.is_oct()`、`DbBox.get_type()`
- 已提供 `DbWire.length()`
- 已提供 `DbITerm.get_mterm()`、`DbITerm.get_inst()`
- 已提供 `DbProperty.set_value()`、`DbProperty.get_value()`
- 已提供 `DbRow.get_origin()`、`DbRow.get_site_count()`
- 已提供 `DbBTerm.connect()`、`DbBTerm.disconnect()`、`DbBTerm.connect_modnet()`、`DbBTerm.add_bpin()`、`DbBTerm.set_io_type()`、`DbBTerm.set_sig_type()`、`DbBTerm.set_mirrored_constraint_region()`
- 已提供 `DbBPin.add_box()`、`DbBPin.set_placement_status()`、`DbBPin.set_min_spacing()`、`DbBPin.set_effective_width()`、`DbBPin.get_bterm()`、`DbBPin.get_boxes()`
- 已提供 `DbGuide.set_box()`
- 已提供 `DbGroup.add_inst()`、`DbGroup.add_group()`、`DbGroup.add_power_net()`、`DbGroup.add_ground_net()`

## 未实现

- OpenDB 完整类体系翻译
- 读写、序列化、迭代器和数据库持久化细节
