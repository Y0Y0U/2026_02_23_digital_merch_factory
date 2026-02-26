import bpy  # Blender 主 API
import os  # 文件路径处理
import time  # 时间戳
import shutil  # 文件清理
from bpy_extras.io_utils import ImportHelper  # 文件选择器辅助
from ..utils import system  # 工具检测与命令执行
from ..utils import blender_utils  # UI 与路径辅助
from ..core import image_processing  # 图片处理
from ..core import generator  # 模型生成
from ..core import naming  # 命名与集合工具
from ..core import materials  # 材质生成

class ACRYLIC_OT_ProcessImage(bpy.types.Operator, ImportHelper):
    """选择图片并自动生成立牌"""
    bl_idname = "acrylic.process_image"  # 操作符 ID
    bl_label = "选择图片"  # UI 显示名称
    bl_options = {'REGISTER', 'UNDO'}  # 支持撤销

    # 文件过滤器：仅显示图片文件
    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;*.jpeg;*.bmp",  # 允许的图片格式
        options={'HIDDEN'},  # 隐藏该字段
    )
    
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)  # 多选文件列表
    directory: bpy.props.StringProperty(subtype='DIR_PATH')  # 目录路径

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        props = context.scene.acrylic_props  # 读取参数
        
        # 检查外部工具是否齐全
        missing = system.check_tools_exist()  # 检查外部工具
        if missing:
            self.report({'ERROR'}, f"缺失工具: {', '.join(missing)}")  # 提示缺失
            return {'CANCELLED'}

        props.is_processing = True  # 标记处理中
        
        # 收集待处理文件列表（支持多选/单选/目录）
        files = []  # 待处理文件列表
        if self.files:
            dirname = os.path.dirname(self.filepath) if self.filepath else self.directory  # 获取目录
            for f in self.files:
                files.append(os.path.join(dirname, f.name))  # 拼接完整路径
        else:
            if self.filepath and os.path.isdir(self.filepath):
                files = [
                    os.path.join(self.filepath, f)
                    for f in os.listdir(self.filepath)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
                ]
            else:
                files = [self.filepath]  # 单文件选择
             
        if not files:
            props.is_processing = False  # 还原状态
            return {'CANCELLED'}
            
        # 创建本次批次集合（用于归类本次生成的所有对象）
        timestamp = time.strftime("%Y%m%d_%H%M%S")  # 生成时间戳
        batch_name_raw = naming.NamingManager.get_batch_collection_name(timestamp)  # 批次名
        batch_name = naming.get_unique_collection_name(batch_name_raw)  # 防止同名冲突
        batch_coll = naming.ensure_collection(context, batch_name)  # 获取/创建集合
        try:
            if batch_coll.name in context.view_layer.layer_collection.children:
                context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[batch_coll.name]
        except Exception:
            pass
        
        total = len(files)  # 文件总数
        success_count = 0  # 成功计数
        
        # 记录本次批次信息，供“再次生成”复用
        props.last_batch_collection_name = batch_name  # 记录批次集合名
        if len(files) == 1:
            props.last_image_path = files[0]  # 记录最后图片路径
        
        for i, f in enumerate(files):
            if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):  # 过滤非图片
                continue
                
            props.status_text = f"正在处理 [{i+1}/{total}]: {os.path.basename(f)}"  # 状态提示
            blender_utils.update_ui(context, props.status_text)  # 刷新 UI
            
            try:
                props.last_image_path = f
                # 1) 图片处理（生成 SVG + 贴图）
                result = image_processing.process_image(context, f)  # 图片处理
                if not result:
                    print(f"Skipping {f}")  # 跳过无结果
                    continue
                    
                name_pure, svg_path, tex_path = result  # 解包处理结果
                
                # 2) 建模（导入 SVG/贴图并生成厚度、插脚、底板等）
                generator.create_model(context, svg_path, tex_path, name_pure, i+1, batch_coll)  # 生成模型
                success_count += 1  # 成功计数 +1
                
            except Exception as e:
                self.report({'ERROR'}, f"处理 {os.path.basename(f)} 失败: {str(e)}")  # UI 报错
                print(f"Error processing {f}: {e}")  # 控制台日志
                import traceback
                traceback.print_exc()  # 输出详细堆栈
                if total == 1:
                    blender_utils.show_error_popup(context, str(e))
        
        # 清理临时目录（避免残留中间文件）
        blender_utils.clean_temp_folder(blender_utils.get_temp_dir())  # 清理临时目录
        
        props.is_processing = False  # 还原处理中状态
        props.status_text = "就绪"  # 重置状态文本
        
        if success_count > 0:
            naming.NamingManager.increment_batch_sequence()  # 成功后递增批次序号
            self.report({'INFO'}, f"成功生成 {success_count} 个立牌")  # 成功提示
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "未生成任何模型")  # 失败提示
            return {'CANCELLED'}

