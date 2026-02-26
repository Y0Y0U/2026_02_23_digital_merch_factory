import bpy

class DigitalMerchPreferences(bpy.types.AddonPreferences):
    # 此属性必须与插件目录名一致，否则无法在偏好设置中显示
    # 在 __init__.py 中 bl_idname = __name__，因为 __name__ 是包名
    # 在此文件中，__package__ 应该是包名
    bl_idname = __package__

    controller_scale: bpy.props.FloatProperty(
        name="控制器大小",
        description="调整生成控制器时的大小",
        default=2.5,
        min=0.1,
        max=100.0
    )

    auto_stand_up: bpy.props.BoolProperty(
        name="自动立起",
        description="生成后自动旋转 90 度使立牌直立",
        default=True
    )

    batch_prefix: bpy.props.StringProperty(
        name="批次集合前缀",
        description="自动生成的批次集合名称前缀",
        default="立牌批次"
    )

    model_prefix: bpy.props.StringProperty(
        name="模型集合前缀",
        description="自动生成的模型集合名称前缀",
        default="亚克力"
    )

    svg_prefix: bpy.props.StringProperty(
        name="SVG对象前缀",
        description="导入的SVG曲线对象名称前缀",
        default="亚克力"
    )

    plane_prefix: bpy.props.StringProperty(
        name="图案对象前缀",
        description="生成的图案平面对象名称前缀",
        default="图案"
    )

    rainbow_prefix: bpy.props.StringProperty(
        name="彩窗对象前缀",
        description="生成的彩窗对象名称前缀",
        default="彩窗"
    )

    controller_suffix: bpy.props.StringProperty(
        name="控制器后缀",
        description="控制器对象的名称后缀",
        default="_控制器"
    )

    socket_prefix: bpy.props.StringProperty(
        name="插脚控制器前缀",
        description="插脚控制器对象的名称前缀",
        default="插脚控制器"
    )

    base_prefix: bpy.props.StringProperty(
        name="底板对象前缀",
        description="底板对象的名称前缀",
        default="底板"
    )

    safety_master_switch: bpy.props.BoolProperty(
        name="安全总开关",
        description="启用后，执行删除、重置等危险操作前会弹出确认框",
        default=True
    )

    confirm_delete_selected: bpy.props.BoolProperty(
        name="确认删除选中",
        description="删除选中对象时是否需要确认",
        default=True
    )

    confirm_delete_all: bpy.props.BoolProperty(
        name="确认删除全部",
        description="删除全部生成对象时是否需要确认",
        default=True
    )

    confirm_reset: bpy.props.BoolProperty(
        name="确认重置参数",
        description="重置参数时是否需要确认",
        default=True
    )

    batch_name_mode: bpy.props.EnumProperty(
        name="批次命名模式",
        description="选择批次集合的命名规则",
        items=[
            ('TIMESTAMP', "时间码 (默认)", "使用当前日期时间 (YYYYMMDD_HHMMSS)"),
            ('NUMBER', "数字正序", "自动递增数字 (01, 02, ...)"),
            ('ALPHA', "字母正序", "自动递增字母 (A, B, ...)"),
        ],
        default='TIMESTAMP'
    )

    model_name_mode: bpy.props.EnumProperty(
        name="模型命名模式",
        description="选择生成模型的命名规则",
        items=[
            ('FILENAME_INDEX', "文件名 + 序号 (默认)", "前缀_序号_文件名"),
            ('FILENAME', "仅文件名", "前缀_文件名"),
            ('NUMBER', "仅数字序号", "前缀_序号"),
            ('ALPHA', "仅字母序号", "前缀_字母"),
            ('TIMESTAMP', "时间码", "前缀_时间戳_序号"),
        ],
        default='FILENAME_INDEX'
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "controller_scale")
        layout.prop(self, "auto_stand_up")
        
        box = layout.box()
        box.label(text="命名设置")
        
        row = box.row()
        row.prop(self, "batch_name_mode", text="批次规则")
        row.prop(self, "model_name_mode", text="模型规则")
        
        box.prop(self, "batch_prefix")
        box.prop(self, "model_prefix")
        box.prop(self, "svg_prefix")
        box.prop(self, "plane_prefix")
        box.prop(self, "rainbow_prefix")
        box.prop(self, "controller_suffix")
        box.prop(self, "socket_prefix")
        box.prop(self, "base_prefix")

        box = layout.box()
        box.label(text="安全设置")
        box.prop(self, "safety_master_switch")
        
        col = box.column()
        col.enabled = self.safety_master_switch
        col.prop(self, "confirm_delete_selected")
        col.prop(self, "confirm_delete_all")
        col.prop(self, "confirm_reset")
