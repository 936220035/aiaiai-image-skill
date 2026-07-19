---
name: aiaiai-image
description: Generate or edit raster images through the AIAIAI OpenAI-compatible image API, save returned Base64 or URL images locally, and save a user-supplied dedicated image key for later use when explicitly requested. Use when a user asks Codex or Claude Code to create, redraw, transform, or edit an image with an AIAIAI API key, the GPT-Image group, api.aiaiai001.com, or the gpt-image-2 model.
---

# AIAIAI Image

Use the bundled `scripts/aiaiai_image.py` runner instead of the built-in image path when the request must use the user's AIAIAI relay account.

## Simple workflow

1. If the user has not supplied a key, ask them to create a dedicated image key in the AIAIAI console. Recommend limiting it to model `gpt-image-2`, group `GPT-Image`, and a small available balance.
2. If the user supplies a key and explicitly asks to save it locally, save it immediately and continue. Do not ask them to send it again:

```bash
python "{baseDir}/scripts/aiaiai_image.py" configure --api-key "<key supplied by user>"
```

3. Do not repeat the key in the response, logs, generated files, screenshots, or summary.
4. Generate or edit the requested image immediately after saving the key. A separate `check` is optional, not a required extra step.

If no key was supplied in chat, hidden interactive setup remains available:

```bash
python "{baseDir}/scripts/aiaiai_image.py" configure
```

When Plan mode and user-question tools are available, ask short questions only when important details such as style, aspect ratio, text, or reference-image intent are unclear. Otherwise use reasonable defaults and proceed.

## Generate an image

```bash
python "{baseDir}/scripts/aiaiai_image.py" generate \
  --prompt "A photorealistic orange cat in a spacesuit watching television on the moon" \
  --size 1024x1024 \
  --out ./generated/moon-cat.png
```

## Edit an image

```bash
python "{baseDir}/scripts/aiaiai_image.py" edit \
  --image ./input.png \
  --prompt "Keep the subject unchanged and replace the background with the moon" \
  --out ./generated/edited.png
```

## Workflow rules

- Use model `gpt-image-2` unless the user explicitly requests another model known to be available.
- Treat `--size` as a requested size, not a promise of true 2K or 4K output. Report the actual saved pixel dimensions when the task depends on resolution.
- The API key's group controls billing and channel access. The script cannot override a key that was created for another group.
- The default endpoint is `https://api.aiaiai001.com/v1`; use `AIAIAI_BASE_URL` only when the user explicitly needs another compatible endpoint.
- The runner accepts both `data[0].b64_json` and `data[0].url` responses.
- Default to one request attempt. A timeout or dropped connection can be an uncertain completion and retrying may duplicate charges. Ask before using `--max-attempts 2` or higher.
- Save output inside the current workspace unless the user provides another path.
- For reference-image editing, pass the local attachment path with `--image`; do not paste Base64 into chat.
- Surface API error messages without exposing authorization headers or raw Base64 data.

Read `references/api.md` only when endpoint parameters, configuration precedence, or troubleshooting details are needed.
