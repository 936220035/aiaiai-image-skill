#!/usr/bin/env python3
"""Generate and edit images through the AIAIAI OpenAI-compatible API."""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import mimetypes
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Optional


DEFAULT_BASE_URL = "https://api.aiaiai001.com/v1"
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_TIMEOUT = 300
MAX_ATTEMPTS = 3
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
CONFIG_PATH = Path.home() / ".config" / "aiaiai-image" / "credentials.json"


class ImageAPIError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, uncertain: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.uncertain = uncertain


def normalize_base_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ImageAPIError("Base URL must be an absolute http(s) URL.")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ImageAPIError("Base URL must use HTTPS outside local testing.")
    return value


def api_url(base_url: str, endpoint: str) -> str:
    base_url = normalize_base_url(base_url)
    endpoint = "/" + endpoint.lstrip("/")
    if base_url.endswith("/v1") and endpoint.startswith("/v1/"):
        endpoint = endpoint[3:]
    if not base_url.endswith("/v1") and not endpoint.startswith("/v1/"):
        endpoint = "/v1" + endpoint
    return base_url + endpoint


def read_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImageAPIError(f"Credential file is invalid: {path}") from exc
    if not isinstance(data, dict):
        raise ImageAPIError(f"Credential file is invalid: {path}")
    return data


