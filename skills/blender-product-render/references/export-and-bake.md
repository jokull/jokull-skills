# Baking procedural materials and exporting GLB / USDZ

Read this when a scripted `.blend` has to ship as a runtime asset: `three.js` / `model-viewer` on
the web (GLB), or SceneKit / RealityKit / Quick Look in an app (USDZ).

## The core problem

glTF and USD both describe materials as **textures plus PBR scalars**. A procedural material —
object-space noise driving bump, roughness and albedo — has no texture to export, so it silently
degrades to a flat grey plastic. The fix is to bake it to images and rebuild a plain Principled
BSDF from those images.

## Bake procedure

Baking needs UVs. Meshes built with `from_pydata` or bmesh have none, so project them first:

```python
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.004)   # 66°
bpy.ops.object.mode_set(mode="OBJECT")
```

Then bake albedo, roughness and a tangent-space normal. These passes are deterministic (no lighting
is involved), so 16 samples is plenty and CPU is fine:

```python
scene.render.engine = "CYCLES"
scene.cycles.device, scene.cycles.samples = "CPU", 16
scene.render.bake.margin, scene.render.bake.use_clear = 8, True

for name, bake_type, colorspace, pass_filter in (
    ("albedo",    "DIFFUSE",   "sRGB",      {"COLOR"}),   # COLOR only — no lighting
    ("roughness", "ROUGHNESS", "Non-Color", None),
    ("normal",    "NORMAL",    "Non-Color", None),
):
    image = bpy.data.images.new(f"bake_{name}", 2048, 2048, alpha=False, float_buffer=False)
    image.colorspace_settings.name = colorspace
    node = material.node_tree.nodes.new("ShaderNodeTexImage")   # bake target = ACTIVE node
    node.image, node.select = image, True
    material.node_tree.nodes.active = node
    kwargs = {"type": bake_type} | ({"pass_filter": pass_filter} if pass_filter else {})
    if bpy.ops.object.bake(**kwargs) != {"FINISHED"}:
        sys.exit(f"BAKE FAILED: {name}")
    image.filepath_raw, image.file_format = f"out/{name}.png", "PNG"
    image.save()
```

Rules that matter:

- The bake target is whichever Image Texture node is **active** in the material — set `.active`, not
  just `.select`, and do it per pass.
- `pass_filter={"COLOR"}` on the DIFFUSE bake, or the light gets baked into the albedo.
- Colour spaces: albedo `sRGB`, roughness and normal `Non-Color`. Getting this wrong yields a washed
  or crunchy asset that looks "almost right", which is the hardest kind of bug to spot.
- Rebuild the export material from scratch (`ShaderNodeBsdfPrincipled` + three `TexImage` nodes +
  `NormalMap`), assign it, and drop the procedural one. Set `IOR` to match the real material
  (~1.46 for PBT plastic, 1.5 for glass).

## Keep fine detail as geometry, not texture

Text, logos and legends baked into a 2048 map go soft the moment anyone zooms. If they exist as real
geometry (a conformed decal, a shrinkwrapped surface), **keep them as geometry** with a simple
material. It is resolution-independent and usually cheaper than the texture budget it replaces.

The catch is depth precision. Shrinkwrap offsets tuned for a Cycles still (~7.5 µm) z-fight badly in
WebGL. Raise them to ~40 µm before export:

```python
for modifier in decal.modifiers:
    if modifier.type == "SHRINKWRAP":
        modifier.offset = 0.0048          # scene units; ~40 µm at this scale
```

Semi-transparent detail (a dye diffusion fringe, a soft shadow decal) needs the blend mode set
across Blender versions, whose material API changed:

```python
if hasattr(mat, "surface_render_method"):   # 4.2+
    mat.surface_render_method = "BLENDED"
if hasattr(mat, "blend_method"):            # legacy
    mat.blend_method = "BLEND"
```

## GLB export

