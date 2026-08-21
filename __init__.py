bl_info = {
    "name": "Digital Merch Factory",
    "author": "yyu",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Digital Merch",
    "description": "一键生成亚克力立牌",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
    "category": "Object",
    "license": "GPL-2.0-or-later",
}

# Last updated: 2026-02-24
import bpy  # Blender 主 API
from . import properties  # 属性定义
from . import preferences  # 偏好设置
from .ui import panels, operators  # UI 面板与操作器
from .utils import system  # 工具检测

classes = (
    preferences.DigitalMerchPreferences,  # 插件首选项
    properties.AcrylicProperties,  # 属性组
    operators.ACRYLIC_OT_ProcessImage,  # 主流程操作器
    operators.ACRYLIC_OT_DeleteSelected,  # 删除选中
    operators.ACRYLIC_OT_DeleteAllGenerated,  # 删除全部脚本模型
    operators.ACRYLIC_OT_ReconstructLast,  # 重新生成
    operators.ACRYLIC_OT_ResetToDefaults,  # 恢复默认数值（不影响开关）
    operators.ACRYLIC_OT_CreateDefaultAcrylicMaterial,  # 默认亚克力材质
    operators.ACRYLIC_OT_CreateDefaultRainbowMaterial,  # 默认彩窗材质
    operators.ACRYLIC_OT_CreateDefaultBaseMaterial,  # 默认底板材质
    operators.ACRYLIC_OT_CreateRainbowFromSelection,  # 生成彩窗
    panels.ACRYLIC_PT_MainPanel,
    panels.ACRYLIC_PT_ImageSettings,
    panels.ACRYLIC_PT_GeometrySettings,
    panels.ACRYLIC_PT_MaterialSettings,
    panels.ACRYLIC_PT_BaseSettings,
    panels.ACRYLIC_PT_RainbowSettings,
    panels.ACRYLIC_PT_Management,
)

@bpy.app.handlers.persistent
def check_tools_handler(dummy):
    """在文件加载或启用插件时检查外部工具是否齐全"""
    # load_post handler 需要一个占位参数
    scene = bpy.context.scene  # 获取当前场景
    if hasattr(scene, "acrylic_props"):  # 确保属性已注册
        missing = system.check_tools_exist()  # 检查工具
        if missing:
            scene.acrylic_props.tools_valid = False  # 标记工具缺失
            scene.acrylic_props.missing_tools = ", ".join(missing)  # 写入缺失列表
            scene.acrylic_props.status_text = "错误: 工具缺失"  # 状态提示
            print(f"[DigitalMerchFactory] Missing tools: {missing}")  # 控制台日志
        else:
            scene.acrylic_props.tools_valid = True  # 工具齐全
            scene.acrylic_props.missing_tools = ""  # 清空缺失
            scene.acrylic_props.status_text = "就绪"  # 状态提示
            print("[DigitalMerchFactory] Tools check passed.")  # 控制台日志

def register():
    for cls in classes:  # 逐个注册类
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.acrylic_props = bpy.props.PointerProperty(type=properties.AcrylicProperties)  # 注册场景属性
    
    # 注册加载后检查工具的 handler
    if check_tools_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(check_tools_handler)  # 挂载加载后检查
    
    # 也尝试立即检查一次（某些上下文 scene 可能尚未完全就绪，因此失败也不影响后续 handler 检查）
    scene = getattr(bpy.context, "scene", None)
    if scene and hasattr(scene, "acrylic_props"):
        check_tools_handler(None)

def unregister():
    if check_tools_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(check_tools_handler)  # 移除加载后检查
        
    if hasattr(bpy.types.Scene, "acrylic_props"):
        del bpy.types.Scene.acrylic_props  # 移除场景属性
    
    for cls in reversed(classes):  # 逆序注销
        bpy.utils.unregister_class(cls)