class ACRYLIC_OT_DeleteSelected(bpy.types.Operator):
    """删除选中的立牌模型"""
    bl_idname = "acrylic.delete_selected"  # 操作符 ID
    bl_label = "删除选中立牌"  # UI 显示名称
    bl_options = {'REGISTER', 'UNDO'}  # 支持撤销
    
    def execute(self, context):
        obj = context.active_object  # 当前激活对象
        if not obj:
            self.report({'WARNING'}, "未选择物体")  # 未选中提示
            return {'CANCELLED'}
        
        target_coll = None  # 目标集合
        # 优先查找直接关联的集合
        try:
            for coll in obj.users_collection:  # 遍历对象所属集合
                if naming.NamingManager.is_script_generated_collection(coll.name):  # 判断是否脚本集合
                    target_coll = coll
                    break
        except Exception:
            pass  # 安全兜底
        
        if not target_coll:
            self.report({'WARNING'}, "选中的物体不属于脚本生成的立牌集合")  # 非脚本对象提示
            return {'CANCELLED'}
            
        # 删除集合中的所有物体
        for o in list(target_coll.objects):  # 遍历集合对象
            bpy.data.objects.remove(o, do_unlink=True)  # 删除对象
            
        # 删除集合本身
        coll_name = target_coll.name
        bpy.data.collections.remove(target_coll)  # 删除集合
        
        self.report({'INFO'}, f"已删除立牌: {coll_name}")  # 成功提示
        return {'FINISHED'}

class ACRYLIC_OT_DeleteAllGenerated(bpy.types.Operator):
    """删除所有由脚本生成的文件夹内的所有模型"""
    bl_idname = "acrylic.delete_all_generated"  # 操作符 ID
    bl_label = "删除所有脚本模型"  # UI 显示名称
    bl_options = {'REGISTER', 'UNDO'}  # 支持撤销
    
    def execute(self, context):
        colls_to_delete = []  # 待删除集合列表
        for coll in bpy.data.collections:  # 遍历所有集合
            if naming.NamingManager.is_script_generated_collection(coll.name):  # 脚本集合判定
                colls_to_delete.append(coll)
                
        if not colls_to_delete:
            self.report({'INFO'}, "未找到可删除的模型")  # 未找到提示
            return {'CANCELLED'}
            
        count = len(colls_to_delete)  # 待删除集合数量
        
        for coll in colls_to_delete:
            for obj in list(coll.objects):  # 删除集合内对象
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(coll)  # 删除集合
            
        self.report({'INFO'}, f"已删除 {count} 个集合")  # 成功提示
        return {'FINISHED'}

