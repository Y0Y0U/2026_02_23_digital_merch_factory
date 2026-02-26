import bpy
import os
import subprocess
import shutil
import math
import mathutils
import xml.etree.ElementTree as ET
from bpy_extras.io_utils import ImportHelper

import time

# =================================================================
# 亚克力立牌自动化脚本 v7.1
# [填写数据]：工具路径配置
# =================================================================
TOOLS_DIR = r"C:/Users/Lenovo/Desktop/Acrylic Figure automation script_by yyu/new_tast/tools"
OUTPUT_DIR = r"C:/Users/Lenovo/Desktop/Acrylic Figure automation script_by yyu/new_tast/output"
TEMP_DIR = r"C:/Users/Lenovo/Desktop/Acrylic Figure automation script_by yyu/new_tast/temp"

# 新增：压缩素材保存路径 (与工程文件同级)
# 注意：在 Blender 脚本中，os.getcwd() 不一定是 blend 文件所在目录，
# 最稳妥的方式是基于当前 blend 文件的路径。
# 如果 blend 文件未保存，bpy.data.filepath 为空，此时退回到当前脚本目录或桌面。
def get_assets_dir():
    if bpy.data.filepath:
        base_dir = os.path.dirname(bpy.data.filepath)
    else:
        # 如果文件未保存，尝试使用脚本所在目录 (new_tast)
        # 这里硬编码了当前工作目录，或者我们可以假设脚本运行时 cwd 是正确的
        base_dir = r"C:/Users/Lenovo/Desktop/Acrylic Figure automation script_by yyu/new_tast"
    
    return os.path.join(base_dir, "(勿删)赛博谷子工厂压缩素材")

# --- 修正系数 ---
# 由于我们现在统一了 DPI 和分辨率，理论上 Scale 应该是 1.0
#但是明显这没有用，按照Gemini的猜测修正系数是8.333
ALIGN_SCALE = 8.034


def clean_temp_folder():
    """
    作用：清理临时文件夹 (TEMP_DIR)，但不清理素材文件夹
    数据：遍历 TEMP_DIR 删除所有文件
    """
    if os.path.exists(TEMP_DIR):
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"清理临时文件失败: {e}")

def update_ui(context, message):
    """
    作用：强制刷新 Blender UI，防止脚本运行时界面假死
    数据：写入 status_text 并调用 redraw_timer
    """
    props = context.scene.acrylic_props
    props.status_text = message
    # 强制重绘所有窗口，让用户看到文字变化
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

def show_error_popup(context, message):
    def draw(self, _context):
        self.layout.label(text=message)
    context.window_manager.popup_menu(draw, title="脚本运行错误", icon='ERROR')

def get_unique_collection_name(base_name):
    """生成唯一的集合名称，避免冲突"""
    if base_name not in bpy.data.collections:
        return base_name
    
    # 如果已存在，尝试添加数字后缀
    counter = 1
    while True:
        new_name = f"{base_name}_{counter:02d}"
        if new_name not in bpy.data.collections:
            return new_name
        counter += 1

def ensure_collection(context, name):
    """确保集合存在并返回"""
    # 这里不再直接查找，而是每次都生成一个新的唯一集合（如果是批量任务的根集合）
    # 但由于这个函数也用于获取子集合，我们需要区分逻辑
    # 简单起见，我们假设外部调用者负责处理命名唯一性
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    else:
        new_coll = bpy.data.collections.new(name)
        context.scene.collection.children.link(new_coll)
        return new_coll

def set_origin_to_bounds_min(context, obj):
    cursor_loc = context.scene.cursor.location.copy()
    try:
        corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
        min_x = min(c.x for c in corners)
        min_y = min(c.y for c in corners)
        min_z = min(c.z for c in corners)
        context.scene.cursor.location = (min_x, min_y, min_z)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    finally:
        context.scene.cursor.location = cursor_loc

def create_socket_helper(context, parent_obj, thickness_mm, width_mm=20.0, height_mm=10.0):
    """
    功能：为立牌创建辅助插口（Boolean Union），允许用户实时调整
    参数：
      - parent_obj: 亚克力立牌主体对象
      - thickness_mm: 板材厚度（决定插口厚度）
      - width_mm: 插口初始宽度
      - height_mm: 插口初始高度
    """
    # 1. 计算尺寸（米）
    thickness_m = thickness_mm / 1000.0
    width_m = width_mm / 1000.0
    height_m = height_mm / 1000.0
    
    # 2. 创建立方体网格
    bpy.ops.mesh.primitive_cube_add(size=1.0) # 创建单位立方体
    socket_obj = context.active_object
    
    # 3. 命名规范：插口辅助体_原名
    socket_obj.name = f"插口辅助_{parent_obj.name}"
    
    # 4. 设置尺寸和初始位置
    # 策略重构：
    # 1. 先调整立方体到目标尺寸
    # 2. 应用缩放 (Apply Scale)，将尺寸固化到网格顶点，Scale重置为1
    # 3. 定位
    # 4. 使用 keep_transform=True 建立父子关系，确保视觉不变
    
    # 因为初始 size=1.0，所以直接设置 scale 等于目标尺寸即可
    socket_obj.scale = (width_m, height_m, thickness_m)
    
    # 应用缩放，避免后续继承父级缩放产生复杂问题
    # 注意：Apply Scale 需要对象在 Object Mode 且被选中
    if context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # 定位：移动到立牌底部中心
    # 使用世界坐标定位最直观
    world_loc = parent_obj.matrix_world.translation.copy()
    
    # 此时 socket_obj 的原点在几何中心
    # 我们希望它在立牌底部往下伸出
    # 假设立牌原点在底部中心 (Z=0 relative to geometry bottom)
    
    # 先移动到和立牌原点重合
    socket_obj.location = world_loc
    
    # 再进行微调
    # 注意：这里我们是在世界坐标系下移动，假设立牌是竖直放置的
    # 如果立牌被旋转了，直接修改 location.y/z 可能不对
    # 但通常立牌生成是标准方向。为了保险，我们可以使用局部移动，但在建立父子关系前比较麻烦。
    # 鉴于目前需求，我们先按标准方向处理：
    # Y轴是高度方向（对于2D形状），Z轴是厚度？
    # 不，通常 Blender 中 Z 是向上，Y 是深度/厚度？或者 SVG 导入是平的？
    # 根据之前的逻辑：thickness 对应 Z，height 对应 Y。
    # 这意味着立牌是躺着的？或者立牌是竖着的但厚度在Z？
    # 之前的代码：socket_obj.location.z = ... + thickness/2
    # 让我们保持之前的轴向逻辑，假设它是对的。
    
    socket_obj.location.y -= height_m / 2.0 # 向下伸出
    
    # 修正 Z 轴位置：
    # 确保插口与模型厚度完全一致且居中，不进行任何 Z 轴偏移
    # socket_obj.location.z = 0 
    
    # 5. 建立父子关系 (关键：Keep Transform)
    bpy.ops.object.select_all(action='DESELECT')
    socket_obj.select_set(True)
    parent_obj.select_set(True)
    context.view_layer.objects.active = parent_obj # 父级作为活动对象
    
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
    
    # 6. 视觉设置：线框模式 + 渲染隐藏
    socket_obj.display_type = 'WIRE'
    socket_obj.hide_render = True
    
    # 7. 移动到同一集合
    for coll in socket_obj.users_collection:
        coll.objects.unlink(socket_obj)
    # 获取父级所在的集合
    parent_coll = parent_obj.users_collection[0]
    parent_coll.objects.link(socket_obj)
    
    # 8. 添加布尔修改器 (Union)
    # 检查是否已存在同名修改器
    mod_name = "Socket_Union"
    if context.view_layer.objects.active != parent_obj:
        context.view_layer.objects.active = parent_obj
        
    if mod_name in parent_obj.modifiers:
        parent_obj.modifiers.remove(parent_obj.modifiers[mod_name])
        
    mod = parent_obj.modifiers.new(name=mod_name, type='BOOLEAN')
    if mod:
        mod.operation = 'UNION'
        mod.object = socket_obj
        # 根据用户需求，强制使用 'EXACT' (准确) 求解器
        # 这通常比 FAST 慢，但在复杂几何体上更稳定
        try:
            mod.solver = 'EXACT'
        except Exception as e:
            print(f"设置布尔求解器为 EXACT 失败: {e}")
    else:
        print(f"警告: 无法为 {parent_obj.name} 创建布尔修改器") 
    
    # 9. 最后选中插口辅助体，方便用户直接调整
    bpy.ops.object.select_all(action='DESELECT')
    socket_obj.select_set(True)
    context.view_layer.objects.active = socket_obj

