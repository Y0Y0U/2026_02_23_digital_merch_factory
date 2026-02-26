import bpy
from ..properties import AcrylicProperties

class ACRYLIC_PT_MainPanel(bpy.types.Panel):
    """
    侧边栏 (N-Panel) 主面板 - 状态与核心操作
    """
    bl_label = "赛博谷子工厂"
    bl_idname = "ACRYLIC_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '立牌生成器'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        
        # --- 顶部状态监视器 ---
        box = layout.box()
        box.scale_y = 1.2
        
        if props.is_processing:
            row = box.row()
            row.label(text=props.status_text, icon="SORTTIME")
        elif (not props.tools_valid) and props.missing_tools:
            box.alert = True
            box.label(text="⚠️ 错误：未找到必要工具", icon='ERROR')
            box.label(text=f"缺失: {props.missing_tools}")
            return
        else:
            row = box.row()
            row.alignment = 'CENTER'
            row.label(text="Acrylic Figure Automation")

        layout.separator()

         # --- 按钮区 ---
        if props.is_processing:
            layout.label(text="脚本正在运行，请勿操作...", icon='INFO')
        else:
            col_btn = layout.column(align=True)
            col_btn.scale_y = 1.2
            col_btn.operator("acrylic.process_image", icon='FILE_NEW', text="选择图片开始制作")
            
            layout.label(text="快速模型调整")
            
            # 第一行：功能开关
            row_opts = layout.row(align=True)
            row_opts.scale_y = 1.2
            row_opts.prop(props, "auto_stand_up", toggle=True)
            row_opts.prop(props, "lock_non_controllers", toggle=True, icon="LOCKED" if props.lock_non_controllers else "UNLOCKED")
            row_opts.prop(props, "sync_image", toggle=True, icon="FILE_IMAGE", text="同步导入")
            
            # 第二行：位置设置
            row_cursor = layout.row(align=True)
            row_cursor.scale_y = 1.2
            row_cursor.prop(props, "use_3d_cursor", toggle=True, icon="CURSOR")
            
            layout.label(text="原点位置")
            row_origin = layout.row(align=True)
            row_origin.scale_y = 1.2
            row_origin.prop(props, "origin_mode", expand=True)


class ACRYLIC_PT_ImageSettings(bpy.types.Panel):
    bl_label = "图像预处理"
    bl_idname = "ACRYLIC_PT_image_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '立牌生成器'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        layout.enabled = not props.is_processing
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.prop(props, "offset_px")
        col.prop(props, "smoothing_px")
        col.prop(props, "threshold")


class ACRYLIC_PT_GeometrySettings(bpy.types.Panel):
    bl_label = "3D 建模设置"
    bl_idname = "ACRYLIC_PT_geometry_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '立牌生成器'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        layout.enabled = not props.is_processing
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.prop(props, "model_scale")
        col.prop(props, "thickness")
        col.prop(props, "use_modifier_extrusion")
        
        # 倒角
        row_bevel = col.row(align=True)
        row_bevel.prop(props, "use_auto_bevel")
        
        sub_col = col.column(align=True)
        sub_col.active = props.use_auto_bevel
        sub_col.prop(props, "bevel_depth")


class ACRYLIC_PT_MaterialSettings(bpy.types.Panel):
    bl_label = "材质设置"
    bl_idname = "ACRYLIC_PT_material_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '立牌生成器'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        layout.enabled = not props.is_processing
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.prop(props, "material_to_assign")
        col.operator("acrylic.create_default_acrylic_material", text="新建默认亚克力材质", icon='SHADING_RENDERED')


class ACRYLIC_PT_BaseSettings(bpy.types.Panel):
    bl_label = "底板与插脚"
    bl_idname = "ACRYLIC_PT_base_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '立牌生成器'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        layout.enabled = not props.is_processing
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        
        # 插脚
        col.label(text="插脚设置", icon='SNAP_FACE')
        col.prop(props, "create_socket")
        
        col_sock_group = col.column(align=True)
        col_sock_group.active = props.create_socket
        col_sock_group.prop(props, "socket_width")
        col_sock_group.prop(props, "socket_height")
        
        col.separator()
        
        # 底板
        col.label(text="底板设置", icon='MESH_CUBE')
        col.prop(props, "create_base")
        
        col_base_group = col.column(align=True)
        col_base_group.active = props.create_base
        col_base_group.prop(props, "base_length")
        col_base_group.prop(props, "base_width")
        col_base_group.prop(props, "base_use_round_corner")
        
        col_round = col_base_group.column(align=True)
        col_round.active = props.base_use_round_corner
        col_round.prop(props, "base_round_radius")
        
        col_base_group.separator()
        col_base_group.prop(props, "base_use_separate_material")
        
        col_mat = col_base_group.column(align=True)
        col_mat.active = props.base_use_separate_material
        col_mat.prop(props, "base_material")


class ACRYLIC_PT_RainbowSettings(bpy.types.Panel):
    bl_label = "彩窗效果"
    bl_idname = "ACRYLIC_PT_rainbow_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '立牌生成器'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        layout.enabled = not props.is_processing
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.prop(props, "rainbow_material")
        col.prop(props, "use_rainbow_colorful")
        col.operator("acrylic.create_default_rainbow_material", text="新建默认彩窗材质", icon='SHADING_RENDERED')
        col.operator("acrylic.create_rainbow_from_selection", text="从选中模型生成彩窗", icon='LIGHT')


class ACRYLIC_PT_Management(bpy.types.Panel):
    bl_label = "模型管理"
    bl_idname = "ACRYLIC_PT_management"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '立牌生成器'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        
        if not props.is_processing:
            col = layout.column(align=True)
            col.operator("acrylic.reconstruct_last", text="再次生成", icon='FILE_REFRESH')
            col.separator()
            
            row_d = col.row(align=True)
            row_d.operator("acrylic.delete_selected", text="删除选中", icon='TRASH')
            row_d.operator("acrylic.delete_all_generated", text="删除所有", icon='X')
            
            col.separator()
            col.operator("acrylic.reset_to_defaults", text="恢复默认数值", icon='LOOP_BACK')