class ACRYLIC_OT_ReconstructLast(bpy.types.Operator):
    """根据上次处理的图像重新生成模型"""
    bl_idname = "acrylic.reconstruct_last"  # 操作符 ID
    bl_label = "再次生成"  # UI 显示名称
    bl_options = {'REGISTER', 'UNDO'}  # 支持撤销
    
    def execute(self, context):
        props = context.scene.acrylic_props  # 读取参数
        last_path = props.last_image_path  # 上次图片路径
        
        if not last_path or not os.path.exists(last_path):
            self.report({'WARNING'}, "未找到上次处理的图片记录")  # 未找到提示
            return {'CANCELLED'}
            
        # 检查外部工具是否齐全
        missing = system.check_tools_exist()  # 检查工具
        if missing:
            self.report({'ERROR'}, f"缺失工具: {', '.join(missing)}")  # 缺失提示
            return {'CANCELLED'}
            
        props.is_processing = True  # 处理中标记
        props.status_text = "正在重新生成..."  # 状态提示
        
        try:
            batch_coll = None  # 批次集合初始化
            if props.last_batch_collection_name and props.last_batch_collection_name in bpy.data.collections:
                batch_coll = bpy.data.collections[props.last_batch_collection_name]  # 复用上次批次
            else:
                timestamp = time.strftime("%Y%m%d_%H%M%S")  # 新时间戳
                batch_name = naming.NamingManager.get_batch_collection_name(timestamp)  # 新批次名
                batch_coll = naming.ensure_collection(context, batch_name)  # 创建集合
                props.last_batch_collection_name = batch_name  # 记录批次名
            
            name_pure = os.path.splitext(os.path.basename(last_path))[0]
            assets_dir = blender_utils.get_assets_dir()
            svg_path = os.path.join(assets_dir, f"{name_pure}.svg")
            tex_path = os.path.join(assets_dir, f"{name_pure}_tex_72dpi.png")

            if os.path.exists(svg_path) and os.path.exists(tex_path):
                props.status_text = "检测到现有素材，正在快速生成..."
                blender_utils.update_ui(context, props.status_text)
                generator.create_model(context, svg_path, tex_path, name_pure, 1, batch_coll)
                self.report({'INFO'}, "快速生成完成")
            else:
                props.status_text = "素材缺失，正在重新处理图片..."
                blender_utils.update_ui(context, props.status_text)
                result = image_processing.process_image(context, last_path)
                if result:
                    name_pure, svg_path, tex_path = result
                    generator.create_model(context, svg_path, tex_path, name_pure, 1, batch_coll)
                    self.report({'INFO'}, "重新生成完成")
                else:
                    self.report({'ERROR'}, "生成失败")
                
        except Exception as e:
            self.report({'ERROR'}, f"错误: {e}")  # UI 报错
            print(f"Reconstruct error: {e}")  # 控制台日志
            import traceback
            traceback.print_exc()  # 输出堆栈
            blender_utils.show_error_popup(context, str(e))
            
        props.is_processing = False  # 处理完成
        props.status_text = "就绪"  # 状态复位
        return {'FINISHED'}

class ACRYLIC_OT_ResetToDefaults(bpy.types.Operator):
    """恢复参数到默认数值（不影响开关）"""
    bl_idname = "acrylic.reset_to_defaults"
    bl_label = "恢复默认数值"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.acrylic_props
        
        # 核心参数
        props.model_scale = 1.0
        props.thickness = 0.03
        
        # 高级参数
        props.offset_px = 15
        props.smoothing_px = 10
        props.threshold = 60
        
        # 倒角
        props.bevel_depth = 0.0005
        
        # 插脚
        props.socket_width = 0.2
        props.socket_height = 0.1
        
        # 底板
        props.base_width = 0.5
        props.base_length = 0.3
        props.base_round_radius = 0.002
        
        # 原点位置
        props.origin_mode = 'CENTER'
        
        self.report({'INFO'}, "参数已恢复默认值")
        return {'FINISHED'}

class ACRYLIC_OT_CreateDefaultAcrylicMaterial(bpy.types.Operator):
    bl_idname = "acrylic.create_default_acrylic_material"  # 操作符 ID
    bl_label = "新建默认亚克力材质"  # UI 显示名称
    
    def execute(self, context):
        materials.get_or_create_acrylic_material(context)  # 创建/获取材质
        self.report({'INFO'}, "已创建默认材质")  # 成功提示
        return {'FINISHED'}