def parse_svg_viewbox(svg_path):
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
    except Exception:
        return None
    view_box = root.attrib.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) >= 4:
            try:
                return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
            except Exception:
                return None
    width = root.attrib.get("width")
    height = root.attrib.get("height")
    if width and height:
        def parse_num(value):
            num = "".join(ch for ch in value if (ch.isdigit() or ch in ".-+"))
            try:
                return float(num)
            except Exception:
                return None
        w = parse_num(width)
        h = parse_num(height)
        if w is not None and h is not None:
            return 0.0, 0.0, w, h
    return None

def set_origin_to_local_point(context, obj, local_point):
    cursor_loc = context.scene.cursor.location.copy()
    try:
        world_point = obj.matrix_world @ mathutils.Vector(local_point)
        context.scene.cursor.location = world_point
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    finally:
        context.scene.cursor.location = cursor_loc

def set_origin_to_svg_canvas(context, obj, svg_path):
    vb = parse_svg_viewbox(svg_path)
    if vb:
        min_x, min_y, _w, _h = vb
    else:
        min_x, min_y = 0.0, 0.0
    set_origin_to_local_point(context, obj, (min_x, min_y, 0.0))

class ACRYLIC_OT_CreateDefaultAcrylicMaterial(bpy.types.Operator):
    """创建默认亚克力材质 (Glass BSDF)"""
    bl_idname = "acrylic.create_default_acrylic_material"
    bl_label = "新建默认亚克力材质"
    
    def execute(self, context):
        mat_name = "默认亚克力"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        # 节点
        glass = nodes.new(type='ShaderNodeBsdfGlass')
        glass.location = (0, 0)
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
        # 链接
        links.new(glass.outputs['BSDF'], output.inputs['Surface'])
        
        # 设置到属性
        context.scene.acrylic_props.material_to_assign = mat
        
        self.report({'INFO'}, f"已创建材质: {mat_name}")
        return {'FINISHED'}

class ACRYLIC_OT_CreateDefaultRainbowMaterial(bpy.types.Operator):
    """创建默认彩窗材质 (TexCoord -> Mapping -> SepXYZ -> Ramp -> Glass)"""
    bl_idname = "acrylic.create_default_rainbow_material"
    bl_label = "新建默认彩窗材质"
    
    def execute(self, context):
        mat_name = "默认彩窗"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        # 节点
        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        tex_coord.location = (-800, 0)
        
        mapping = nodes.new(type='ShaderNodeMapping')
        mapping.location = (-600, 0)
        
        sep_xyz = nodes.new(type='ShaderNodeSeparateXYZ')
        sep_xyz.location = (-400, 0)
        
        ramp = nodes.new(type='ShaderNodeValToRGB')
        ramp.location = (-200, 0)
        # 添加彩虹渐变
        ramp.color_ramp.interpolation = 'LINEAR'
        
        if context.scene.acrylic_props.use_rainbow_colorful:
            # 默认为黑白。根据"彩虹"的含义使其多彩
            # 起点 (0.0): 红色
            ramp.color_ramp.elements[0].color = (1, 0, 0, 1)
            # 终点 (1.0): 紫色
            ramp.color_ramp.elements[1].color = (0.5, 0, 1, 1)
            # 中间节点
            ramp.color_ramp.elements.new(0.2).color = (1, 1, 0, 1) # 黄色
            ramp.color_ramp.elements.new(0.4).color = (0, 1, 0, 1) # 绿色
            ramp.color_ramp.elements.new(0.6).color = (0, 1, 1, 1) # 青色
            ramp.color_ramp.elements.new(0.8).color = (0, 0, 1, 1) # 蓝色
        else:
            # 保持默认黑白渐变
            ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
            ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        
        glass = nodes.new(type='ShaderNodeBsdfGlass')
        glass.location = (100, 0)
        
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
        # 链接
        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        links.new(mapping.outputs['Vector'], sep_xyz.inputs['Vector'])
        links.new(sep_xyz.outputs['Z'], ramp.inputs['Fac'])
        links.new(ramp.outputs['Color'], glass.inputs['Color'])
        links.new(glass.outputs['BSDF'], output.inputs['Surface'])
        
        # 设置到属性
        context.scene.acrylic_props.rainbow_material = mat
        
        self.report({'INFO'}, f"已创建材质: {mat_name}")
        return {'FINISHED'}

class ACRYLIC_OT_CreateRainbowFromSelection(bpy.types.Operator):
    """从选中模型生成彩窗并绑定到原模型"""
    bl_idname = "acrylic.create_rainbow_from_selection"
    bl_label = "从选中模型生成彩窗"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.acrylic_props
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        selected = [obj for obj in context.selected_objects if obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}]
        if not selected:
            self.report({'WARNING'}, "未选中可用模型")
            return {'CANCELLED'}
        
        created = []
        for source_obj in selected:
            bpy.ops.object.select_all(action='DESELECT')
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            bpy.ops.object.duplicate()
            rainbow_obj = context.active_object
            rainbow_obj.name = f"彩窗_{source_obj.name}"
            
            bpy.ops.object.convert(target='MESH')
            
            bpy.ops.object.mode_set(mode='EDIT')
            import bmesh
            bm = bmesh.from_edit_mesh(rainbow_obj.data)
            bm.faces.ensure_lookup_table()
            
            faces_to_delete = [f for f in bm.faces if f.normal.z > -0.9]
            if faces_to_delete:
                bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
            bmesh.update_edit_mesh(rainbow_obj.data)
            
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.delete_loose()
            bpy.ops.object.mode_set(mode='OBJECT')
            
            rainbow_obj.location.z += 0.001
            
            rainbow_obj.data.materials.clear()
            if props.rainbow_material:
                rainbow_obj.data.materials.append(props.rainbow_material)
            
            for coll in rainbow_obj.users_collection:
                coll.objects.unlink(rainbow_obj)
            if source_obj.users_collection:
                source_obj.users_collection[0].objects.link(rainbow_obj)
            else:
                context.scene.collection.objects.link(rainbow_obj)
            
            bpy.ops.object.select_all(action='DESELECT')
            rainbow_obj.select_set(True)
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
            
            created.append(rainbow_obj)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in created:
            obj.select_set(True)
        context.view_layer.objects.active = created[-1]
        
        self.report({'INFO'}, f"已生成彩窗: {len(created)}")
        return {'FINISHED'}

