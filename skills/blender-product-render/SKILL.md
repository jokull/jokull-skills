---
name: blender-product-render
description: "Builds product renders, marketing shots, App Store screenshots, and 3D web/app assets by scripting Blender headlessly in Python instead of modelling in the GUI — procedural scene from real dimensions, per-shot pose tables, solved camera framing, and a one-command pipeline that re-renders from scratch. Use when the user wants a rendered product image, device mockup, hero render, store screenshot with a 3D device, a GLB/USDZ export from a .blend, or when an existing render needs to change and the scene should be reproducible rather than hand-tweaked."
compatibility: Requires a local Blender install (4.x/5.x) reachable at /Applications/Blender.app/Contents/MacOS/Blender or `blender` on PATH. GPU rendering assumes Metal on macOS; falls back to CPU.
license: MIT
metadata:
  author: jokull
  version: "1.0"
---

# Scripted product renders in Blender

The premise: **the `.blend` file is an output, not a source.** A Python script builds the whole
scene from nothing on every run, so the scene is diffable, reviewable, and re-renderable after any
upstream change. Hand-tweaking a saved scene in the GUI destroys that — the next change starts from
"open the file and remember what you did".

This is what makes an agent able to work on renders at all. You cannot nudge a light in a viewport
you cannot see. You *can* change `energy=4.0` to `3.2`, re-run one command, and look at the PNG.

## When this is the wrong tool

There is a whole tier of Blender MCP servers that drive a **live** Blender session — good for
open-ended exploration, sculpting, and poking at a scene somebody else authored. Use one of those
when the goal is "help me figure out what this scene should be", and use this skill when the goal is
"this image must regenerate identically, on any machine, after an upstream change". A render that
ships — a store screenshot, a hero, a web asset — belongs in a script. If a live session produced
something good, port it into `build_scene.py` before it becomes the only copy.

## Non-negotiables

1. **Headless, always.** `blender --background --python build_scene.py -- <args>`. Never open the GUI.
2. **Build from empty.** Start with `bpy.ops.wm.read_factory_settings(use_empty=True)`. No inherited
   startup scene, no default cube, no drift between machines.
3. **Real units, sourced.** Model in metres with millimetre constants taken from the actual spec
   sheet or measured part. Put the source in a comment *and* a custom property.
4. **Parameters as data, not code.** One dict/table of per-shot poses at the top of the file. Every
   knob a human will want to turn lives there, named, with a comment saying what it does.
5. **Emit the `.blend` as an artifact.** `--save-blend` (with `bpy.ops.file.pack_all()` first) so a
   human can open and inspect what the script built. It is disposable; regenerating it is one command.
6. **Look at the output.** Read the rendered PNG back before claiming anything about it. A render
   that "should" look right routinely does not.

## Scaffold

```python
"""build_scene.py — <what this renders, and the evidence base for its dimensions>."""
import argparse, math, os, sys
import bpy, bmesh
from mathutils import Vector

MM = 0.001
BODY_W, BODY_H, BODY_T = 77.6 * MM, 163.0 * MM, 8.25 * MM   # Apple spec, iPhone 16 Pro Max
FINAL_W, FINAL_H = 1260, 2736
SUPER = 2                                # render 2x, downscale in compose

# (rot_x tilt-away, rot_y side-lean, rot_z in-frame lean, shift_x,
#  bottom_frac, width_frac, fade_start, fade_end)
POSES = {
    1: (-18.0,  5.0, -4.0, 0.0, 0.080, 0.95, 0.445, 0.520),
    2: (-20.0, -6.0,  5.0, 0.0, 0.075, 0.96, 0.445, 0.520),
}

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--shot", type=int, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--preview", action="store_true")   # fast: 1x res, few samples
    p.add_argument("--save-blend", default=None)
    return p.parse_args(argv)
```

Blender swallows its own flags, so script arguments go after a bare `--`. Everything the script
needs — input textures, output path, which shot — arrives as a flag. No hardcoded absolute paths.

## Geometry: model in manufacturing order

Build the way the object is actually made, not the way it looks. For a phone body: extrude a slab
from a rounded-rect outline (plan-view corner radius baked into the profile), then bevel *only* the
two horizontal edge rings with a weighted bevel for the rail-to-face blend. Beveling everything
double-rounds the corners and reads as a soap bar.

