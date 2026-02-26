# Badge Generator Spec (马口铁徽章生成模块)

## Why
用户需要一个独立于现有亚克力生成流程的模块，专门用于制作“马口铁徽章”（Badge/Button）。
目前的亚克力生成器生成的模型是扁平挤出的，不符合徽章通常具有的“凸起曲面”和“圆形/方形”的金属背底结构。
创建一个独立的模块可以避免现有代码逻辑过于复杂，同时满足特定的周边（Merch）制作需求。

## What Changes
- **UI 变更**:
  - 在 N-Panel 中新增一个 "Badge" (徽章) 面板或子标签页。
  - 新增徽章专用的参数设置区（形状、尺寸、凸起程度、背底材质等）。
- **新增核心逻辑**:
  - `core/badge_generator.py`: 负责生成徽章的几何体（圆顶/方顶曲面 + 卷边底托 + 别针结构）。
  - `properties.py`: 新增 `BadgeProperties` 类。
  - `ui/badge_operators.py`: 新增徽章生成的 Operator。
  - `ui/badge_panels.py`: 新增徽章生成的 Panel。
- **新增材质逻辑**:
  - `core/badge_materials.py`: 实现复杂的“三层材质”系统（闪底 + 图案 + 覆膜）。

## Impact
- **Affected specs**: 无直接冲突，独立于 Acrylic 模块。
- **Affected code**: 
  - `__init__.py` (需要注册新模块)。
  - `properties.py` (新增属性类)。
  - `ui/panels.py` (可能需要调整以容纳新面板，或者新建 `ui/badge_panels.py`)。

## ADDED Requirements

### Requirement: Badge Parameter Configuration
系统应提供以下参数供用户调整：
- **形状 (Shape)**: 
  - *圆形 (Circle)*: 默认。
  - *方形 (Square)*: 带圆角，类似圆角矩形徽章。
- **尺寸 (Size)**: 
  - 直径 (Diameter) / 边长 (Side Length)。
  - 圆角半径 (Corner Radius, 仅方形)。
- **厚度 (Thickness)**: 徽章的整体厚度。
- **凸起高度 (Convexity)**: 表面的弧度/拱起高度。

### Requirement: Layered Material System (闪底-图案-覆膜)
系统应生成包含三层结构的材质节点树：
1.  **底层 (Base Layer)**: 
    - 支持 *素面 (Plain)*、*细闪 (Glitter)*、*全息 (Holographic)* 等效果。
    - 提供颜色或纹理输入。
2.  **图案层 (Pattern Layer)**: 
    - 用户输入的图片。
    - 支持 Alpha 混合或正片叠底 (Multiply) 模式（用于透出底层的闪粉效果）。
3.  **覆膜层 (Film Layer)**: 
    - *光面 (Glossy)*: 高光泽度塑料感。
    - *磨砂 (Matte)*: 低光泽度漫反射。
    - *星幻/镭射 (Holo Pattern)*: 表面带有星星/爱心等纹理的法线或高光贴图。

### Requirement: Geometry Generation
- **Circular Badge**: 标准圆形凸起 + 卷边 + 底托。
- **Square Badge**: 圆角方形凸起 + 卷边 + 底托。
- **Backing**: 简单的金属底托，可选是否生成别针结构。

#### Scenario: Generate 58mm Glitter Badge
- **WHEN** 用户选择一张半透明图片，选择“圆形”，底材选“细闪银”，覆膜选“光面”。
- **THEN** 生成一个 58mm 圆形徽章，表面有银色细闪透过图片显示，且表面有高光塑料质感。

## MODIFIED Requirements
无。此为新增模块。