class NamingManager:
    """集中管理命名逻辑"""
    @staticmethod
    def get_batch_collection_name(timestamp):
        return f"立牌批次_{timestamp}"

    @staticmethod
    def get_model_collection_name(index, name_pure):
        return f"亚克力_{index:02d}_{name_pure}"

    @staticmethod
    def get_svg_obj_name(index, name_pure):
        return f"亚克力_{index:02d}_{name_pure}"

    @staticmethod
    def get_plane_obj_name(index, name_pure):
        return f"图案_{index:02d}_{name_pure}"

    @staticmethod
    def is_script_generated_collection(collection_name):
        return collection_name.startswith("亚克力_") or collection_name.startswith("立牌批次_")

    @staticmethod
    def parse_name_from_collection(collection_name):
        # 假设格式: 亚克力_{index}_{name}
        if not collection_name.startswith("亚克力_"):
            return None, None
        
        parts = collection_name.split('_', 2)
        if len(parts) < 3:
            return None, None
            
        try:
            index = int(parts[1])
            name_pure = parts[2]
            return index, name_pure
        except ValueError:
            return None, None

def create_base_helper(context, parent_obj, socket_obj, props):
    """
    生成底座并同步插口 (使用修改器堆栈实现，支持实时调整)
    """
    # 1. 基础尺寸
    w = props.base_width / 1000.0
    l = props.base_length / 1000.0
    # h = props.thickness_mm / 1000.0 # 将由 Solidify 驱动
    
    # 2. 新建平面 (XY平面)
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    base_obj = context.active_object
    base_obj.name = f"底座_{parent_obj.name}"
    
    # 应用尺寸 (平面只有宽和长)
    base_obj.scale = (w, l, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # 3. 添加倒角修改器 (Bevel - Vertices)
    # 即使当前不启用圆角，也加上修改器但隐藏，或者让驱动器控制
    mod_bevel = base_obj.modifiers.new(name="Base_Bevel", type='BEVEL')
    mod_bevel.affect = 'VERTICES' # 只倒角顶点 -> 平面圆角
    mod_bevel.segments = 16
    mod_bevel.use_clamp_overlap = True # 防止圆角过大破面
    
    # 驱动圆角半径
    # d = mod_bevel.driver_add("width")
    # var = d.driver.variables.new()
    # var.name = "radius"
    # var.type = 'SINGLE_PROP'
    # var.targets[0].id_type = 'SCENE'
    # var.targets[0].id = context.scene
    # var.targets[0].data_path = "acrylic_props.base_round_radius"
    # d.driver.expression = "radius / 1000.0"
    
    # 不再使用驱动器，而是直接设置初始值
    mod_bevel.width = props.base_round_radius / 1000.0
    
    # 驱动是否启用圆角 (控制修改器可见性)
    # d_vis = mod_bevel.driver_add("show_viewport")
    # var_vis = d_vis.driver.variables.new()
    # var_vis.name = "use_round"
    # var_vis.type = 'SINGLE_PROP'
    # var_vis.targets[0].id_type = 'SCENE'
    # var_vis.targets[0].id = context.scene
    # var_vis.targets[0].data_path = "acrylic_props.base_use_round_corner"
    # d_vis.driver.expression = "use_round"
    
    # 不再使用驱动器，而是直接设置初始值
    mod_bevel.show_viewport = props.base_use_round_corner
    
    # 渲染可见性也驱动一下
    # d_vis_r = mod_bevel.driver_add("show_render")
    # var_vis_r = d_vis_r.driver.variables.new()
    # var_vis_r.name = "use_round"
    # var_vis_r.type = 'SINGLE_PROP'
    # var_vis_r.targets[0].id_type = 'SCENE'
    # var_vis_r.targets[0].id = context.scene
    # var_vis_r.targets[0].data_path = "acrylic_props.base_use_round_corner"
    # d_vis_r.driver.expression = "use_round"
    
    # 不再使用驱动器，而是直接设置初始值
    mod_bevel.show_render = props.base_use_round_corner

    # 4. 添加实体化修改器 (Solidify) -> 挤出厚度
    mod_solid = base_obj.modifiers.new(name="Base_Solidify", type='SOLIDIFY')
    mod_solid.offset = 0 # 居中
    
    # 驱动厚度
    # d_thick = mod_solid.driver_add("thickness")
    # var_thick = d_thick.driver.variables.new()
    # var_thick.name = "thick"
    # var_thick.type = 'SINGLE_PROP'
    # var_thick.targets[0].id_type = 'SCENE'
    # var_thick.targets[0].id = context.scene
    # var_thick.targets[0].data_path = "acrylic_props.thickness_mm"
    # d_thick.driver.expression = "thick / 1000.0"
    
    # 不再使用驱动器，而是直接设置初始值
    mod_solid.thickness = props.thickness_mm / 1000.0

    # 5. 建立层级 (Parent to Figure)
    base_obj.parent = parent_obj
    
    # 6. 初始位置与旋转
    # 不再强制设置位置，而是通过约束+偏移来控制
    # base_obj.matrix_world.translation = socket_obj.matrix_world.translation
    # 确保本地位置归零，以便 Copy Location 的 Offset 正常工作
    base_obj.location = (0, 0, 0)
    
    # 旋转 90 度 (相对于父级)
    base_obj.rotation_euler.x = math.radians(90)
    
    # 7. 添加约束 (Copy Location)
    const = base_obj.constraints.new(type='COPY_LOCATION')
    const.target = socket_obj
    const.owner_space = 'LOCAL'
    const.target_space = 'LOCAL'
    const.use_x = True
    const.use_y = True
    const.use_z = True
    # 开启偏移，以便通过 Driver 调整 Y 轴位置实现底部对齐
    const.use_offset = True
    
    # 驱动 Y 轴位置，使底座底部与插口底部对齐
    # 逻辑：
    # Socket 高度 H (Local Y)
    # Base 厚度 T (Local Z -> Parent Y)
    # 我们希望 Bottom_Base = Bottom_Socket
    # Socket Bottom = Center - H/2
    # Base Bottom = Center - T/2
    # Base Center = Socket Center + (T - H) / 2
    
    d_loc = base_obj.driver_add("location", 1) # Index 1 is Y
    
    # 变量：插口高度 H
    var_h = d_loc.driver.variables.new()
    var_h.name = "h"
    var_h.type = 'SINGLE_PROP'
    var_h.targets[0].id = socket_obj
    var_h.targets[0].data_path = "dimensions[1]" # Y dimension
    
    # 变量：底座厚度 T
    var_t = d_loc.driver.variables.new()
    var_t.name = "t"
    var_t.type = 'SINGLE_PROP'
    var_t.targets[0].id_type = 'SCENE'
    var_t.targets[0].id = context.scene
    var_t.targets[0].data_path = "acrylic_props.thickness_mm"
    
    d_loc.driver.expression = "(t/1000 - h) / 2"
    
    # 8. 布尔挖孔 (最后一步)
    mod_bool = base_obj.modifiers.new(name="Socket_Diff", type='BOOLEAN')
    mod_bool.operation = 'DIFFERENCE'
    mod_bool.object = socket_obj
    mod_bool.solver = 'EXACT'
    
    # 9. 整理集合
    for coll in base_obj.users_collection:
        coll.objects.unlink(base_obj)
    parent_obj.users_collection[0].objects.link(base_obj)
    
    # 10. 材质应用
    # 逻辑：
    # 如果开启了独立材质且指定了材质，则使用指定的 base_material
    # 否则，尝试从 parent_obj (立牌本体) 获取材质
    
    mat_to_assign = None
    
    if props.base_use_separate_material:
        if props.base_material:
            mat_to_assign = props.base_material
    else:
        # 直接使用全局设置的立牌材质，不做其他尝试
        if props.material_to_assign:
            mat_to_assign = props.material_to_assign

    if mat_to_assign:
        # 检查是否已存在
        if not base_obj.data.materials:
            base_obj.data.materials.append(mat_to_assign)
        else:
            base_obj.data.materials[0] = mat_to_assign

    return base_obj

def create_single_acrylic_model(context, svg_path, tex_path, name_pure, index, parent_collection):
    """
    生成单个亚克力模型的核心逻辑
    """
    props = context.scene.acrylic_props
    
    # 1. 创建子集合
    new_obj_name = NamingManager.get_svg_obj_name(index, name_pure)
    target_coll_name = get_unique_collection_name(NamingManager.get_model_collection_name(index, name_pure))
    
    target_coll = bpy.data.collections.new(target_coll_name)
    parent_collection.children.link(target_coll)
    
    # --- 0. 确定生成位置 ---
    if props.use_3d_cursor:
        cursor_base = context.scene.cursor.location.copy()
    else:
        cursor_base = mathutils.Vector((0, 0, 0))
        
    base_x = cursor_base.x + (index - 1) * 0.2
    base_y = cursor_base.y
    base_z = cursor_base.z
    
    # --- 1. 创建整体控制器 (Root Empty) ---
    bpy.ops.object.empty_add(type='SPHERE', location=(base_x, base_y, base_z))
    root_obj = context.active_object
    root_obj.name = f"{name_pure}_控制器"
    
    # 动态调整控制器大小 (约为目标高度的 5%)
    # 假设 target_height_mm 默认 100mm -> 0.1m
    # 之前是 0.5m (太大了). 用户希望缩小 90% -> 0.05m
    # 如果 target_height_mm 是 0 (不缩放)，则使用默认值 0.05
    ref_height = props.target_height_mm if props.target_height_mm > 0 else 100.0
    root_obj.empty_display_size = (ref_height / 100.0) * 0.05
    
    root_obj.show_name = True
    root_obj.show_in_front = True
    root_obj.color = (1, 0.8, 0, 1) # 亮黄色
    # 移动到目标集合
    for coll in root_obj.users_collection:
        coll.objects.unlink(root_obj)
    target_coll.objects.link(root_obj)
    
    svg_obj = None
    
    # --- 2. 处理 SVG 模型 ---
    if os.path.exists(svg_path):
        old_objs = set(context.scene.objects)
        old_colls = set(bpy.data.collections)
        
        bpy.ops.import_curve.svg(filepath=svg_path)
        
        new_objs = set(context.scene.objects) - old_objs
        new_colls = set(bpy.data.collections) - old_colls
        
        # 清理临时集合
        for coll in new_colls:
            bpy.data.collections.remove(coll)

        if new_objs:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in new_objs:
                if obj.name not in context.scene.objects:
                    context.scene.collection.objects.link(obj)
                obj.select_set(True)
                context.view_layer.objects.active = obj
                
                # 移动到目标集合
                for coll in obj.users_collection:
                    coll.objects.unlink(obj)
                target_coll.objects.link(obj)
            
            if len(new_objs) > 1:
                bpy.ops.object.join()
            
            svg_obj = context.active_object
            svg_obj.name = new_obj_name

            # 转网格并清理
            bpy.ops.object.convert(target='MESH')
            svg_obj = context.active_object
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0008, use_unselected=True)
            bpy.ops.mesh.tris_convert_to_quads()
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')

            svg_obj.data.materials.clear()
            set_origin_to_svg_canvas(context, svg_obj, svg_path)
    
    if svg_obj:
        # --- 3. 处理贴图 ---
        import_tex_path = os.path.abspath(tex_path)
        tex_file_name = os.path.basename(import_tex_path)
        tex_dir = os.path.dirname(import_tex_path)
        
        old_colls_img = set(bpy.data.collections)
        
        bpy.ops.image.import_as_mesh_planes(
            filepath=import_tex_path,
            files=[{"name": tex_file_name}],
            directory=tex_dir,
            align_axis='+Z'
        )
        
        new_colls_img = set(bpy.data.collections) - old_colls_img
        for coll in new_colls_img:
             bpy.data.collections.remove(coll)

        plane = context.active_object
        
        # 修复材质路径
        if plane and plane.data.materials:
            for mat in plane.data.materials:
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            node.image.filepath = import_tex_path
                            try:
                                node.image.reload()
                            except Exception as e:
                                print(f"Warning: Failed to reload image: {e}")
        
        # 移动到集合
        for coll in plane.users_collection:
            coll.objects.unlink(plane)
        target_coll.objects.link(plane)
        
        plane.name = NamingManager.get_plane_obj_name(index, name_pure)

        set_origin_to_bounds_min(context, plane)
        
        # --- 4. 对齐和定位 ---
        # 此时 svg_obj 和 plane 都在原点附近或 SVG 坐标
        # 我们先对齐它们到 (0,0,0) (相对于 Root)
        
        # 移动到 Root 位置
        plane.location = root_obj.location
        svg_obj.location = root_obj.location
        
        # --- 5. 统一缩放 ---
        base_scale = 1.0
        if props.target_height_mm > 0:
            current_h = plane.dimensions.y
            if current_h > 0:
                target_h_m = props.target_height_mm / 1000.0
                base_scale = target_h_m / current_h
        
        plane.scale = (base_scale, base_scale, base_scale)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        
        final_svg_scale = base_scale * ALIGN_SCALE
        svg_obj.scale = (final_svg_scale, final_svg_scale, final_svg_scale)
        
        bpy.ops.object.select_all(action='DESELECT')
        svg_obj.select_set(True)
        context.view_layer.objects.active = svg_obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # --- 5.1 居中对齐逻辑 (新增) ---
        if props.origin_mode == 'CENTER':
            # 获取 SVG 的边界框（此时 Scale 已 Apply）
            # bound_box 是局部坐标，但此时无旋转且 Scale=1
            bbox = [mathutils.Vector(corner) for corner in svg_obj.bound_box]
            min_x = min(v.x for v in bbox)
            max_x = max(v.x for v in bbox)
            min_y = min(v.y for v in bbox)
            
            center_x = (min_x + max_x) / 2
            bottom_y = min_y
            
            # 计算偏移量：将中心移到 X=0，底部移到 Y=0
            offset = mathutils.Vector((-center_x, -bottom_y, 0))
            
            # 直接移动网格数据，这样 Origin 保持不变但几何体移动了
            svg_obj.data.transform(mathutils.Matrix.Translation(offset))
            plane.data.transform(mathutils.Matrix.Translation(offset))
            
            # 更新一下依赖图，确保后续尺寸计算正确
            context.view_layer.update()

        # 再次强制对齐到 Root
        # svg_obj.location = root_obj.location
        # plane.location = root_obj.location
        
        # --- 建立父子关系 ---
        # 将 svg_obj 和 plane 设为 root_obj 的子级
        # 直接设置 parent，然后归零位置，确保它们相对于 Root 居中
        # 修复偏移问题
        plane.parent = root_obj
        plane.location = (0, 0, 0)
        
        svg_obj.parent = root_obj
        svg_obj.location = (0, 0, 0)
        
        # --- 6. 挤出逻辑 (修复厚度问题) ---
        thickness_m = props.thickness_mm / 1000.0
        
        if props.use_modifier_extrusion:
            solidify = svg_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            
            # 启用 Complex 模式 (NON_MANIFOLD) 以修复破口
            solidify.solidify_mode = 'NON_MANIFOLD'
            solidify.nonmanifold_thickness_mode = 'CONSTRAINTS'
            solidify.nonmanifold_boundary_mode = 'FLAT'
            
            solidify.thickness = thickness_m
            solidify.offset = 0.0 # 居中，确保有厚度感
            solidify.use_rim = True # 填充边缘
            solidify.use_even_offset = True # 均匀厚度
            solidify.use_quality_normals = True
        else:
            # 使用普通网格挤出 (更稳定，解决破面问题)
            context.view_layer.objects.active = svg_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            
            # 挤出
            bpy.ops.mesh.extrude_region_move(
                MESH_OT_extrude_region={"use_normal_flip":False, "mirror":False}, 
                TRANSFORM_OT_translate={"value":(0, 0, thickness_m), "orient_type":'GLOBAL'}
            )
            
            # 重算此法线
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            
            # 居中几何体 (将所有顶点下移一半厚度，保持原点在几何中心)
            bpy.ops.transform.translate(value=(0, 0, -thickness_m / 2.0))
            
            bpy.ops.object.mode_set(mode='OBJECT')

        # --- 7. 材质应用 ---
        if props.material_to_assign:
            found_slot = False
            for slot in svg_obj.material_slots:
                if slot.material == props.material_to_assign:
                    found_slot = True
                    break
            if not found_slot:
                svg_obj.data.materials.append(props.material_to_assign)
            svg_obj.active_material_index = 0
        
        # --- 8. 平滑与倒角 ---
        bpy.ops.object.shade_auto_smooth(angle=math.radians(89))
        
        if props.use_auto_bevel and props.bevel_depth_mm > 0:
            bevel = svg_obj.modifiers.new(name="Bevel", type='BEVEL')
            bevel.width = props.bevel_depth_mm / 1000.0
            bevel.segments = 4
            bevel.limit_method = 'ANGLE'
            bevel.angle_limit = math.radians(30)

        # --- 9. 插口与底座生成 ---
        if props.create_socket:
            context.view_layer.objects.active = svg_obj
            # 确保是 Mesh 才能进行顶点操作 (虽然已经是Mesh了)
            
            actual_thickness_mm = props.thickness_mm # 使用设定厚度，因为 Modifier 可能未应用
            if not props.use_modifier_extrusion:
                 actual_thickness_mm = svg_obj.dimensions.z * 1000.0
            
            # 这里的 create_socket_helper 需要返回 socket_obj
            # 我们需要修改 create_socket_helper 让他返回 socket_obj，或者在这里获取 active object
            # 为了稳妥，我们在这里调用后获取 active object
            
            create_socket_helper(context, svg_obj, actual_thickness_mm, props.socket_width_mm, props.socket_height_mm)
            socket_obj = context.active_object # create_socket_helper 最后激活了 socket_obj
            
            if props.create_base:
                base_obj = create_base_helper(context, svg_obj, socket_obj, props)
    
    # --- 10. 自动立起 ---
    if props.auto_stand_up:
        # 旋转 Root 控制器
        root_obj.rotation_euler.x = math.radians(90)
    
    # --- 11. 应用锁定逻辑 ---
    if props.lock_non_controllers:
        if svg_obj: svg_obj.hide_select = True
        if plane: plane.hide_select = True
        if 'base_obj' in locals() and base_obj: base_obj.hide_select = True
        # root_obj 和 socket_obj 保持可选

    # --- 12. 最终选中插口辅助体 ---
    # 如果生成了插口，最后选中插口辅助体，方便用户直接调整
    if socket_obj:
        bpy.ops.object.select_all(action='DESELECT')
        socket_obj.select_set(True)
        context.view_layer.objects.active = socket_obj
        
    return target_coll