```python
bw = bm.edges.layers.float.new("bevel_weight_edge")
for e in bm.edges:
    if len({round(v.co.z, 6) for v in e.verts}) == 1:   # horizontal ring only
        e[bw] = 1.0
bev = obj.modifiers.new("EdgeBlend", "BEVEL")
bev.limit_method, bev.width, bev.segments, bev.profile = "WEIGHT", 2.2 * MM, 8, 0.72
```

Assign `material_index` per face while the bmesh is still open — side faces are the metal rail, caps
are glass. Sorting materials out later means re-selecting faces you no longer have handles to.

## Camera framing is arithmetic, not eyeballing

Never hand-tune camera distance until it looks right. Solve it. With a vertical sensor fit, the
visible frame height at distance `d` is `d * sensor_height / lens`. Rotate the bounding box by the
pose, measure its projected width, then set `d` so the object spans exactly `width_frac` of the
frame and its bottom edge sits at `bottom_frac` of frame height:

```python
eul = mathutils.Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ")
corners = [eul.to_matrix() @ Vector(c) for c in bbox_corners]
proj_w = max(c.x for c in corners) - min(c.x for c in corners)
cam.location.z *= proj_w / (width_frac * frame_w)          # solve distance
frame_h = cam.location.z * SENSOR_H / LENS
obj.location.y = -frame_h / 2 + bottom_frac * frame_h - min(c.y for c in corners)
```

Now `width_frac = 0.96` means what it says, poses are comparable across shots, and changing the lens
does not silently reframe everything. `width_frac > 1` deliberately crops the object's edges out of
frame — a legitimate composition, but only when nothing load-bearing lives near the edge.

## Lighting: name the intent

Three or four area lights, each named for its job, is enough for a product shot: one large pooled
softbox (the key, slightly warm if the product is warm), one or two narrow raking strips at grazing
angles to draw metal edges as a light line, and a weak frontal fill so black surfaces separate from
a dark backdrop.

```python
area("Large pooled softbox",   (-0.26, -0.08, 0.34), (24, -22, 0), 0.8, 0.8, 4.0, (1.0, .965, .915))
area("Rail rake strip right",  ( 0.30, -0.15, 0.12), (60,  62, 0), 0.04, 0.8, 3.0)
area("Tiny frontal fill",      ( 0.0,  -0.05, 0.50), ( 0,   0, 0), 0.4, 0.4, 0.5)
```

Names show up in the outliner and in the diff — `area("key", ...)` teaches nobody anything, but
"rail rake strip" tells the next reader why it exists and what breaks if you delete it.

A physical backdrop plane below the product beats `film_transparent` when you want a real contact
shadow and a lit environment. A procedural radial gradient on it (`TexGradient` QUADRATIC_SPHERE →
ColorRamp) gives a designed studio sweep that stays dark at the frame edges where captions land.
Use `film_transparent = True` only when a downstream compositing step owns the background.

## Screen content and colour management

To put a real screenshot on a device screen, use an **emissive plane** just above the glass, mixed
with a glossy BSDF through a `LayerWeight` fresnel at ~0.04 blend — a whisper of sheen, because the
UI still has to read.

Two traps:

- **Sample the texture in object space, not UVs.** A rounded-rect n-gon's vertex-interpolated UVs
  distort badly across the interior. `TexCoord.Object → Mapping (scale 1/W, 1/H) → TexImage`.
- **Set `scene.view_settings.view_transform = "Standard"`.** AgX/Filmic tone-map the UI and your
  screenshot no longer matches the app's actual colours. Standard reproduces the capture's sRGB
  values exactly. (For a pure product shot with no UI, AgX is the better look.)

A `MapRange` on the object-space Y, mixing the texture toward the backdrop colour, fades an empty
upper screen into the stage instead of ending in a hard black rectangle.

## Render settings

```python
scene.render.engine = "CYCLES"
scene.cycles.samples = 24 if args.preview else 160
scene.cycles.use_denoising = True
try:
    scene.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"       # CUDA / OPTIX / HIP elsewhere
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
except Exception:
    scene.cycles.device = "CPU"
scale = 1 if args.preview else SUPER
scene.render.resolution_x, scene.render.resolution_y = FINAL_W * scale, FINAL_H * scale
```

