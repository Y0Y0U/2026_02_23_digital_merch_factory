# UI Optimization Plan

## Goal
Transform the current "Cyber Goods Factory" add-on UI into a professional, native-feeling Blender interface. The focus is on improved categorization, visual hierarchy, and user-friendly interaction flows, adhering to Blender's official UI guidelines.

## 1. Architectural Restructuring (Sub-panels)
Instead of a single monolithic panel with manual boolean toggles for folding, we will adopt Blender's native Sub-panel system (`bl_parent_id`). This allows for:
- Native drag-and-drop reordering.
- Better performance.
- Consistent look and feel with other Blender modifiers and tools.

### Panel Hierarchy
- **`ACRYLIC_PT_MainPanel`** (Parent)
    - **Header**: Status indicator & Main "Start" Action.
    - **Global Settings**: Quick toggles (Lock, Cursor, Sync).
- **`ACRYLIC_PT_Image`** (Child)
    - *Label*: "Image Processing" (Icon: `IMAGE_DATA`)
    - *Content*: Offset, Smoothing, Threshold.
- **`ACRYLIC_PT_Geometry`** (Child)
    - *Label*: "Geometry" (Icon: `MESH_CUBE`)
    - *Content*: Scale, Thickness, Modifiers, Bevel.
- **`ACRYLIC_PT_Materials`** (Child)
    - *Label*: "Materials" (Icon: `MATERIAL`)
    - *Content*: Material assignment, Create Default Material.
- **`ACRYLIC_PT_Base`** (Child)
    - *Label*: "Base & Stand" (Icon: `OUTLINER_OB_POINTCLOUD`)
    - *Content*: Socket settings, Base dimensions, Round corners.
- **`ACRYLIC_PT_Rainbow`** (Child)
    - *Label*: "Effects (Rainbow)" (Icon: `LIGHT`)
    - *Content*: Rainbow material, Colorful mode, Generate from selection.
- **`ACRYLIC_PT_Manage`** (Child)
    - *Label*: "Management" (Icon: `PREFERENCES`)
    - *Content*: Reconstruct, Delete options, Reset defaults.

## 2. Visual & Interaction Polish
- **Standard Layout**: Enforce `layout.use_property_split = True` across all panels for clean "Label | Value" alignment.
- **Contextual Feedback**:
    - Disable setting panels when `is_processing` is True.
    - Show dynamic icons for toggle buttons (e.g., "Play" vs "Pause").
- **Grouping**: Use `layout.box()` *within* sub-panels only for distinct logical groups (e.g., separating "Socket" from "Base" inside the Base panel).
- **Icons**: Use semantic icons for every operator and header.

## 3. New Features & Improvements
- **Preset System (Proposed)**: Add a simple EnumProperty for "Quality Presets" (e.g., "Draft (Fast)", "High Quality (Smooth)", "Custom").
    - *Draft*: Low smoothing, no bevel.
    - *High Quality*: High smoothing, auto-bevel enabled.
- **Help Section**: A footer panel with a link to documentation or a "Quick Tip" label.

## 4. Implementation Checklist
- [ ] **Refactor `ui/panels.py`**:
    - Create the base `ACRYLIC_Panel_Base` class (mixin) to share context logic.
    - Implement the 7 panel classes defined above.
- [ ] **Update `__init__.py`**:
    - Update registration list to include all new panel classes.
- [ ] **Clean up `properties.py`**:
    - Remove the now obsolete manual folding booleans (`show_image_settings`, etc.).
- [ ] **Verify**:
    - Check "N-Panel" rendering.
    - Test "Process Image" flow with new UI.

## 5. Draft Preview (Mental Model)
```
[ Cyber Goods Factory ]       (Main Panel)
   [ Status: Idle ]
   [ (ICON) Process Image ]   (Big Button)
   [ Quick Settings ]         (Row)

> [ Image Processing ]        (Sub-panel, Collapsed)
> [ Geometry ]                (Sub-panel, Expanded)
     Scale      : 1.0
     Thickness  : 0.03
     ...
> [ Base & Stand ]            (Sub-panel, Expanded)
     ...
> [ Management ]              (Sub-panel, Collapsed)
```
