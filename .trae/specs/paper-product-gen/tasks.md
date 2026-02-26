# 任务列表 (Tasks)

- [ ] 任务 1: 重构图像处理
  - [ ] 子任务 1.1: 修改 `core/image_processing.py:process_image`，使其接受 `offset`, `blur`, `threshold` 作为显式参数，而不是读取 `context.scene.acrylic_props`。
  - [ ] 子任务 1.2: 更新 `ui/operators.py`（亚克力操作符）以从 `acrylic_props` 传递这些参数。
  - [ ] 子任务 1.3: 验证亚克力生成功能是否仍像以前一样工作。

- [ ] 任务 2: 实现纸品属性与 UI
  - [ ] 子任务 2.1: 创建 `properties_paper.py`（或添加到 `properties.py`），包含 `PaperProperties` 类。
    - 字段: `type` (枚举: 矩形, 异形), `width` (浮点), `thickness` (浮点), `curved` (布尔), `curve_amount` (浮点)。
  - [ ] 子任务 2.2: 在 `__init__.py` 中注册 `PaperProperties` 并附加到 `bpy.types.Scene`。
  - [ ] 子任务 2.3: 创建 `ui/panel_paper.py`（或添加到 `ui/panels.py`），包含 `PAPER_PT_MainPanel`。
    - 类别: "Paper"（或者如果要分组则用 "Merch"，但按要求保持独立则用 "Paper"）。
    - 绘制新属性的逻辑。

- [ ] 任务 3: 实现纸品生成逻辑
  - [ ] 子任务 3.1: 创建 `core/paper_generator.py`。
  - [ ] 子任务 3.2: 实现 `create_paper_model` 函数。
    - "矩形"模式逻辑：创建平面，设置尺寸，设置材质。
    - "异形"模式逻辑：使用 `process_image` 获取 SVG，导入，挤出。
    - "弯曲"逻辑：如果请求，添加简易形变修改器（弯曲）。
  - [ ] 子任务 3.3: 在 `ui/operators.py`（或新文件）中实现 `Paper_OT_process_image` 操作符以处理按钮点击。

- [ ] 任务 4: 集成与清理
  - [ ] 子任务 4.1: 确保所有新文件在 `__init__.py` 中被导入和注册。
  - [ ] 子任务 4.2: 验证“纸品”面板是否出现并独立运行。