def get_generated_file_paths(full_input_path):
    """
    根据输入图片路径，推断生成的中间文件路径
    """
    file_name = os.path.basename(full_input_path)
    name_pure = os.path.splitext(file_name)[0]
    ASSETS_DIR = get_assets_dir()
    
    # 将 SVG 也保存到持久化素材库，防止被误删
    svg_path = os.path.join(ASSETS_DIR, f"{name_pure}.svg")
    # 压缩素材的持久化路径
    persistent_texture_path = os.path.join(ASSETS_DIR, f"{name_pure}_tex_72dpi.png")
    
    return name_pure, svg_path, persistent_texture_path

def process_single_image_pipeline(context, full_input_path, index, total_files, batch_collection):
    """
    处理单张图片的核心流程：ImageMagick -> Potrace -> Blender Import
    """
    props = context.scene.acrylic_props
    magick_exe = os.path.join(TOOLS_DIR, "magick.exe")
    potrace_exe = os.path.join(TOOLS_DIR, "potrace.exe")
    
    # 获取标准路径
    name_pure, svg_path, persistent_texture_path = get_generated_file_paths(full_input_path)
    
    # --- 状态更新 ---
    progress_prefix = f"[{index}/{total_files}] " if total_files > 1 else ""
    update_ui(context, f"{progress_prefix}正在处理: {name_pure}...")
    
    mask_path = os.path.join(TEMP_DIR, f"{name_pure}_mask.bmp")

    # 确保临时文件夹存在
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    # --- 步骤 1: ImageMagick 处理 ---
    update_ui(context, f"{progress_prefix}正在处理图片...")
    
    # 显式定义 DPI
    TARGET_DPI = 72
    
    # 构造临时贴图路径
    temp_texture_path = os.path.join(TEMP_DIR, f"{name_pure}_tex_72dpi.png")
    
    # ImageMagick 命令
    magick_cmd = [
        magick_exe, full_input_path,
        "-resize", "x1000",
        "-density", str(TARGET_DPI),
        "-units", "PixelsPerInch",
        "+write", temp_texture_path,
        "+write", persistent_texture_path, # 写入持久化素材库
        "-alpha", "extract"
    ]

    if props.offset_px > 0:
        magick_cmd.extend(["-morphology", "Dilate", f"Disk:{props.offset_px}"])
    
    if props.smoothing_px > 0:
        magick_cmd.extend(["-blur", f"0x{props.smoothing_px}"])

    magick_cmd.extend([
        "-threshold", f"{props.threshold}%",
        "-negate", "-depth", "8",
        mask_path
    ])

    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    magick_result = subprocess.run(magick_cmd, capture_output=True, text=True, shell=False, startupinfo=startupinfo)
    if magick_result.returncode != 0:
        err_info = magick_result.stderr.strip() if magick_result.stderr else "无详细错误信息"
        raise RuntimeError(f"图片处理失败 (Exit Code {magick_result.returncode})\n详细错误: {err_info}\n命令: {magick_cmd}")

    # --- 步骤 2: Potrace 矢量化 ---
    update_ui(context, f"{progress_prefix}正在生成矢量路径...")
    potrace_cmd = [potrace_exe, mask_path, "-s", "--flat", "-o", svg_path]
    potrace_result = subprocess.run(potrace_cmd, capture_output=True, text=True, shell=False, startupinfo=startupinfo)
    if potrace_result.returncode != 0:
        err_info = potrace_result.stderr.strip() if potrace_result.stderr else "无详细错误信息"
        raise RuntimeError(f"转矢量失败 (Exit Code {potrace_result.returncode})\n详细错误: {err_info}")

    # --- 步骤 3: Blender 导入建模 ---
    update_ui(context, f"{progress_prefix}正在生成 3D 模型...")
    
    # 这里其实不需要强制拷贝了，因为 ImageMagick 已经尝试写入 persistent_texture_path
    # 但保留检查逻辑是好的
    if not os.path.exists(persistent_texture_path):
        if os.path.exists(temp_texture_path):
            print(f"警告: ImageMagick 未能直接写入 {persistent_texture_path}，尝试手动复制...")
            shutil.copy2(temp_texture_path, persistent_texture_path)
        else:
            raise RuntimeError(f"贴图生成失败，找不到文件: {persistent_texture_path}")

    # 调用核心生成函数
    create_single_acrylic_model(context, svg_path, persistent_texture_path, name_pure, index, batch_collection)

