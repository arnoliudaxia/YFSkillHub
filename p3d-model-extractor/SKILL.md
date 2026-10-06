---
name: p3d-model-extractor
description: Extract publicly loaded 3D models from p3d.in share pages into a standard glTF scene and a Blender .blend scene, including Draco geometry, node transforms, animations, UVs, and separately hosted PBR textures. Use when a user provides a p3d.in model-share URL and asks to download, inspect, convert, or open the model in Blender.
compatibility: Requires Python 3, Node.js, and Blender 4.x or newer for .blend output. Network access to p3d.in and uploads2.p3d.in is required.
---

# p3d.in model extractor

Use this skill only for models the user is authorized to download or reuse. It reads the public viewer API and the binary asset actually loaded by the share page; it does not bypass authentication or model permissions.

## Quick start

From any directory, run the bundled script with a p3d.in share URL:

```text
python <skill-directory>/scripts/p3d_extract.py https://p3d.in/<shortid>/spin
```

By default it writes a directory named `p3d-<shortid>` below the current directory containing:

- `model.gltf` and `model.bin`: standard, uncompressed glTF geometry with original node hierarchy and animation data.
- `model.glb`: primary textured single-file GLB, with images embedded and converted to PNG for broad viewer compatibility.
- `textures/`: separately hosted PBR texture images.
- `model.blend`: Blender scene imported from that glTF, with textures packed into the blend.
- `source-model.bin`, `source-model.json`, and `api.json`: downloaded/source metadata useful for debugging.

Useful options:

```text
--output <dir>       Explicit output directory
--no-blender         Produce glTF and textures without invoking Blender
--keep-work          Keep Draco decoder and intermediate decoded files
```

## What the script does

1. Extracts the short ID from the p3d.in URL.
2. Requests `/api/viewer_models/<shortid>?type=editor&cdn=true&webp=true`.
3. Downloads `viewer_model.base_url`, which is a P3D container holding glTF JSON and a binary buffer.
4. Extracts the JSON and buffer from the P3D container (`P3D`, `JSON`, JSON length at offset 12).
5. Downloads textures listed in the API's `textures` array. The p3d.in API commonly returns WebP URLs even when `format` says PNG.
6. Downloads p3d.in's current Draco decoder and decodes each `KHR_draco_mesh_compression` bufferView. Pass the **complete** bufferView bytes to `DecoderBuffer.Init`; do not strip a fixed number of prefix bytes. p3d.in's loader passes the complete bufferView and different model revisions use different prefix layouts.
7. Builds a standard glTF. It retains the original `nodes`, `children`, local transforms, and animation accessors, while replacing only compressed geometry with ordinary POSITION/NORMAL/TEXCOORD_0/index accessors. This avoids the coordinate and parent-transform errors caused by an OBJ intermediate.
8. Writes PBR material references: diffuse → base color, normal → normal map, and the p3d.in packed metalness/roughness image uses B → metallic and G → roughness.
9. Imports the standard glTF into Blender, packs all images, converts image datablocks to PNG, saves `model.blend`, and exports the primary textured single-file `model.glb`.

## Important implementation notes

- Do not reconstruct the scene through OBJ when a glTF result is wanted. OBJ loses glTF node hierarchy, animation, and transform semantics.
- Do not manually flip UVs in the generated standard glTF. Blender's glTF importer handles glTF UV conventions; manually applying `V = 1 - V` can invert the finished texture.
- Supports meshes with multiple primitives and multiple material slots; do not assume one mesh has one primitive or one material.
- A p3d.in P3D payload may contain a valid glTF JSON but no `images` array. Textures are often separate API resources and must be connected from `material_assignments`, `materials.texture_assignment_ids`, and `texture_assignments`.
- A Draco decoder can report a non-success attribute status while still exposing the decoded mesh. The bundled decoder checks that points and faces exist and preserves the decoded attributes.
- If Blender is unavailable, use `--no-blender`; the generated glTF is still usable by Blender, Godot, Unity tooling, and other glTF readers.
- The normal result is `model.glb`; use it for sharing and viewers that do not resolve external buffers. A `.gltf` must remain beside its referenced `.bin`; copying only the JSON file causes a missing-buffer error. The generated GLB embeds textures as PNG and does not require `EXT_texture_webp`.

## Troubleshooting

- `403` from CDN: the script sends `Referer: https://p3d.in/<shortid>/spin` and a browser User-Agent. Check network access and retry.
- No texture files: inspect `api.json`; if the API has no `textures` or texture assignments, the model may use only runtime/default material settings.
- Blender reports Draco errors: do not feed the original P3D payload or compressed glTF to Blender. Use the generated `model.gltf`, which contains decoded geometry.
- Components pile up at the origin: use the generated glTF directly. This indicates an OBJ/manual-parenting workflow was used instead of preserving the original glTF nodes.
