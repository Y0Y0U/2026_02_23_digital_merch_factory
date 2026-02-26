import bpy  # Blender 主 API，用于注册属性与访问场景
from .utils import system  # 工具检测与系统级辅助函数
from .core import naming  # 命名工具，用于锁定逻辑

def update_lock_state(self, context):
    """
    更新锁定状态：除了控制器和插脚控制器外，锁定其他所有相关对象
    """
    lock = self.lock_non_controllers
    
    # 遍历场景中的所有对象
    for obj in bpy.data.objects:
        # 检查是否属于脚本生成的集合
        is_script_obj = False
        for coll in obj.users_collection:
            try:
                if coll and naming.NamingManager.is_script_generated_collection(coll.name):
                    is_script_obj = True
                    break
            except Exception:
                continue
        
        if not is_script_obj:
            continue
            
        # 判断类型
        # 控制器：名称以“_控制器”结尾
        # 插脚控制器：名称以“插脚控制器_”开头
        is_controller = obj.name.endswith("_控制器")
        is_socket_helper = obj.name.startswith("插脚控制器_")
        
        if is_controller or is_socket_helper:
            # 这些始终保持可选
            obj.hide_select = False
        else:
            # 其他对象根据设置锁定
            obj.hide_select = lock

def update_base_round_corner(self, context):
    """更新选中物体的底板圆角状态"""
    for obj in context.selected_objects:
        # 尝试查找关联的底板
        base_obj = None
        if obj.name.startswith("底板_"):
            base_obj = obj
        else:
            # 如果选中的是立牌或控制器，尝试找其子级中的底板
            for child in obj.children:
                if child.name.startswith("底板_"):
                    base_obj = child
                    break
        
        if base_obj:
            # 找到 Base_Bevel 修改器
            mod = base_obj.modifiers.get("Base_Bevel")
            if mod:
                mod.show_viewport = self.base_use_round_corner
                mod.show_render = self.base_use_round_corner

def update_base_round_radius(self, context):
    """更新选中物体的底板圆角半径"""
    for obj in context.selected_objects:
        # 尝试查找关联的底板
        base_obj = None
        if obj.name.startswith("底板_"):
            base_obj = obj
        else:
            for child in obj.children:
                if child.name.startswith("底板_"):
                    base_obj = child
                    break
        
        if base_obj:
            mod = base_obj.modifiers.get("Base_Bevel")
            if mod:
                mod.width = self.base_round_radius

