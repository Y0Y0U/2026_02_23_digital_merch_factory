# Tasks

- [ ] Task 1: 搭建徽章生成模块的基础架构
  - [ ] SubTask 1.1: 在 `properties.py` 中定义 `BadgeProperties` 类 (形状[Circle/Square], 尺寸, 材质选项等)。
  - [ ] SubTask 1.2: 创建 `ui/badge_panels.py` 并定义 `BADGE_PT_MainPanel`。
  - [ ] SubTask 1.3: 创建 `ui/badge_operators.py` 并定义基础 Operator 框架。
  - [ ] SubTask 1.4: 在 `__init__.py` 中注册新类和属性。

- [ ] Task 2: 实现核心徽章生成逻辑 (`core/badge_generator.py`)
  - [ ] SubTask 2.1: 实现 `create_badge_mesh` 函数，支持圆形和方形（带圆角）几何体生成。
  - [ ] SubTask 2.2: 实现 UV 展开逻辑，确保图片正确映射（圆形极坐标/方形UV）。
  - [ ] SubTask 2.3: 实现底托 (Backing) 和 卷边 (Rim) 的几何生成。

- [ ] Task 3: 实现多层材质系统 (`core/badge_materials.py`)
  - [ ] SubTask 3.1: 创建 `BadgeMaterialFactory` 类。
  - [ ] SubTask 3.2: 实现 Base Layer (闪底/素面) 节点组。
  - [ ] SubTask 3.3: 实现 Pattern Layer (图片) 节点组，支持 Alpha 混合。
  - [ ] SubTask 3.4: 实现 Film Layer (覆膜/镭射) 节点组（原理化 BSDF 的 Clearcoat 或独立 Glass BSDF 混合）。
  - [ ] SubTask 3.5: 将材质应用到生成的徽章模型。

- [ ] Task 4: UI 完善与集成测试
  - [ ] SubTask 4.1: 在面板中添加形状选择和材质层配置项。
  - [ ] SubTask 4.2: 验证方形和圆形徽章的生成效果。
  - [ ] SubTask 4.3: 验证材质层的叠加效果（闪底是否可见）。

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Task 3
