# UI 参数配置表 (UI_PARAMETERS.md)

此文档列出了插件中所有可配置的 UI 参数及其默认值。
您可以直接修改表格中的 **"默认值"** 列，修改完成后请通知助手，助手将根据此文档批量更新代码。

## 参数类型说明
- **Bool (开关)**: 对应 Blender 界面中的复选框。填写 `True` (勾选) 或 `False` (不勾选)。
- **Float/Int (数值)**: 对应数值输入框或滑动条。请确保填写的数值在“范围”允许内。
- **Enum (下拉)**: 对应下拉菜单。请填写“范围/选项”中列出的某个具体的 KEY (例如 `'LEFT'`)。

## 参数列表

| 变量名 | UI 名称 | 类型/样式 | 默认值 (请修改此列) | 范围/选项 | 描述 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `model_scale` | 模型缩放 | Float (数值) | `1.0` | Min: 0.01 | 整体缩放比例 |
| `thickness` | 厚度 | Float (数值) | `3` | Min: 0.0 | 板材厚度，默认3 |
| `offset_px` | 扩展 (px) | Int (整数) | `15` | Min: 0 | 对原图形执行扩展边界，值为0时无边，默认15px |
| `smoothing_px` | 平滑 (px) | Int (整数) | `10` | Min: 0 | 模糊半径，数值越大越圆滑，值为0时不平滑，默认10px |
| `threshold` | 阈值 (%) | Int (整数) | `60` | Min: 1, Max: 99 | 调整边缘形态，连带效果有值越大边越宽，不推荐设到40%以下，默认60% |
| `origin_mode` | 原点位置 | Enum (下拉) | `'LEFT'` | 'LEFT': 左下角 (稳定)<br>'CENTER': 底部中心 (推荐) | 选择生成模型的原点位置 |
| `auto_stand_up` | 自动立起 | Bool (开关) | `True` | True / False | 生成后自动旋转 90 度使立牌直立 |
| `create_base` | 生成底座 | Bool (开关) | `True` | True / False | 生成与插口对应的底座模型 |
| `use_modifier_extrusion` | 使用修改器挤出 | Bool (开关) | `False` | True / False | 勾选后使用 Solidify 修改器生成厚度（非破坏性）；不勾选则直接应用挤出（普通挤出） |
| `use_auto_bevel` | 倒角 | Bool (开关) | `False` | True / False | 为边缘添加倒角效果 |
| `bevel_depth` | 深度 | Float (数值) | `0.0005` | Min: 0.0 | 边缘倒角大小 |
| `create_socket` | 生成底座插口 | Bool (开关) | `True` | True / False | 在底部生成一个方块作为立牌的连接处 |
| `socket_width` | 插口宽度 | Float (数值) | `0.02` | Min: 0.001 |  |
| `socket_height` | 插口高度 | Float (数值) | `0.01` | Min: 0.001 |  |
| `base_width` | 底座宽度 | Float (数值) | `0.04` | Min: 0.001 |  |
| `base_length` | 底座长度 | Float (数值) | `0.06` | Min: 0.001 |  |
| `base_use_round_corner` | 底座圆角 | Bool (开关) | `True` | True / False |  |
| `base_round_radius` | 圆角半径 | Float (数值) | `0.002` | Min: 0.0 |  |
| `base_use_separate_material` | 独立底座材质 | Bool (开关) | `False` | True / False | 勾选后，底座将使用单独的材质；否则默认与立牌本体材质一致 |
| `use_rainbow_colorful` | 多彩模式 | Bool (开关) | `True` | True / False | 勾选生成彩虹渐变，不勾选生成黑白渐变 |
| `use_3d_cursor` | 使用 3D 游标位置 | Bool (开关) | `False` | True / False | 勾选后在 3D 游标处生成；不勾选则在世界原点 (0,0,0) 生成 |
| `lock_non_controllers` | 锁定 | Bool (开关) | `False` | True / False | 勾选后，锁定除控制器和插口辅助体以外的所有对象，防止误选 |
| `sync_image` | 同步导入图像 | Bool (开关) | `True` | True / False |  |
