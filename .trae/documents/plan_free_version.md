# 插件发布与保护方案 (v2)

结合您提出的"反盗版"和"分步更新"需求，本方案进行了重大调整。重点在于**保护核心资产**和**建立可持续的更新机制**。

## 1. 反盗版策略 (Anti-Piracy)

由于 Blender 插件本质是 Python 脚本（开源），完全防止破解是不可能的，但可以增加破解成本。

### 推荐方案：Cython 编译核心模块 (最有效)
将您的核心算法（如 `core/generator.py` 和 `core/image_processing.py`）编译为二进制文件 (`.pyd` 或 `.so`)。
*   **原理**: 将 Python 代码转译为 C 代码并编译，破解者只能看到二进制乱码，极难还原逻辑。
*   **优点**: 保护力度极高，几乎无法被普通用户修改。
*   **缺点**: 需要为不同平台（Windows, Mac Intel/M1, Linux）分别编译。
*   **适用**: 您提到的"完整版"核心功能。

### 辅助方案：在线验证 (License Check)
在插件启动或执行关键功能时，联网验证激活码（如 Gumroad/淘宝订单号）。
*   **优点**: 能有效控制分发。
*   **缺点**: 需要搭建简单的验证服务器，且容易被修改代码绕过（除非配合 Cython 使用）。

### 结论
建议采用 **Cython 编译核心模块 + 简易联网验证** 的组合。对于免费版，则直接提供源码即可。

## 2. 分步发布与功能控制 (Incremental Release)

针对"不一次性放出完整文件，慢慢更新"的策略，建议采用 **模块化架构 + 特性开关**。

### 2.1 架构调整：功能模块化
不要将所有功能写死在 `operators.py` 中。而是将每个大功能（如"彩窗"、"批量处理"）封装为独立的 Python 包。

*   **当前结构**:
    ```text
    ui/operators.py (包含了所有功能的入口)
    ```
*   **建议结构**:
    ```text
    features/
        __init__.py
        basic_generator/  (基础功能 - 免费版/第一版)
        batch_processor/  (批量功能 - 后续更新)
        rainbow_effect/   (彩窗功能 - 后续更新)
    ```

### 2.2 特性开关 (Feature Toggles)
在 `core/config.py` 中定义功能清单。
发布初期，您可以：
1.  **物理隔离**: 直接不打包 `rainbow_effect` 文件夹。
2.  **代码屏蔽**: 在 `config.py` 中将开关设为 `False`。

```python
# core/config.py
class Features:
    ENABLE_BATCH = True      # 第一版开启
    ENABLE_RAINBOW = False   # 第一版关闭（或者代码根本就不在包里）
    ENABLE_CLOUD_MAT = False # 规划中的功能
```

## 3. 实施路线图

### 第一阶段：基础版发布 (The Base)
*   **功能**: 仅包含单图生成、基础材质。
*   **保护**: 核心 `generator.py` 源码发布（或轻度混淆）。
*   **目的**: 积累用户，收集反馈，测试稳定性。

### 第二阶段：高级功能解锁 (The Updates)
*   **功能**: 加入"批量处理"、"彩窗效果"。
*   **保护**: 将新增的核心逻辑（如 `batch_processor.py`）使用 **Cython 编译为 .pyd** 发布。
*   **发布方式**: 用户下载新的 zip 包覆盖安装，或者插件内置"检查更新"功能。

## 4. 针对当前代码的具体修改建议

1.  **拆分 `ui/operators.py`**:
    目前所有 Operator 都在一个文件中，不利于分步更新。
    *   建议拆分为 `ui/ops_basic.py` (基础), `ui/ops_batch.py` (批量), `ui/ops_rainbow.py` (彩窗)。
    *   在 `ui/__init__.py` 中根据配置动态导入这些文件。

2.  **引入动态注册机制**:
    ```python
    # ui/__init__.py
    def register():
        register_basic()
        if config.HAS_BATCH_MODULE:
            try:
                from . import ops_batch
                ops_batch.register()
            except ImportError:
                pass
    ```

这样，当您想发布新功能时，只需把新的 `.py` (或 `.pyd`) 文件放入文件夹，用户重启 Blender 即可看到新功能。
