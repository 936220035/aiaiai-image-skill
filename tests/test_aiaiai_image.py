from __future__ import annotations

import base64
import importlib.util
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "skills" / "aiaiai-image" / "scripts" / "aiaiai_image.py"
SPEC = importlib.util.spec_from_file_location("aiaiai_image", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


class ImageSkillTests(unittest.TestCase):
    def test_api_url_accepts_base_with_v1(self) -> None:
        self.assertEqual(
            module.api_url("https://example.com/v1", "/images/generations"),
            "https://example.com/v1/images/generations",
        )
        self.assertEqual(
            module.api_url("https://example.com", "/images/generations"),
            "https://example.com/v1/images/generations",
        )

    def test_non_https_remote_url_is_rejected(self) -> None:
        with self.assertRaises(module.ImageAPIError):
            module.normalize_base_url("http://example.com/v1")

    def test_environment_key_precedes_saved_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "credentials.json"
            config.write_text(json.dumps({"api_key": "saved"}), encoding="utf-8")
            with mock.patch.dict(os.environ, {"AIAIAI_API_KEY": "environment"}):
                self.assertEqual(module.resolve_api_key(None, config), "environment")

    def test_save_base64_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "image.png"
            payload = {"data": [{"b64_json": base64.b64encode(b"png-data").decode()}]}
            saved = module.save_images(payload, output, 5)
            self.assertEqual(output.read_bytes(), b"png-data")
            self.assertEqual(saved, [output.resolve()])

    def test_multipart_does_not_include_auth_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "input.png"
            image.write_bytes(b"image-bytes")
            body, boundary = module.multipart_body({"prompt": "hello"}, [("image", image)])
            self.assertIn(boundary.encode(), body)
            self.assertIn(b"hello", body)
            self.assertIn(b"image-bytes", body)
            self.assertNotIn(b"secret-key", body)

    def test_dry_run_redacts_authorization(self) -> None:
        parser = module.build_parser()
        args = parser.parse_args([
            "generate", "--api-key", "secret-key", "--prompt", "cat", "--out", "cat.png", "--dry-run"
        ])
        with mock.patch("builtins.print") as output:
            self.assertEqual(module.run_image(args, edit=False), 0)
        rendered = output.call_args.args[0]
        self.assertIn("Bearer ***", rendered)
        self.assertNotIn("secret-key", rendered)

    def test_generate_end_to_end_against_local_server(self) -> None:
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                received["path"] = self.path
                received["authorization"] = self.headers.get("Authorization")
                length = int(self.headers.get("Content-Length", "0"))
                received["body"] = json.loads(self.rfile.read(length).decode("utf-8"))
                payload = {"data": [{"b64_json": base64.b64encode(b"generated").decode()}]}
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "result.png"
                args = module.build_parser().parse_args([
                    "generate",
                    "--api-key", "local-test-key",
                    "--base-url", f"http://127.0.0.1:{server.server_port}",
                    "--prompt", "orange cat",
                    "--out", str(output),
                ])
                with mock.patch("builtins.print"):
                    self.assertEqual(module.run_image(args, edit=False), 0)
                self.assertEqual(output.read_bytes(), b"generated")
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

        self.assertEqual(received["path"], "/v1/images/generations")
        self.assertEqual(received["authorization"], "Bearer local-test-key")
        self.assertEqual(received["body"]["model"], "gpt-image-2")


if __name__ == "__main__":
    unittest.main()