Iterate with `--preview` (seconds), commit with the full render (minutes). Supersample 2x and
downscale in the compositing step — it is the cheapest quality win available and it anti-aliases the
UI texture properly.

## Provenance as custom properties

```python
obj["source"] = "Apple spec 163.0x77.6x8.25mm"
obj["scale"] = "1 BU = 1 m"
scene["capture"] = os.path.abspath(args.capture)
scene["construction"] = "procedural rounded-rect slab, weighted-edge rail blend, emissive UI plane"
```

Custom properties survive into the saved `.blend`, so the artifact carries its own explanation. When
a dimension is a guess rather than a spec, say so there.

## Pipeline shape

Split into cacheable stages with one orchestrator on top, and make the expensive upstream stage
skippable:

- **A — capture** the real thing (simulator screenshots, photographs, exported UI). Slow, cached on
  disk, refreshed by its own script only when the product actually changed.
- **B — render** each shot in Blender from the stage-A inputs.
- **C — compose** gradients, captions, and typography over the render (PIL/ImageMagick), reading the
  copy from a text file *fresh* each run so wording changes never require a re-render.

```bash
for SHOT in 1 2 3 4 5 6; do
  "$BLENDER" --background --python build_scene.py -- \
    --shot "$SHOT" --capture "captures/0$SHOT-raw.png" --out "blender/render-0$SHOT.png" \
    2>&1 | grep -E "RENDER_OK|Error|Traceback" || true
  [ -f "blender/render-0$SHOT.png" ] || { echo "render $SHOT failed"; exit 1; }
done
```

Blender's stdout is enormous and its exit code is unreliable — print a unique `RENDER_OK` sentinel
at the end of the script, grep for it plus `Error|Traceback`, and **assert the output file exists**.
Give `render-all.sh` a `--skip-render` flag so caption iteration does not pay for renders.

Finish by tiling every shot into one contact sheet and reading it. Reviewing shots one at a time
hides inconsistency in pose, exposure, and crop across the set.

## Exports (GLB, USDZ) and material baking

Procedural materials do not export. When shipping a `.blend` to web (`three.js`, `model-viewer`) or
to SceneKit/RealityKit, the scene must be baked and rebuilt first, and a few things reliably bite:
z-fighting on shrinkwrapped decals, missing UVs on `from_pydata` meshes, and texture size vs. asset
budget. **Read `references/export-and-bake.md` before writing any export script.**

## Give the script an eyeless self-check

You are reading a PNG through a narrow straw. Make the script also emit a machine-readable digest,
so the cheap failures get caught without looking at anything:

```python
if args.inspect:
    import json
    print("SCENE_JSON " + json.dumps({
        "objects": {o.name: {
            "tris": sum(len(p.vertices) - 2 for p in o.data.polygons),
            "materials": [m.name for m in o.data.materials],
            "bbox_mm": [round(v * 1000, 2) for v in o.dimensions],
        } for o in scene.objects if o.type == "MESH"},
        "camera": {"lens": cam.data.lens, "z_mm": round(cam.location.z * 1000, 1)},
        "lights": {o.name: o.data.energy for o in scene.objects if o.type == "LIGHT"},
        "engine": scene.render.engine, "samples": scene.cycles.samples,
        "res": [scene.render.resolution_x, scene.render.resolution_y],
        "view_transform": scene.view_settings.view_transform,
    }))
```

Grep `SCENE_JSON` out of Blender's noise and assert on it: dimensions match the spec sheet, the
texture actually loaded, nothing got orphaned, the view transform is still `Standard`. A dark render
is ambiguous — "the key light has energy 0" is not. This is also the honest way to diff two runs.

## Working rhythm

1. Change one parameter in the table.
2. Re-render that shot with `--preview`.
3. Read the PNG.
4. Full render only once the preview is right; contact-sheet the whole set before shipping.

Resist adding geometry the shot does not sell. Fidelity budget goes where the eye lands — the metal
edge highlight and the screen glass, not the camera bump nobody sees at this angle.
