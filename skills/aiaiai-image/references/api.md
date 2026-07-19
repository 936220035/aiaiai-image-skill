# API and runtime reference

## Defaults

- Base URL: `https://api.aiaiai001.com/v1`
- Model: `gpt-image-2`
- Text-to-image: `POST /images/generations`
- Image edit: `POST /images/edits`
- Model check: `GET /models`
- Response format requested by the runner: `b64_json`
- Request timeout: 300 seconds
- Attempts: 1 by default, maximum 3

## Credential resolution

The runner resolves the API key in this order:

1. `--api-key`
2. `AIAIAI_API_KEY`
3. `~/.config/aiaiai-image/credentials.json`

The Base URL resolves in this order:

1. `--base-url`
2. `AIAIAI_BASE_URL`
3. `https://api.aiaiai001.com/v1`

Use `configure` without `--api-key` for hidden interactive input. Never put a real key in the repository.

## Common errors

- `401`: the key is missing, invalid, or expired.
- `403`: the key or account does not have access to the requested model/group.
- `404`: the configured Base URL is wrong or the image endpoint is unavailable.
- `429`: the upstream account pool or channel is rate limited; retry later rather than immediately creating many duplicate requests.
- `5xx`, timeout, or connection reset: the completion state may be uncertain. Retrying can duplicate a successful upstream charge.
- Successful request but unexpected dimensions: the upstream image provider may normalize or ignore the requested size. Check the actual file dimensions.

## Group behavior

The group is selected when the user creates the API key in the AIAIAI console. For image generation, choose `GPT-Image`. The request body does not force a New API group, so a key assigned to another group may fail even when the model name is correct.