def write_config(api_key: str, path: Path = CONFIG_PATH) -> None:
    api_key = api_key.strip()
    if not api_key:
        raise ImageAPIError("API key cannot be empty.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps({"api_key": api_key}, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(temp_path, 0o600)
    except OSError:
        pass
    temp_path.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def remove_config(path: Path = CONFIG_PATH) -> bool:
    if not path.exists():
        return False
    path.unlink()
    return True


def resolve_api_key(explicit: Optional[str], path: Path = CONFIG_PATH) -> str:
    candidates = [explicit, os.environ.get("AIAIAI_API_KEY"), read_config(path).get("api_key")]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    raise ImageAPIError(
        "No API key found. Run 'aiaiai_image.py configure' or set AIAIAI_API_KEY."
    )


def resolve_base_url(explicit: Optional[str]) -> str:
    return normalize_base_url(explicit or os.environ.get("AIAIAI_BASE_URL") or DEFAULT_BASE_URL)


def json_body(fields: dict[str, Any]) -> bytes:
    return json.dumps(fields, ensure_ascii=False).encode("utf-8")


def multipart_body(fields: dict[str, Any], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----aiaiai-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for name, path in files:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def extract_error_message(raw: bytes, status: int | None = None) -> str:
    try:
        payload = json.loads(raw.decode("utf-8"))
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = error.get("message") or error.get("type") or error
        else:
            message = error or payload
        text = str(message)
    except Exception:
        text = raw.decode("utf-8", errors="replace").strip() or "empty response"
    prefix = f"HTTP {status}: " if status else ""
    return prefix + text[:1000]


def perform_request(
    request_factory: Callable[[], urllib.request.Request], timeout: int, max_attempts: int
) -> bytes:
    last_error: Optional[ImageAPIError] = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request_factory(), timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            last_error = ImageAPIError(
                extract_error_message(raw, exc.code),
                retryable=exc.code in RETRYABLE_STATUS,
                uncertain=exc.code >= 500,
            )
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as exc:
            last_error = ImageAPIError(
                f"Network request failed: {exc}", retryable=True, uncertain=True
            )

        if not last_error.retryable or attempt >= max_attempts:
            break
        time.sleep(min(2 ** (attempt - 1), 4))

    assert last_error is not None
    suffix = " Retrying may duplicate a completed upstream charge." if last_error.uncertain else ""
    raise ImageAPIError(str(last_error) + suffix, retryable=last_error.retryable, uncertain=last_error.uncertain)


def parse_payload(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImageAPIError("Image API returned malformed JSON.") from exc
    if not isinstance(payload, dict):
        raise ImageAPIError("Image API returned an unexpected response.")
    if payload.get("error"):
        raise ImageAPIError(extract_error_message(raw))
    return payload


def numbered_output(path: Path, index: int, total: int) -> Path:
    if total == 1:
        return path
    return path.with_name(f"{path.stem}-{index}{path.suffix}")


def save_images(payload: dict[str, Any], output: Path, timeout: int) -> list[Path]:
    records = payload.get("data")
    if not isinstance(records, list) or not records:
        raise ImageAPIError("Image API response did not contain data records.")
    output.parent.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ImageAPIError("Image API returned an invalid image record.")
        destination = numbered_output(output, index, len(records))
        encoded = record.get("b64_json")
        url = record.get("url")
        if isinstance(encoded, str) and encoded:
            try:
                destination.write_bytes(base64.b64decode(encoded, validate=True))
            except (ValueError, OSError) as exc:
                raise ImageAPIError("Failed to decode the returned Base64 image.") from exc
        elif isinstance(url, str) and url:
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    destination.write_bytes(response.read())
            except Exception as exc:
                raise ImageAPIError(f"Failed to download the returned image URL: {exc}") from exc
        else:
            raise ImageAPIError("Image record did not contain b64_json or url.")
        saved.append(destination.resolve())
    return saved


def request_headers(api_key: str, content_type: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "aiaiai-image-skill/1.0"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def run_check(args: argparse.Namespace) -> int:
    api_key = resolve_api_key(args.api_key)
    url = api_url(resolve_base_url(args.base_url), "/models")

    def factory() -> urllib.request.Request:
        return urllib.request.Request(url, headers=request_headers(api_key), method="GET")

    payload = parse_payload(perform_request(factory, args.timeout, args.max_attempts))
    models = payload.get("data") if isinstance(payload.get("data"), list) else []
    names = {
        item.get("id") for item in models if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    print(json.dumps({"ok": True, "base_url": resolve_base_url(args.base_url), "model": args.model, "model_listed": args.model in names}, ensure_ascii=False, indent=2))
    return 0


def generation_fields(args: argparse.Namespace) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "model": args.model,
        "prompt": args.prompt,
        "n": args.n,
        "response_format": "b64_json",
    }
    if args.size != "auto":
        fields["size"] = args.size
    if args.quality != "auto":
        fields["quality"] = args.quality
    if args.output_format != "auto":
        fields["output_format"] = args.output_format
    return fields


def run_image(args: argparse.Namespace, edit: bool) -> int:
    if args.n < 1 or args.n > 4:
        raise ImageAPIError("--n must be between 1 and 4.")
    api_key = resolve_api_key(args.api_key)
    base_url = resolve_base_url(args.base_url)
    endpoint = "/images/edits" if edit else "/images/generations"
    url = api_url(base_url, endpoint)
    fields = generation_fields(args)

    if edit:
        image_path = args.image.expanduser().resolve()
        if not image_path.is_file():
            raise ImageAPIError(f"Input image does not exist: {image_path}")
        body, boundary = multipart_body(fields, [("image", image_path)])
        content_type = f"multipart/form-data; boundary={boundary}"
    else:
        body = json_body(fields)
        content_type = "application/json"

    if args.dry_run:
        print(json.dumps({"url": url, "endpoint": endpoint, "fields": fields, "has_image": edit, "authorization": "Bearer ***"}, ensure_ascii=False, indent=2))
        return 0

    def factory() -> urllib.request.Request:
        return urllib.request.Request(
            url,
            data=body,
            headers=request_headers(api_key, content_type),
            method="POST",
        )

    payload = parse_payload(perform_request(factory, args.timeout, args.max_attempts))
    output = args.out.expanduser()
    saved = save_images(payload, output, args.timeout)
    print(json.dumps({"ok": True, "model": args.model, "endpoint": endpoint, "images": [str(path) for path in saved]}, ensure_ascii=False, indent=2))
    return 0


def add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", help="One-time API key override. Prefer configure or AIAIAI_API_KEY.")
    parser.add_argument("--base-url", help=f"API base URL. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-attempt timeout in seconds.")
    parser.add_argument("--max-attempts", type=int, choices=range(1, MAX_ATTEMPTS + 1), default=1, help="Total attempts. More than one may duplicate charges after uncertain failures.")
    parser.add_argument("--model", default=DEFAULT_MODEL)


def add_image_args(parser: argparse.ArgumentParser) -> None:
    add_runtime_args(parser)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default="auto")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser("configure", help="Save an API key in the local user profile.")
    configure.add_argument("--api-key", help="API key value. Omit for hidden interactive input.")

    subparsers.add_parser("remove-key", help="Remove the locally saved API key.")

    check = subparsers.add_parser("check", help="Check API access without generating an image.")
    add_runtime_args(check)

    generate = subparsers.add_parser("generate", help="Generate an image from text.")
    add_image_args(generate)

    edit = subparsers.add_parser("edit", help="Edit an existing image.")
    add_image_args(edit)
    edit.add_argument("--image", type=Path, required=True)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "configure":
            key = args.api_key or getpass.getpass("AIAIAI API key: ")
            write_config(key)
            print(f"Saved API key to {CONFIG_PATH}")
            return 0
        if args.command == "remove-key":
            print("Removed saved API key." if remove_config() else "No saved API key was found.")
            return 0
        if args.timeout <= 0:
            raise ImageAPIError("--timeout must be greater than zero.")
        if args.command == "check":
            return run_check(args)
        return run_image(args, edit=args.command == "edit")
    except ImageAPIError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
