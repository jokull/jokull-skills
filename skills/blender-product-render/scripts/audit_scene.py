#!/usr/bin/env python3
"""Audit a Blender product scene and optional PNG delivery files.

Run inside Blender:
  blender --background scene.blend --python audit_scene.py -- [options]
"""

import argparse
import json
import os
import struct
import sys
from collections import Counter

import bpy


def script_arguments():
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def parse_size(value):
    try:
        width, height = value.lower().split("x", 1)
        return int(width), int(height)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError("size must look like 1024x1024") from error


def png_info(path):
    with open(path, "rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a PNG file")
        length = struct.unpack(">I", handle.read(4))[0]
        if handle.read(4) != b"IHDR" or length != 13:
            raise ValueError("missing PNG IHDR")
        width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", handle.read(13))
        handle.read(4)  # IHDR CRC
        has_trns = False
        while True:
            raw_length = handle.read(4)
            if len(raw_length) != 4:
                break
            chunk_length = struct.unpack(">I", raw_length)[0]
            chunk_type = handle.read(4)
            if chunk_type == b"tRNS":
                has_trns = True
            handle.seek(chunk_length + 4, os.SEEK_CUR)
            if chunk_type == b"IEND":
                break
    color_names = {
        0: "grayscale",
        2: "rgb",
        3: "indexed",
        4: "grayscale-alpha",
        6: "rgba",
    }
    return {
        "path": os.path.abspath(path),
        "width": width,
        "height": height,
        "bit_depth": bit_depth,
        "color_type": color_names.get(color_type, f"unknown-{color_type}"),
        "has_alpha": color_type in {4, 6} or has_trns,
    }


def datablock_file_record(kind, datablock):
    filepath = getattr(datablock, "filepath", "")
    packed = bool(getattr(datablock, "packed_file", None))
    builtin = filepath.startswith("<") or not filepath
    absolute = filepath if builtin else bpy.path.abspath(filepath)
    return {
        "kind": kind,
        "name": datablock.name,
        "filepath": filepath,
        "absolute_path": absolute,
        "packed": packed,
        "exists": builtin or packed or os.path.isfile(absolute),
        "builtin": builtin,
    }


def scene_report():
    scene = bpy.context.scene
    camera = scene.camera
    object_types = Counter(obj.type for obj in scene.objects)
    external = []
    for image in bpy.data.images:
        if image.source == "FILE":
            external.append(datablock_file_record("image", image))
    for font in bpy.data.fonts:
        external.append(datablock_file_record("font", font))
    for library in bpy.data.libraries:
        external.append(datablock_file_record("library", library))

    meshes = []
    for obj in sorted((item for item in scene.objects if item.type == "MESH"), key=lambda item: item.name):
        meshes.append(
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "dimensions": [round(value, 6) for value in obj.dimensions],
                "scale": [round(value, 6) for value in obj.scale],
                "modifiers": [modifier.type for modifier in obj.modifiers],
                "hide_render": obj.hide_render,
            }
        )

    materials = []
    for material in sorted(bpy.data.materials, key=lambda item: item.name):
        node_tree = material.node_tree
        materials.append(
            {
                "name": material.name,
                "use_nodes": node_tree is not None,
                "node_count": len(node_tree.nodes) if node_tree else 0,
            }
        )

    return {
        "blend_file": bpy.data.filepath,
        "blender_version": bpy.app.version_string,
        "scene": {
            "name": scene.name,
            "engine": scene.render.engine,
            "resolution": [
                scene.render.resolution_x,
                scene.render.resolution_y,
                scene.render.resolution_percentage,
            ],
            "file_format": scene.render.image_settings.file_format,
            "color_mode": scene.render.image_settings.color_mode,
            "film_transparent": scene.render.film_transparent,
            "camera": None
            if camera is None
            else {
                "name": camera.name,
                "type": camera.data.type,
                "ortho_scale": camera.data.ortho_scale if camera.data.type == "ORTHO" else None,
            },
            "object_types": dict(sorted(object_types.items())),
        },
        "meshes": meshes,
        "materials": materials,
        "external_files": external,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", action="append", default=[], help="PNG delivery file to inspect")
    parser.add_argument("--require-size", type=parse_size)
    parser.add_argument("--require-rgb", action="store_true", help="Require opaque RGB PNGs")
    parser.add_argument("--require-packed", action="store_true", help="Require non-builtin assets to be packed")
    parser.add_argument("--expect-camera", choices=("ORTHO", "PERSP", "PANO"))
    args = parser.parse_args(script_arguments())

    report = scene_report()
    report["images"] = []
    failures = []

    camera = report["scene"]["camera"]
    if camera is None:
        failures.append("scene has no active camera")
    elif args.expect_camera and camera["type"] != args.expect_camera:
        failures.append(f"camera is {camera['type']}, expected {args.expect_camera}")

    for path in args.image:
        try:
            info = png_info(path)
            report["images"].append(info)
            if args.require_size and (info["width"], info["height"]) != args.require_size:
                failures.append(
                    f"{path}: size {info['width']}x{info['height']}, expected "
                    f"{args.require_size[0]}x{args.require_size[1]}"
                )
            if args.require_rgb and (info["color_type"] != "rgb" or info["has_alpha"]):
                failures.append(f"{path}: expected opaque RGB PNG, got {info['color_type']}")
        except (OSError, ValueError) as error:
            failures.append(f"{path}: {error}")

    missing = [item for item in report["external_files"] if not item["exists"]]
    failures.extend(f"missing {item['kind']}: {item['absolute_path']}" for item in missing)
    if args.require_packed:
        unpacked = [
            item
            for item in report["external_files"]
            if not item["builtin"] and not item["packed"]
        ]
        failures.extend(f"unpacked {item['kind']}: {item['name']}" for item in unpacked)

    report["failures"] = failures
    report["ok"] = not failures
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
