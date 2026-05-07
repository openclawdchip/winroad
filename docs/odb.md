# odb

## 已实现

- Python 入口文件已建立
- 已复刻核心对象骨架：`DbDatabase`、`DbChip`、`DbBlock`、`DbNet`、`DbInst`
- 已提供基础创建接口：`create_database()`、`create_chip()`、`create_block()`
- 已提供基础状态接口：`is_schema()`、`is_less_than_schema()`
- 已提供实例坐标接口：`DbInst.set_origin()`

## 未实现

- OpenDB 完整类体系翻译
- `dbTech`、`dbLib`、`dbMaster`、`dbBox` 等细分对象
- 读写、序列化、迭代器和数据库持久化细节
