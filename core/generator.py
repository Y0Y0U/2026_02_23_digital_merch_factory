from __future__ import annotations

import math
import os

import bpy
import mathutils

from . import naming
from . import materials


def _move_obj_to_collection(obj, target_coll):
    for coll in list(obj.users_collection):
        try:
            coll.objects.unlink(obj)
        except Exception:
            continue
    target_coll.objects.link(obj)


def _ensure_object_mode(context):
    try:
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass


def _import_svg(context, svg_path: str):
    old_objs = set(context.scene.objects)
    bpy.ops.import_curve.svg(filepath=svg_path)
    new_objs = [obj for obj in (set(context.scene.objects) - old_objs) if obj and obj.name in context.scene.objects]
    if not new_objs:
        return None

    _ensure_object_mode(context)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in new_objs:
        obj.select_set(True)
        context.view_layer.objects.active = obj

    if len(new_objs) > 1:
        bpy.ops.object.join()
        return context.active_object
    return new_objs[0]


def _convert_to_mesh(context, obj):
    _ensure_object_mode(context)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return context.active_object


def _apply_scale(context, obj):
    _ensure_object_mode(context)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def _align_origin(obj, mode: str):
    if mode not in {"LEFT", "CENTER"}:
        return
    if not obj or not getattr(obj, "data", None):
        return
    bbox = [mathutils.Vector(corner) for corner in obj.bound_box]
    min_x = min(v.x for v in bbox)
    max_x = max(v.x for v in bbox)
    min_y = min(v.y for v in bbox)
    if mode == "CENTER":
        offset = mathutils.Vector((-(min_x + max_x) / 2.0, -min_y, 0.0))
    else:
        offset = mathutils.Vector((-min_x, -min_y, 0.0))
    obj.data.transform(mathutils.Matrix.Translation(offset))


def _extrude_thickness(context, obj, thickness: float, use_modifier: bool):
    thickness = max(0.0, float(thickness))
    if thickness <= 0.0:
        return

    _ensure_object_mode(context)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj

    if use_modifier:
        solidify = obj.modifiers.new(name="Solidify", type="SOLIDIFY")
        solidify.thickness = thickness
        solidify.offset = 0.0
        try:
            solidify.solidify_mode = "NON_MANIFOLD"
        except Exception:
            pass
        return

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.extrude_region_move(
        MESH_OT_extrude_region={"use_normal_flip": False, "mirror": False},
        TRANSFORM_OT_translate={"value": (0, 0, thickness), "orient_type": "GLOBAL"},
    )
    bpy.ops.transform.translate(value=(0, 0, -thickness / 2.0))
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def _add_bevel(obj, bevel_depth: float, enabled: bool):
    if not enabled:
        return
    bevel_depth = max(0.0, float(bevel_depth))
    if bevel_depth <= 0.0:
        return

    bevel = obj.modifiers.new(name="Bevel", type="BEVEL")
    bevel.width = bevel_depth
    bevel.segments = 4
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = math.radians(30)


def _create_socket(context, parent_obj, width: float, height: float, thickness: float):
    _ensure_object_mode(context)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    socket_obj = context.active_object
    socket_obj.name = f"插脚控制器_{parent_obj.name}"

    socket_obj.scale = (float(width), float(height), float(thickness))
    _apply_scale(context, socket_obj)

    socket_obj.parent = parent_obj
    socket_obj.location = (0.0, -float(height) / 2.0, 0.0)
    socket_obj.display_type = "WIRE"
    socket_obj.hide_render = True

    mod = parent_obj.modifiers.new(name="Socket_Union", type="BOOLEAN")
    mod.operation = "UNION"
    mod.object = socket_obj
    try:
        mod.solver = "EXACT"
    except Exception:
        pass

    return socket_obj


