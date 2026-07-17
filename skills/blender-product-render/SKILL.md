---
name: blender-product-render
description: "Builds and iterates evidence-led industrial product models and product renders in Blender with deterministic `bpy` scripts, physically scaled procedural geometry and materials, editable source objects, headless rendering, and visual delivery checks. Use when asked to model a manufactured object from photographs, drawings, measurements, CAD or printable references; create a Blender-based app icon or product shot; refine molded plastic, metal, glass, printed legends, or microscopic surface artifacts; or deliver reproducible `.blend` plus PNG outputs rather than an AI-generated approximation."
license: MIT
metadata:
  author: jokull
  version: "1.0"
---

# Blender Product Render

Treat the render as the final observation of a manufactured object. Recover the object's construction,
material, typography, camera, and light separately; do not paint a plausible-looking result into one
bitmap.

## Choose the control path

Prefer a project-owned `build_scene.py` executed with Blender in the background:

```bash
blender --background --python build_scene.py
```

This is the default for new procedural scenes, reproducible product renders, CI, and versioned outputs.
Use a live Blender bridge or MCP only when the task specifically depends on an already-open scene,
interactive selection, viewport state, or artist-guided edits. Keep the build script as source of truth
even when a `.blend` is also delivered.

## 1. Establish evidence and delivery requirements

Read repository instructions and inspect existing files before editing. Preserve unrelated work and prior
iterations.

Classify every source before modeling:

- **Dimensions and CAD/printable models** establish scale, wall thickness, profile, clearances, and topology.
- **Orthographic drawings and product photographs** establish silhouette, taper, fillets, dish, seams, and
  manufacturing transitions.
- **Macro photographs** establish grain, roughness response, pigment behavior, and microscopic defects.
- **Vector artwork and type research** establish legends and logos.
- **Rendered or AI-generated references** are mood references only unless independently measured.

Record which facts are measured, inferred, and art-directed. Do not infer microscopic geometry from a
compressed photograph or copy camera blur into a material.

Confirm the outputs: `.blend`, build script, render sizes, color mode, alpha policy, optional vector source,
and whether external assets must be packed. For app icons, normally deliver an unmasked square 1024 PNG
and a 2048 master; let the platform apply its icon mask unless the user requests a preview mask.

## 2. Model construction, not appearance

Set a physical unit relationship and store important dimensions as object custom properties. For objects
defined by industrial profiles, construct rings or cross-sections and loft them with consistent vertex
counts. Model the manufacturing sequence:

1. primary shell or body;
2. taper and draft;
3. functional recesses or dishes;
4. fillets and chamfers with plausible radii;
5. wall thickness and underside only where they affect silhouette, shadow, or editability.

Avoid stacked rounded rectangles that merely resemble a UI icon. Avoid impossible bevels, floating faces,
and detail whose scale has no physical interpretation. Prefer explicit mesh generation over long chains of
context-sensitive operators.

Name objects deterministically. Attach source, scale, and construction assumptions to the scene and model
as custom properties. See `references/bpy-patterns.md` when implementing a new build script.

## 3. Preserve editability

Keep semantic source objects and derive render geometry from them:

- retain text as a hidden `FONT` object, then duplicate and convert only the render copy;
- retain profile curves or parameter lists even if the final surface is a mesh;
- keep material controls named by physical meaning and scale;
- keep camera, lights, and backdrop as separate named objects;
- pack required fonts and images into the final `.blend` when portability matters.

Do not destructively replace the user's previous approved scene. Give each substantial visual direction a
new wave or versioned filename until the user chooses a final.

## 4. Build materials from light response

Make clean manufactured material variation come primarily from normals and roughness, not dirty albedo.

- Use object-space 3D coordinates for isotropic molded grain; `Generated` coordinates stretch when object
  dimensions differ.
- Express grain wavelength and bump height in scene units and document their millimetre equivalents.
- Couple height and roughness intentionally: molded peaks may return tighter highlights while valleys remain
  satin.
- Use a second, smaller scale only to break up highlights; do not make sandpaper.
- Keep color variation restrained unless photographed evidence proves otherwise.
- Let a large soft source reveal microfacets at grazing angles. Do not compensate for flat lighting by
  painting dark flecks into the base color.

AI-generated texture maps are candidates, not ground truth. Reject any map containing directional light,
shadows, perspective, recognizable object boundaries, or an unknown physical scale. Prefer procedural maps
or high-pass material evidence from real photography.

### Printed and dyed markings

Identify the process first: dye sublimation, screen printing, pad printing, laser marking, engraving, or a
separate inlay are materially different.

For absorbed dye, preserve the substrate surface, change pigment density, and introduce only a narrow
evidence-supported diffusion edge. Keep a dense core plus a separate faint fringe when needed. Do not add
extrusion, recess, a cast shadow, or noisy interior simply to make the print visible. Treat antialiasing and
photographic defocus as camera artifacts, not automatically as pigment behavior.

## 5. Compose as product photography

Use orthographic projection or a long focal length unless perspective is part of the product evidence.
Start with one large overhead or back-side softbox and a small frontal fill. Make contact shadow nearly
imperceptible. Use a neutral opaque backdrop for App Store output.

Fit the object to the intended mask or crop through camera composition, not by adding a decorative border.
Render the actual delivery composition early; a technically good material can disappear or become grotesque
at icon scale.

## 6. Iterate with truthful comparisons

For each wave:

1. change one evidence class—geometry, material, print, camera, or light;
2. render a fast 1024 preview;
3. inspect the complete composition;
4. inspect a magnified crop without inventing detail through sharpening;
5. compare against the exact source photograph or drawing;
6. reduce any artifact that becomes the subject instead of supporting the material;
7. render the 2048 master only after the preview passes.

Preserve rejected waves when they are useful comparisons. State why a change is supported by evidence and
where the source is too weak for certainty.

## 7. Validate the deliverables

Run the build from a clean Blender process. Reopen the saved `.blend` in background mode and inspect named
objects, modifiers, editable sources, materials, camera type, and packed dependencies.

Use the bundled audit script for a machine-readable scene and PNG check:

```bash
blender --background /absolute/path/product.blend \
  --python /absolute/path/to/skills/blender-product-render/scripts/audit_scene.py -- \
  --image /absolute/path/icon-1024.png \
  --image /absolute/path/icon-2048.png \
  --expect-camera ORTHO \
  --require-packed \
  --require-rgb
```

Add `--require-size 1024x1024` only when every supplied image must have that size; otherwise inspect the
reported dimensions individually. The script exits nonzero when a requested invariant fails.

Always inspect the final pixels visually after the audit. Downsample to representative device sizes when
the asset is an icon. A successful render command proves that Blender ran, not that the object looks real.

## Failure modes to reject

- A reference photograph supplies geometry, lighting, and color simultaneously.
- Surface grain becomes dirt, orange peel, or a visible repeating pattern.
- A printed legend floats above a compound surface or loses the substrate grain entirely.
- An orthographic industrial object acquires wide-angle perspective.
- Every revision overwrites the only `.blend` and eliminates comparison evidence.
- A packed scene silently depends on a local font or texture.
- A 2048 image is accepted without checking the 1024 composition and small-icon read.