class ACRYLIC_OT_BatchProcessor(bpy.types.Operator, ImportHelper):
    """从文件管理器选择图片并开始制作"""
    bl_idname = "acrylic.batch_processor"
    bl_label = "选择并制作"
    
    # 过滤器：只允许看到图片文件
    filter_glob: bpy.props.StringProperty(default="*.png;*", options={'HIDDEN'})
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        props = context.scene.acrylic_props
        props.is_processing = True # 标记为运行状态
        
        magick_exe = os.path.join(TOOLS_DIR, "magick.exe")
        potrace_exe = os.path.join(TOOLS_DIR, "potrace.exe")
        
        ASSETS_DIR = get_assets_dir()

        # 确保路径存在
        for d in [OUTPUT_DIR, TEMP_DIR, ASSETS_DIR]:
            os.makedirs(d, exist_ok=True)

        # 1. 确定要处理的文件列表
        files = []
        if self.files:
            # 多选模式
            dirname = os.path.dirname(self.filepath) if self.filepath else self.directory
            for f in self.files:
                files.append(os.path.join(dirname, f.name))
        else:
            # 单选模式或目录模式
            if os.path.isdir(self.filepath):
                files = [os.path.join(self.filepath, f) for f in os.listdir(self.filepath) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            else:
                files = [self.filepath]
        
        total_files = len(files)
        if total_files == 0:
            self.report({'WARNING'}, "未找到图片文件")
            return {'CANCELLED'}

        # --- 创建本次任务的总集合 (带时间戳) ---
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        batch_collection_name = get_unique_collection_name(NamingManager.get_batch_collection_name(timestamp))
        batch_collection = ensure_collection(context, batch_collection_name)
        
        # 激活该集合，确保新物体（如下面的 SVG 导入产生的集合）默认关联到这里，或方便后续管理
        layer_collection = context.view_layer.layer_collection.children[batch_collection.name]
        context.view_layer.active_layer_collection = layer_collection

        try:
            # 遍历用户选中的所有文件
            for index, full_input_path in enumerate(files, start=1):
                # 检查文件扩展名
                if not full_input_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    continue
                    
                # 调用核心处理流程
                process_single_image_pipeline(context, full_input_path, index, total_files, batch_collection)
                
                # 记录最后一次处理的信息
                props.last_image_path = full_input_path
                props.last_batch_collection_name = batch_collection.name

        except Exception as e:
            error_message = f"发生错误: {str(e)}"
            self.report({'ERROR'}, error_message)
            props.status_text = error_message
            props.is_processing = False
            show_error_popup(context, error_message)
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

        # --- 收尾工作 ---
        clean_temp_folder() # 仅在结束时清理
        props.is_processing = False
        props.status_text = "Acrylic Figure automation script_by yyu" 
        self.report({'INFO'}, f"制作完成！共处理 {total_files} 张图片")
        return {'FINISHED'}

class ACRYLIC_OT_DeleteSelected(bpy.types.Operator):
    """删除选中的立牌模型"""
    bl_idname = "acrylic.delete_selected"
    bl_label = "删除选中立牌"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "未选择物体")
            return {'CANCELLED'}
        
        # 查找所属集合
        target_coll = None
        # 优先查找直接关联的集合
        try:
            for coll in obj.users_collection:
                try:
                    # 检查集合引用是否有效
                    if not coll: 
                        continue
                    if NamingManager.is_script_generated_collection(coll.name):
                        target_coll = coll
                        break
                except ReferenceError:
                    continue
        except ReferenceError:
            pass
        
        if not target_coll:
            self.report({'WARNING'}, "选中的物体不属于脚本生成的立牌集合")
            return {'CANCELLED'}
            
        # 删除集合中的所有物体
        for o in list(target_coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
            
        # 删除集合本身
        coll_name = target_coll.name
        bpy.data.collections.remove(target_coll)
        
        self.report({'INFO'}, f"已删除立牌: {coll_name}")
        return {'FINISHED'}

class ACRYLIC_OT_DeleteAllGenerated(bpy.types.Operator):
    """删除所有由脚本生成的文件夹内的所有模型（即使是用户手动的）"""
    bl_idname = "acrylic.delete_all_generated"
    bl_label = "删除所有脚本模型"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 1. 收集所有目标集合
        colls_to_delete = []
        for coll in bpy.data.collections:
            if NamingManager.is_script_generated_collection(coll.name):
                colls_to_delete.append(coll)
                
        if not colls_to_delete:
            self.report({'INFO'}, "未找到可删除的模型")
            return {'CANCELLED'}
            
        count = len(colls_to_delete)
        
        # 2. 删除
        for coll in colls_to_delete:
            # 先删除集合内的物体
            for obj in list(coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            # 再删除集合
            bpy.data.collections.remove(coll)
            
        self.report({'INFO'}, f"已删除 {count} 个集合")
        return {'FINISHED'}

class ACRYLIC_OT_ReconstructLast(bpy.types.Operator):
    """根据上次处理的图像重新生成模型（使用当前参数）"""
    bl_idname = "acrylic.reconstruct_last"
    bl_label = "再次生成"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.acrylic_props
        last_path = props.last_image_path
        
        if not last_path or not os.path.exists(last_path):
            self.report({'WARNING'}, "未找到上次处理的图片记录")
            return {'CANCELLED'}
            
        # 确定集合
        batch_collection = None
        # 优先尝试复用上次的集合
        if props.last_batch_collection_name and props.last_batch_collection_name in bpy.data.collections:
            batch_collection = bpy.data.collections[props.last_batch_collection_name]
        else:
            # 如果找不到，新建一个
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            batch_collection_name = get_unique_collection_name(NamingManager.get_batch_collection_name(timestamp))
            batch_collection = ensure_collection(context, batch_collection_name)
            # 更新记录
            props.last_batch_collection_name = batch_collection_name
        
        # 尝试激活集合
        try:
            # 注意：如果集合在深层级，直接 access children 可能找不到。
            # 这里简单尝试，如果失败也不影响功能，只是 active layer collection 不对而已
            if batch_collection.name in context.view_layer.layer_collection.children:
                layer_collection = context.view_layer.layer_collection.children[batch_collection.name]
                context.view_layer.active_layer_collection = layer_collection
        except Exception:
            pass
            
        props.is_processing = True
        try:
            # 1. 尝试查找已存在的素材
            name_pure, svg_path, tex_path = get_generated_file_paths(last_path)
            
            # [新增] 检查旧位置是否有 SVG，如果有则移动过来，防止重复生成
            old_svg_path = os.path.join(OUTPUT_DIR, f"{name_pure}.svg")
            if not os.path.exists(svg_path) and os.path.exists(old_svg_path):
                try:
                    shutil.move(old_svg_path, svg_path)
                    update_ui(context, "已迁移旧版 SVG 文件...")
                except Exception as e:
                    print(f"Migration failed: {e}")
            
            # 如果文件都存在，直接复用，跳过繁琐的图片处理流程
            if os.path.exists(svg_path) and os.path.exists(tex_path):
                update_ui(context, "检测到现有素材，正在快速生成...")
                # 直接调用建模函数
                create_single_acrylic_model(context, svg_path, tex_path, name_pure, 1, batch_collection)
                self.report({'INFO'}, f"快速生成完成: {name_pure}")
            else:
                # 2. 如果素材丢失，回退到完整流程
                update_ui(context, "素材缺失，重新处理图片...")
                # 使用 index=1，因为命名管理器会自动处理重名冲突
                process_single_image_pipeline(context, last_path, 1, 1, batch_collection)
                self.report({'INFO'}, f"已再次生成: {os.path.basename(last_path)}")
            
        except Exception as e:
            self.report({'ERROR'}, f"生成失败: {str(e)}")
            props.is_processing = False
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
            
        props.is_processing = False
        clean_temp_folder()
        return {'FINISHED'}

def update_lock_state(self, context):
    """
    更新锁定状态：除了控制器和插口辅助体外，锁定其他所有相关对象
    """
    lock = self.lock_non_controllers
    
    # 遍历场景中的所有对象
    for obj in bpy.data.objects:
        # 检查是否属于脚本生成的集合
        is_script_obj = False
        for coll in obj.users_collection:
            if NamingManager.is_script_generated_collection(coll.name):
                is_script_obj = True
                break
        
        if not is_script_obj:
            continue
            
        # 判断类型
        # 控制器: endswith("_控制器")
        # 插口辅助体: startswith("插口辅助_")
        is_controller = obj.name.endswith("_控制器")
        is_socket_helper = obj.name.startswith("插口辅助_")
        
        if is_controller or is_socket_helper:
            # 这些始终保持可选
            obj.hide_select = False
        else:
            # 其他对象根据设置锁定
            obj.hide_select = lock

# --- 插件界面与属性 ---
def update_base_round_corner(self, context):
    """更新选中物体的底座圆角状态"""
    for obj in context.selected_objects:
        # 尝试查找关联的底座
        base_obj = None
        if obj.name.startswith("底座_"):
            base_obj = obj
        else:
            # 如果选中的是立牌或控制器，尝试找其子级中的底座
            for child in obj.children:
                if child.name.startswith("底座_"):
                    base_obj = child
                    break
        
        if base_obj:
            # 找到 Base_Bevel 修改器
            mod = base_obj.modifiers.get("Base_Bevel")
            if mod:
                mod.show_viewport = self.base_use_round_corner
                mod.show_render = self.base_use_round_corner

def update_base_round_radius(self, context):
    """更新选中物体的底座圆角半径"""
    for obj in context.selected_objects:
        # 尝试查找关联的底座
        base_obj = None
        if obj.name.startswith("底座_"):
            base_obj = obj
        else:
            for child in obj.children:
                if child.name.startswith("底座_"):
                    base_obj = child
                    break
        
        if base_obj:
            mod = base_obj.modifiers.get("Base_Bevel")
            if mod:
                mod.width = self.base_round_radius / 1000.0

class AcrylicProperties(bpy.types.PropertyGroup):
    target_height_mm: bpy.props.FloatProperty(
        name="模型缩放", 
        description="0表示保持原尺寸，偏小",
        default=100.0, 
        min=0.0
    )
    thickness_mm: bpy.props.FloatProperty(
        name="厚度 (mm)", 
        description="板材厚度，默认3mm",
        default=3.0, 
        min=0.0,
        precision=2
    )
    use_modifier_extrusion: bpy.props.BoolProperty(
        name="使用修改器挤出",
        description="勾选后使用 Solidify 修改器生成厚度（非破坏性）；不勾选则直接应用挤出（普通挤出）",
        default=True
    )
    use_auto_bevel: bpy.props.BoolProperty(
        name="倒角",
        description="为边缘添加倒角效果",
        default=False
    )
    create_socket: bpy.props.BoolProperty(
        name="生成底座插口",
        description="在底部生成一个方块作为立牌的连接处",
        default=True
    )
    socket_width_mm: bpy.props.FloatProperty(
        name="插口宽度 (mm)",
        default=20.0,
        min=1.0
    )
    socket_height_mm: bpy.props.FloatProperty(
        name="插口高度 (mm)",
        default=10.0,
        min=1.0
    )
    bevel_depth_mm: bpy.props.FloatProperty(
        name="深度 (mm)", 
        description="边缘倒角大小",
        default=0.5, 
        min=0.0,
        precision=2
    )
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
    material_to_assign: bpy.props.PointerProperty(
        name="指定材质",
        type=bpy.types.Material,
        description="选择一个材质，将在生成后应用到模型侧面（SVG部分）"
    )
    
    rainbow_material: bpy.props.PointerProperty(
        name="彩窗材质",
        type=bpy.types.Material,
        description="选择应用到彩窗平面的材质"
    )
    use_rainbow_colorful: bpy.props.BoolProperty(
        name="多彩模式",
        description="勾选生成彩虹渐变，不勾选生成黑白渐变",
        default=True
    )

    sync_image: bpy.props.BoolProperty(name="同步导入图像", default=True)
    is_processing: bpy.props.BoolProperty(default=False)
    status_text: bpy.props.StringProperty(default="等待开始...")

    # --- 新增属性 ---
    last_image_path: bpy.props.StringProperty(default="")
    last_batch_collection_name: bpy.props.StringProperty(default="")

    origin_mode: bpy.props.EnumProperty(
        name="原点位置",
        description="选择生成模型的原点位置",
        items=[
            ('LEFT', "左下角 (稳定)", "保持 SVG 默认原点，最稳定"),
            ('CENTER', "底部中心 (推荐)", "自动计算并居中，可减少手动调整插口位置的操作")
        ],
        default='LEFT'
    )

    # UI 折叠状态
    show_image_settings: bpy.props.BoolProperty(name="图像预处理", default=False)
    show_geo_settings: bpy.props.BoolProperty(name="3D 建模设置", default=True)
    show_mat_settings: bpy.props.BoolProperty(name="材质设置", default=False)
    show_base_settings: bpy.props.BoolProperty(name="底座与插口", default=True)
    show_rainbow_settings: bpy.props.BoolProperty(name="彩窗效果", default=False)

    # 生成选项
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
        description="勾选后，锁定除控制器和插口辅助体以外的所有对象，防止误选",
        default=False,
        update=update_lock_state
    )

    # 底座设置
    create_base: bpy.props.BoolProperty(
        name="生成底座",
        description="生成与插口对应的底座模型",
        default=True
    )
    base_width: bpy.props.FloatProperty(
        name="底座宽度 (mm)",
        default=40.0,
        min=1.0
    )
    base_length: bpy.props.FloatProperty(
        name="底座长度 (mm)",
        default=60.0,
        min=1.0
    )
    base_use_round_corner: bpy.props.BoolProperty(
        name="底座圆角",
        default=True,
        update=update_base_round_corner
    )
    base_round_radius: bpy.props.FloatProperty(
        name="圆角半径 (mm)",
        default=2.0,
        min=0.0,
        update=update_base_round_radius
    )
    
    # 底座材质设置
    base_use_separate_material: bpy.props.BoolProperty(
        name="独立底座材质",
        description="勾选后，底座将使用单独的材质；否则默认与立牌本体材质一致",
        default=False
    )
    base_material: bpy.props.PointerProperty(
        name="底座材质",
        type=bpy.types.Material,
        description="选择应用到底座的材质"
    )

class ACRYLIC_PT_MainPanel(bpy.types.Panel):
    """在 3D 视图侧边栏 (N 面板) 创建界面"""
    bl_label = "赛博谷子工厂"
    bl_idname = "ACRYLIC_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Acrylic'

    def draw(self, context):
        layout = self.layout
        props = context.scene.acrylic_props
        
        # --- 顶部状态监视器 ---
        box = layout.box()
        box.scale_y = 1.2
        
        if props.is_processing:
            row = box.row()
            row.label(text=props.status_text, icon="SORTTIME")
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
            col_btn.operator("acrylic.batch_processor", icon='FILE_NEW', text="选择图片开始制作")
            
            row_opts = layout.row(align=True)
            # row_opts.prop(props, "use_3d_cursor", toggle=True)
            row_opts.prop(props, "auto_stand_up", toggle=True)
            row_opts.prop(props, "lock_non_controllers", toggle=True, icon="LOCKED" if props.lock_non_controllers else "UNLOCKED")
            row_opts.prop(props, "sync_image", toggle=True)
            
            row_origin = layout.row(align=True)
            row_origin.prop(props, "origin_mode", expand=True)

        layout.separator()

        # --- 参数设置区 ---
        col = layout.column(align=True)
        col.enabled = not props.is_processing 
        col.use_property_split = True # 启用左右对齐布局
        col.use_property_decorate = False # 移除属性装饰点
        
        # 1. 图像预处理
        box_img = col.box()
        row = box_img.row(align=True)
        row.prop(props, "show_image_settings", icon="TRIA_DOWN" if props.show_image_settings else "TRIA_RIGHT", emboss=False)
        if props.show_image_settings:
            box_img.prop(props, "offset_px")
            box_img.prop(props, "smoothing_px")
            box_img.prop(props, "threshold")
        
        # 2. 3D 建模设置
        box_geo = col.box()
        row = box_geo.row(align=True)
        row.prop(props, "show_geo_settings", icon="TRIA_DOWN" if props.show_geo_settings else "TRIA_RIGHT", emboss=False)
        if props.show_geo_settings:
            box_geo.prop(props, "target_height_mm")
            box_geo.prop(props, "thickness_mm")
            box_geo.prop(props, "use_modifier_extrusion")
            
            # 倒角
            row_bevel = box_geo.row(align=True)
            row_bevel.prop(props, "use_auto_bevel")
            if props.use_auto_bevel:
                 sub_col = box_geo.column(align=True)
                 sub_col.prop(props, "bevel_depth_mm")

        # 3. 材质设置
        box_mat = col.box()
        row = box_mat.row(align=True)
        row.prop(props, "show_mat_settings", icon="TRIA_DOWN" if props.show_mat_settings else "TRIA_RIGHT", emboss=False)
        if props.show_mat_settings:
            box_mat.prop(props, "material_to_assign")
            box_mat.operator("acrylic.create_default_acrylic_material", text="新建默认亚克力材质", icon='SHADING_RENDERED')

        # 4. 底座与插口设置
        box_base = col.box()
        row = box_base.row(align=True)
        row.prop(props, "show_base_settings", icon="TRIA_DOWN" if props.show_base_settings else "TRIA_RIGHT", emboss=False)
        if props.show_base_settings:
            # 插口
            box_base.label(text="插口设置", icon='SNAP_FACE')
            box_base.prop(props, "create_socket")
            if props.create_socket:
                 col_sock = box_base.column(align=True)
                 col_sock.prop(props, "socket_width_mm")
                 col_sock.prop(props, "socket_height_mm")
            
                 box_base.separator()
            
                 # 底座
                 box_base.label(text="底座设置", icon='MESH_CUBE')
                 box_base.prop(props, "create_base")
                 if props.create_base:
                     col_base = box_base.column(align=True)
                     col_base.prop(props, "base_length") # 对应 长
                     col_base.prop(props, "base_width")  # 对应 宽
                     col_base.prop(props, "base_use_round_corner")
                     if props.base_use_round_corner:
                         col_base.prop(props, "base_round_radius")
                     
                     col_base.separator()
                     col_base.prop(props, "base_use_separate_material")
                     if props.base_use_separate_material:
                         col_base.prop(props, "base_material")

        # 5. 彩窗效果
        box_rainbow = col.box()
        row = box_rainbow.row(align=True)
        row.prop(props, "show_rainbow_settings", icon="TRIA_DOWN" if props.show_rainbow_settings else "TRIA_RIGHT", emboss=False)
        if props.show_rainbow_settings:
            box_rainbow.prop(props, "rainbow_material")
            box_rainbow.prop(props, "use_rainbow_colorful")
            box_rainbow.operator("acrylic.create_default_rainbow_material", text="新建默认彩窗材质", icon='SHADING_RENDERED')
            box_rainbow.operator("acrylic.create_rainbow_from_selection", text="从选中模型生成彩窗", icon='LIGHT')

        layout.separator()

        # --- 模型管理区 ---
        if not props.is_processing:
            box_manage = layout.box()
            box_manage.label(text="模型管理", icon='OUTLINER')
            col_m = box_manage.column(align=True)
            col_m.operator("acrylic.reconstruct_last", text="再次生成", icon='FILE_REFRESH')
            col_m.separator()
            row_d = col_m.row(align=True)
            row_d.operator("acrylic.delete_selected", text="删除选中", icon='TRASH')
            row_d.operator("acrylic.delete_all_generated", text="删除所有", icon='X')
        
       
# --- 注册 ---
classes = [
    AcrylicProperties, 
    ACRYLIC_OT_BatchProcessor, 
    ACRYLIC_OT_CreateDefaultAcrylicMaterial, 
    ACRYLIC_OT_CreateDefaultRainbowMaterial, 
    ACRYLIC_OT_CreateRainbowFromSelection, 
    ACRYLIC_OT_DeleteSelected, 
    ACRYLIC_OT_DeleteAllGenerated, 
    ACRYLIC_OT_ReconstructLast, 
    ACRYLIC_PT_MainPanel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.acrylic_props = bpy.props.PointerProperty(type=AcrylicProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.acrylic_props

if __name__ == "__main__":
    register()
