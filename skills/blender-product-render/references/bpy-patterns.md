# Blender Python patterns for product scenes

Read this reference while implementing or repairing a deterministic product-scene build script.

## Entrypoint and versioning

Use a standalone script whose output names make iteration explicit:

```python
ROOT = os.path.dirname(os.path.abspath(__file__))
WAVE = "wave-3"
BLEND = os.path.join(ROOT, f"product-{WAVE}.blend")
OUT_1024 = os.path.join(ROOT, f"product-{WAVE}-1024.png")
OUT_2048 = os.path.join(ROOT, f"product-{WAVE}-2048.png")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
```

Use `read_factory_settings` only when the script owns the complete scene. Never run it while editing a user's
open scene through a bridge.

## Procedural lofts

Represent an industrial profile as data rather than repeated operators:

```python
# width, depth, corner_radius, z
profile = [
    (18.0, 18.0, 1.1, 0.0),
    (17.2, 17.2, 1.0, 3.0),
    (14.4, 14.4, 0.8, 7.8),
]
```

Generate each rounded-rectangle ring with the same vertex count, connect adjacent rings by index, then build
the mesh with `mesh.from_pydata`. Keep the profile list in the script and store critical dimensions on the
resulting object:

```python
obj["physical_width_mm"] = 18.0
obj["nominal_wall_mm"] = 1.2
obj["profile_source"] = "measured drawing; revision B"
```

## Editable masters and render derivatives

Keep an editable text or curve source, duplicate it, and convert only the duplicate:

```python
render_copy = source.copy()
render_copy.data = source.data.copy()
bpy.context.collection.objects.link(render_copy)
bpy.context.view_layer.objects.active = render_copy
render_copy.select_set(True)
bpy.ops.object.convert(target="MESH")
source.hide_render = True
```

Project flat print geometry to a compound surface with Shrinkwrap. Keep offsets microscopic and use a second,
fainter expanded copy only when evidence supports ink diffusion.

## Physical texture coordinates

For isotropic grain, use the `Object` output of `ShaderNodeTexCoord`. `Generated` coordinates normalize each
axis independently and stretch the physical grain across unequal dimensions. Name nodes by purpose and scale,
for example `0.10 mm molded grain` and `Satin valleys to polished peaks`.

Drive related effects from the same field:

```text
object coordinates → shaped grain → bump
                              └──→ mapped roughness
                              └──→ tiny neutral color variation
```

Use a much smaller amplitude for color than for normal or roughness response.

## Render targets

Render previews and masters from one scene without rebuilding it:

```python
targets = ((1024, OUT_1024), (2048, OUT_2048))
for size, path in targets:
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
```

Save the `.blend` after setting the intended default camera and render settings. Print every output path and
the selected font path to make logs auditable.

## Context-sensitive operator hygiene

Prefer Blender data APIs. When an operator is unavoidable:

1. deselect everything;
2. select the intended object;
3. make it active in the view layer;
4. set the required mode explicitly;
5. run the operator;
6. return to Object mode.

Background execution exposes hidden context assumptions quickly; treat that as a design signal, not a reason
to add sleeps or UI automation.