def _create_base(context, parent_obj, socket_obj, length: float, width: float, thickness: float):
    _ensure_object_mode(context)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    base_obj = context.active_object
    base_obj.name = f"底板_{parent_obj.name}"
    
    # 使底板与主体垂直：
    # 父级最终会绕X轴旋转90度，因此：
    # Local X (最终 Global X) = 宽度 (width)
    # Local Y (最终 Global Z) = 厚度 (thickness)
    # Local Z (最终 Global -Y) = 长度 (length)
    base_obj.scale = (float(width), float(thickness), float(length))
    _apply_scale(context, base_obj)
    
    base_obj.parent = parent_obj
    # 位置：使底板顶面与主体底面(Y=0)齐平
    base_obj.location = (0.0, -float(thickness) / 2.0, 0.0)

    mod = base_obj.modifiers.new(name="Socket_Diff", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = socket_obj
    try:
        mod.solver = "EXACT"
    except Exception:
        pass

    return base_obj


def create_model(context, svg_path: str, tex_path: str, name_pure: str, index: int, batch_coll):
    props = context.scene.acrylic_props

    model_coll_name_raw = naming.NamingManager.get_model_collection_name(index, name_pure, context=context)
    model_coll_name = naming.get_unique_collection_name(model_coll_name_raw)
    model_coll = bpy.data.collections.new(model_coll_name)
    batch_coll.children.link(model_coll)

    root = None
    _ensure_object_mode(context)
    bpy.ops.object.empty_add(type="SPHERE", location=(0, 0, 0))
    root = context.active_object
    root.name = f"{name_pure}_控制器"
    root.show_name = True
    root.show_in_front = True
    _move_obj_to_collection(root, model_coll)

    svg_obj = _import_svg(context, svg_path)
    if not svg_obj:
        raise RuntimeError("SVG 导入失败")
    _move_obj_to_collection(svg_obj, model_coll)

    svg_obj = _convert_to_mesh(context, svg_obj)

    _ensure_object_mode(context)
    bpy.ops.object.select_all(action="DESELECT")
    svg_obj.select_set(True)
    context.view_layer.objects.active = svg_obj
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    _align_origin(svg_obj, getattr(props, "origin_mode", "LEFT"))

    scale = float(getattr(props, "model_scale", 1.0))
    root.scale = (scale, scale, scale)

    thickness = float(getattr(props, "thickness", 0.03))
    _extrude_thickness(context, svg_obj, thickness, bool(getattr(props, "use_modifier_extrusion", False)))

    _add_bevel(svg_obj, float(getattr(props, "bevel_depth", 0.0)), bool(getattr(props, "use_auto_bevel", False)))

    try:
        bpy.ops.object.shade_auto_smooth(angle=math.radians(89))
    except Exception:
        pass

    if getattr(props, "material_to_assign", None):
        if not svg_obj.data.materials:
            svg_obj.data.materials.append(props.material_to_assign)
        else:
            svg_obj.data.materials[0] = props.material_to_assign
    else:
        mat = materials.get_or_create_acrylic_material(context)
        if not svg_obj.data.materials:
            svg_obj.data.materials.append(mat)

    svg_obj.parent = root
    svg_obj.location = (0.0, 0.0, 0.0)

    socket_obj = None
    if bool(getattr(props, "create_socket", True)):
        socket_obj = _create_socket(
            context,
            svg_obj,
            float(getattr(props, "socket_width", 0.2)),
            float(getattr(props, "socket_height", 0.1)),
            thickness,
        )
        _move_obj_to_collection(socket_obj, model_coll)

    if socket_obj and bool(getattr(props, "create_base", True)):
        base_obj = _create_base(
            context,
            svg_obj,
            socket_obj,
            float(getattr(props, "base_length", 0.3)),
            float(getattr(props, "base_width", 0.5)),
            thickness,
        )
        _move_obj_to_collection(base_obj, model_coll)

    if bool(getattr(props, "lock_non_controllers", False)):
        try:
            for o in list(model_coll.objects):
                if o is root or o is socket_obj:
                    continue
                o.hide_select = True
        except Exception:
            pass

    if bool(getattr(props, "use_3d_cursor", False)):
        root.location = context.scene.cursor.location.copy()

    if bool(getattr(props, "auto_stand_up", False)):
        root.rotation_euler.x = math.radians(90)

    return model_coll