class AcrylicProperties(bpy.types.PropertyGroup):
    # --- 核心参数 (默认显示) ---
    model_scale: bpy.props.FloatProperty(
        name="模型缩放", 
        description="整体缩放比例 (1.0为原始大小，1.0以上放大，1.0以下缩小)",
        default=1.0, 
        min=0.01
    )
    
    thickness: bpy.props.FloatProperty(
        name="厚度", 
        description="板材厚度，默认0.03",
        default=0.03, 
        min=0.0,
        precision=4
    )

    # --- 高级参数 ---
    offset_px: bpy.props.IntProperty(
        name="扩展 (px)", 
        description="对原图形执行扩展边界，值为0时无边，默认15px",
        default=15, 
        min=0
    )
    
    smoothing_px: bpy.props.IntProperty(
        name="平滑 (px)", 
        description="模糊半径，数值越大越圆滑，值为0时不平滑，默认10px",
        default=10, 
        min=0
    )
    
    threshold: bpy.props.IntProperty(
        name="阈值 (%)", 
        description="调整边缘形态，连带效果有值越大边越宽，不推荐设到40%以下，默认60%",
        default=60, 
        min=1, 
        max=99
    )

    # --- 生成选项 ---
    origin_mode: bpy.props.EnumProperty(
        name="原点位置",
        description="选择生成模型的原点位置",
        items=[
            ('LEFT', "左下角", "保持 SVG 默认原点，最稳定"),
            ('CENTER', "底部中心", "居中，可减少手动调整插脚位置的操作，可能出现未知bug")
        ],
        default='CENTER'
    )
    
    create_base: bpy.props.BoolProperty(
        name="生成底板",
        description="生成与插脚对应的底板模型",
        default=True
    )

    # --- 额外属性 (补全) ---
    use_modifier_extrusion: bpy.props.BoolProperty(
        name="使用修改器挤出",
        description="勾选后使用 Solidify 修改器生成厚度（非破坏性）；不勾选则直接应用挤出（普通挤出）",
        default=False
    )
    
    use_auto_bevel: bpy.props.BoolProperty(
        name="倒角",
        description="为边缘添加倒角效果",
        default=False
    )
    
    bevel_depth: bpy.props.FloatProperty(
        name="深度", 
        description="边缘倒角大小",
        default=0.0005, 
        min=0.0,
        precision=4
    )
    
    create_socket: bpy.props.BoolProperty(
        name="生成插脚",
        description="在底部生成一个方块作为立牌的插脚",
        default=True
    )
    
    socket_width: bpy.props.FloatProperty(
        name="插脚宽度",
        default=0.2,
        min=0.001,
        precision=3
    )
    
    socket_height: bpy.props.FloatProperty(
        name="插脚高度",
        default=0.1,
        min=0.001,
        precision=3
    )
    
    base_width: bpy.props.FloatProperty(
        name="底板宽度",
        default=0.5,
        min=0.001,
        precision=3
    )
    
    base_length: bpy.props.FloatProperty(
        name="底板长度",
        default=0.3,
        min=0.001,
        precision=3
    )
    
    base_use_round_corner: bpy.props.BoolProperty(
        name="底板圆角",
        default=False,
        update=update_base_round_corner
    )
    
    base_round_radius: bpy.props.FloatProperty(
        name="圆角半径",
        default=0.002,
        min=0.0,
        precision=4,
        update=update_base_round_radius
    )
    
    base_use_separate_material: bpy.props.BoolProperty(
        name="独立底板材质",
        description="勾选后，底板将使用单独的材质；否则默认与立牌本体材质一致",
        default=False
    )
    
    base_material: bpy.props.PointerProperty(
        name="底板材质",
        type=bpy.types.Material,
        description="选择应用到底板的材质"
    )
    
    material_to_assign: bpy.props.PointerProperty(
        name="指定材质",
        type=bpy.types.Material,
        description="选择应用到立牌本体的材质"
    )
    
    rainbow_material: bpy.props.PointerProperty(
        name="彩窗材质",
        type=bpy.types.Material,
        description="选择应用到彩窗平面的材质"
    )
    
    use_rainbow_colorful: bpy.props.BoolProperty(
        name="多彩模式",
        description="勾选生成彩虹渐变，不勾选生成黑白渐变",
        default=False
    )

    use_3d_cursor: bpy.props.BoolProperty(
        name="使用 3D 游标位置",
        description="勾选后在 3D 游标处生成；不勾选则在世界原点 (0,0,0) 生成",
        default=False
    )
    
    auto_stand_up: bpy.props.BoolProperty(
        name="自动立起",
        description="生成后自动旋转 90 度使立牌直立",
        default=True
    )
    
    lock_non_controllers: bpy.props.BoolProperty(
        name="锁定",
        description="勾选后，锁定除控制器和插脚控制器以外的所有对象，防止误选，对文件内所有插件生成的对象生效",
        default=False,
        update=update_lock_state
    )
    
    sync_image: bpy.props.BoolProperty(name="同步导入图像", default=True)

    # --- 状态与内部变量 ---
    is_processing: bpy.props.BoolProperty(default=False)  # 内部状态：是否正在处理
    status_text: bpy.props.StringProperty(default="等待开始...")  # 内部状态：状态栏文字
    
    # 工具检查状态
    tools_valid: bpy.props.BoolProperty(default=True)  # 内部状态：工具是否齐全
    missing_tools: bpy.props.StringProperty(default="")  # 内部状态：缺失工具列表

    last_image_path: bpy.props.StringProperty(default="")
    last_batch_collection_name: bpy.props.StringProperty(default="")

    # --- UI 折叠状态 ---
    show_image_settings: bpy.props.BoolProperty(name="图像设置", default=True)
    show_geo_settings: bpy.props.BoolProperty(name="建模设置", default=True)
    show_mat_settings: bpy.props.BoolProperty(name="材质设置", default=True)
    show_base_settings: bpy.props.BoolProperty(name="底座设置", default=True)
    show_rainbow_settings: bpy.props.BoolProperty(name="彩窗设置", default=True)

    # 批次计数器 (文件级持久化)
    batch_sequence_number: bpy.props.IntProperty(
        name="批次序号",
        default=0,
        description="当前文件的批次序号计数器"
    )