```python
bpy.ops.object.select_all(action="DESELECT")
for o in (mesh, decal, fringe):
    o.hide_set(False); o.hide_render = False; o.select_set(True)
bpy.context.view_layer.objects.active = mesh

bpy.ops.export_scene.gltf(
    filepath=GLB, export_format="GLB",
    use_selection=True,      # never export the studio lights and backdrop
    export_apply=True,       # apply modifiers — the bevel/shrinkwrap IS the shape
    export_yup=True,
    export_image_format="AUTO",
)
```

Hidden objects are skipped even when selected, so unhide explicitly. Log the byte size after export
and watch it: a web hero has a budget, and a silent jump to 12 MB means a texture setting regressed.

For a web asset, add compression once the geometry is settled:

```python
    export_draco_mesh_compression_enable=True,   # 60–90% smaller geometry
    export_draco_mesh_compression_level=6,
    export_image_format="JPEG", export_jpeg_quality=85,   # AUTO keeps PNG — big
```

Draco is not free: the viewer must load a decoder (`DRACOLoader` + the decoder files in three.js,
`model-viewer` handles it natively). If the consumer is a small hero with a couple of thousand
triangles, skip it — you would ship a 200 KB decoder to save 40 KB. JPEG textures kill alpha, so
keep any texture with meaningful transparency as PNG.

Budgets worth holding a web asset to: **< 1 MB** ideal and < 5 MB tolerable, **< 50k triangles**,
textures at **1024²** (2048² only when the asset is the page's subject), first render under ~2 s on
an average connection. A product hero that misses these is usually carrying baked maps at a
resolution nobody sees at its on-screen size.

### Pre-export hygiene

Run before either exporter, in this order: apply/enable the modifiers you want baked into the shape,
merge doubles, confirm every material is a Principled BSDF (custom node groups do not survive — they
export flat), then `bpy.ops.outliner.orphans_purge(do_recursive=True)` to drop orphaned meshes and
images the script created along the way. Purging is what stops a script that iterates on materials
from shipping every discarded bake inside the GLB.

Two failure modes that look like export bugs but are not:

- **Textures vanish.** Packed images or relative paths. Save images externally and load by absolute
  path, or pack deliberately with `bpy.ops.file.pack_all()` and let the exporter embed them.
- **Animation missing.** glTF exports timeline actions; NLA strips are ignored unless baked. Push
  the action to the timeline or bake it before exporting, and set `export_animations=True`.

## USDZ export

Same baked scene, different writer. SceneKit supplies its own camera and lighting, so ship geometry
and materials only, and downscale textures — a small in-app hero does not need the web GLB's 2048 maps.

```python
bpy.ops.wm.usd_export(
    filepath=USDZ,
    selected_objects_only=True,
    export_animation=False,
    export_materials=True,
    generate_preview_surface=True,       # USDPreviewSurface — required for SceneKit
    convert_orientation=True,
    export_global_forward_selection="NEGATIVE_Z",
    export_global_up_selection="Y",
    export_textures_mode="NEW",
    overwrite_textures=True,
    root_prim_path="/Keycap",
    usdz_downscale_size="512",           # ~0.75 MB asset instead of ~4 MB
)
```

## Sharing setup between two exporters

Two export scripts that both open the blend, bake and rebuild materials will drift apart. Do not
copy-paste, and do not turn the first script into a module just for this. Execute the first script
*up to* its export call:

```python
src = open(SRC).read()
head = src[: src.index("bpy.ops.export_scene.gltf(")]
exec(compile(head, SRC, "exec"), {"__name__": "export_head", "__file__": SRC})
# scene is now baked, materials rebuilt, the right objects selected
bpy.ops.wm.usd_export(...)
```

Blunt, but honest about the dependency: the second script cannot diverge from the first, and the
split point is a single visible string. If a third consumer appears, that is the moment to factor a
real shared module.

## Verify before shipping

- Byte size of each output, printed by the script.
- Render the *baked* material once in Blender and compare against the procedural original — bakes
  regress quietly.
- Load the GLB in a viewer and the USDZ in Quick Look. Look for: flat grey (materials lost), sparkly
  z-fighting on decals (raise offsets), inside-out normals (`export_yup` / orientation flags), and
  legends gone soft (bake resolution or geometry accidentally flattened).
