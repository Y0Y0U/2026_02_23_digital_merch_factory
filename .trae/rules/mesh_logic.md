---
alwaysApply: false
description: 处理物体时
---
bmesh 优先：在处理顶点、边、面等网格数据时，严禁滥用 bpy.ops（操作符）。必须优先使用 bmesh 模块，以提升运行速度。
减少冗余刷新：严禁在循环体内部调用 bpy.context.view_layer.update()。
对象引用：操作物体时，通过直接引用（Object Reference）进行，避免通过名称字符串查找导致重名冲突。