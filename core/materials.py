from __future__ import annotations

import bpy


def get_or_create_acrylic_material(context, name: str = "默认亚克力"):
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    glass = nodes.new(type="ShaderNodeBsdfGlass")
    glass.location = (0, 0)
    out = nodes.new(type="ShaderNodeOutputMaterial")
    out.location = (300, 0)
    links.new(glass.outputs["BSDF"], out.inputs["Surface"])
    return mat


def get_or_create_rainbow_material(context, colorful: bool = False, name: str = "默认彩窗"):
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    tex_coord = nodes.new(type="ShaderNodeTexCoord")
    tex_coord.location = (-800, 0)
    mapping = nodes.new(type="ShaderNodeMapping")
    mapping.location = (-600, 0)
    sep_xyz = nodes.new(type="ShaderNodeSeparateXYZ")
    sep_xyz.location = (-400, 0)
    ramp = nodes.new(type="ShaderNodeValToRGB")
    ramp.location = (-200, 0)
    ramp.color_ramp.interpolation = "LINEAR"

    if colorful:
        ramp.color_ramp.elements[0].color = (1, 0, 0, 1)
        ramp.color_ramp.elements[1].color = (0.5, 0, 1, 1)
        ramp.color_ramp.elements.new(0.2).color = (1, 1, 0, 1)
        ramp.color_ramp.elements.new(0.4).color = (0, 1, 0, 1)
        ramp.color_ramp.elements.new(0.6).color = (0, 1, 1, 1)
        ramp.color_ramp.elements.new(0.8).color = (0, 0, 1, 1)
    else:
        ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        ramp.color_ramp.elements[1].color = (1, 1, 1, 1)

    glass = nodes.new(type="ShaderNodeBsdfGlass")
    glass.location = (100, 0)
    out = nodes.new(type="ShaderNodeOutputMaterial")
    out.location = (300, 0)

    links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], sep_xyz.inputs["Vector"])
    links.new(sep_xyz.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], glass.inputs["Color"])
    links.new(glass.outputs["BSDF"], out.inputs["Surface"])
    return mat