class ACRYLIC_OT_CreateDefaultRainbowMaterial(bpy.types.Operator):
    bl_idname = "acrylic.create_default_rainbow_material"  # 操作符 ID
    bl_label = "新建默认彩窗材质"  # UI 显示名称
    
    def execute(self, context):
        props = context.scene.acrylic_props
        materials.get_or_create_rainbow_material(context, colorful=props.use_rainbow_colorful)  # 创建/获取材质
        self.report({'INFO'}, "已创建彩窗材质")  # 成功提示
        return {'FINISHED'}

class ACRYLIC_OT_CreateRainbowFromSelection(bpy.types.Operator):
    """从选中模型生成彩窗并绑定到原模型"""
    bl_idname = "acrylic.create_rainbow_from_selection"  # 操作符 ID
    bl_label = "从选中模型生成彩窗"  # UI 显示名称
    bl_options = {'REGISTER', 'UNDO'}  # 支持撤销
    
    def execute(self, context):
        props = context.scene.acrylic_props  # 读取参数
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')  # 切回对象模式
        
        selected = [obj for obj in context.selected_objects if obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}]  # 可用对象
        if not selected:
            self.report({'WARNING'}, "未选中可用模型")  # 未选中提示
            return {'CANCELLED'}
        
        created = []  # 新建彩窗对象列表
        for source_obj in selected:
            bpy.ops.object.select_all(action='DESELECT')  # 清空选择
            source_obj.select_set(True)  # 选中源对象
            context.view_layer.objects.active = source_obj  # 设为活动对象
            
            bpy.ops.object.duplicate()  # 复制对象
            rainbow_obj = context.active_object  # 获取复制对象
            rainbow_obj.name = naming.NamingManager.get_rainbow_obj_name(source_obj.name)  # 彩窗命名
            
            bpy.ops.object.convert(target='MESH')  # 转为网格
            
            bpy.ops.object.mode_set(mode='EDIT')  # 进入编辑模式
            import bmesh
            bm = bmesh.from_edit_mesh(rainbow_obj.data)  # 获取 bmesh
            bm.faces.ensure_lookup_table()  # 确保面索引可用
            
            # 仅保留近似“正面”的面，删除其他面，得到薄片彩窗效果
            faces_to_delete = [f for f in bm.faces if f.normal.z > -0.9]  # 过滤背面
            if faces_to_delete:
                bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')  # 删除背面
            bmesh.update_edit_mesh(rainbow_obj.data)  # 更新网格
            
            bpy.ops.mesh.select_all(action='SELECT')  # 全选
            bpy.ops.mesh.delete_loose()  # 删除松散元素
            bpy.ops.object.mode_set(mode='OBJECT')  # 回到对象模式
            
            rainbow_obj.location.z += 0.001  # 轻微抬高避免重叠闪烁
            
            rainbow_obj.data.materials.clear()  # 清空材质
            mat = props.rainbow_material or materials.get_or_create_rainbow_material(context, colorful=props.use_rainbow_colorful)  # 选择彩窗材质
            rainbow_obj.data.materials.append(mat)  # 赋材质
            
            # 集合整理：放回源对象所在集合，便于层级管理
            for coll in rainbow_obj.users_collection:  # 从原集合解绑
                coll.objects.unlink(rainbow_obj)
            if source_obj.users_collection:
                source_obj.users_collection[0].objects.link(rainbow_obj)  # 绑定到源对象集合
            else:
                context.scene.collection.objects.link(rainbow_obj)  # 绑定到场景集合
            
            # 建立父子关系：彩窗跟随源对象
            bpy.ops.object.select_all(action='DESELECT')  # 清空选择
            rainbow_obj.select_set(True)  # 选中彩窗
            source_obj.select_set(True)  # 选中源对象
            context.view_layer.objects.active = source_obj  # 设源对象为活动
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)  # 建立父子关系
            
            created.append(rainbow_obj)  # 记录新对象
        
        bpy.ops.object.select_all(action='DESELECT')  # 清空选择
        for obj in created:
            obj.select_set(True)  # 选中新建对象
        if created:
            context.view_layer.objects.active = created[-1]  # 设最后一个为活动
        
        self.report({'INFO'}, f"已生成彩窗: {len(created)}")  # 成功提示
        return {'FINISHED'}
