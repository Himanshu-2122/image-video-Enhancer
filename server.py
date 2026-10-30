#!/usr/bin/env python3
"""
EliteBabes.com Clone & Real-Time AI Image Enhancer Server
Provides real-time folder scanning, dHash burst deduplication, visual similarity search,
SSE live file watching, SQLite metadata & custom presets, Portrait AI (eye pop, f/1.4 bokeh,
auto-exposure/WB, smart framing), 3D .cube LUT grading, batch 4K ZIP export,
AI best-frame video scanner, and animated WebP loop extraction.
"""

import json
import mimetypes
import queue
import shutil
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List

from enhancer_engine import (
    AIImageEnhancerEngine,
    PRESET_CONFIGS,
    SUPPORTED_EXTENSIONS,
    VIDEO_PREVIEW_CACHE_DIR,
)

STATIC_DIR = Path("/home/himanshu/Projects/image-shower/static")
engine = AIImageEnhancerEngine()

_sse_clients_lock = threading.Lock()
_sse_clients: List[queue.Queue] = []


def broadcast_sse(event_type: str, payload: dict):
    msg = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n".encode("utf-8")
    with _sse_clients_lock:
        stale = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except Exception:
                stale.append(q)
        for q in stale:
            _sse_clients.remove(q)


def folder_watcher_loop():
    """Monitor active source folder in real time and push SSE updates when files change."""
    last_snapshot = None
    last_dir = None
    while True:
        try:
            cur_dir = engine.source_dir
            if cur_dir.exists():
                files = sorted(
                    [
                        (f.name, f.stat().st_mtime_ns, f.stat().st_size)
                        for f in cur_dir.iterdir()
                        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
                    ]
                )
                snapshot = (str(cur_dir), tuple(files))
                if last_snapshot is not None and snapshot != last_snapshot and cur_dir == last_dir:
                    engine._meta_cache.clear()
                    broadcast_sse(
                        "folder_changed",
                        {
                            "source_folder": str(cur_dir),
                            "count": len(files),
                            "timestamp": int(time.time()),
                        },
                    )
                last_snapshot = snapshot
                last_dir = cur_dir
        except Exception as exc:
            print(f"[Watcher] Warning: {exc}")
        time.sleep(2.0)


def prewarm_thumbnails():
    """Prune stale disk caches and warm lightweight metadata & a couple of thumbnails."""
    try:
        engine.prune_disk_caches()
        items = engine.scan_folder()
        for item in items[:8]:
            engine.get_thumbnail(item["id"])
        # Warm only 2 transparent cutouts lazily so startup RAM stays minimal
        engine.prewarm_nobg_cache(count=2)
    except Exception as exc:
        print(f"[Prewarm] Prewarm warning: {exc}")


class EliteBabesRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"[Engine HTTP] {self.address_string()} - {fmt % args}")

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _send_bytes(
        self,
        data: bytes,
        content_type: str,
        download_name: str = "",
        cache_seconds: int = 0,
    ):
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            if cache_seconds > 0:
                self.send_header("Cache-Control", f"public, max-age={cache_seconds}")
            else:
                self.send_header("Cache-Control", "no-store")
            if download_name:
                safe_name = download_name.replace('"', "")
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _send_file(self, file_path: Path, download_name: str = "", cache_seconds: int = 3600):
        if not file_path or not file_path.exists():
            self._send_json({"error": "File not found"}, 404)
            return

        try:
            st = file_path.stat()
        except OSError:
            self._send_json({"error": "File not found"}, 404)
            return

        etag = f'W/"{st.st_mtime_ns:x}-{st.st_size:x}"'
        if cache_seconds > 0 and not download_name:
            inm = self.headers.get("If-None-Match")
            if inm and inm == etag:
                try:
                    self.send_response(304)
                    self.send_header("ETag", etag)
                    self.send_header("Cache-Control", f"public, max-age={cache_seconds}")
                    self.end_headers()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return

        ctype, _ = mimetypes.guess_type(str(file_path))
        if not ctype:
            ctype = "application/octet-stream"

        try:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(st.st_size))
            self.send_header("ETag", etag)
            if cache_seconds > 0:
                self.send_header("Cache-Control", f"public, max-age={cache_seconds}")
            else:
                self.send_header("Cache-Control", "no-store")
            if download_name:
                safe_name = download_name.replace('"', "")
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name}"')
            self.end_headers()

            with open(file_path, "rb") as f:
                shutil.copyfileobj(f, self.wfile, length=65536)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _parse_enhance_params(self, qs: dict) -> dict:
        custom_params = {}
        for param_key in (
            "skin_smooth",
            "detail_sharpen",
            "micro_contrast",
            "depth_shadows",
            "warmth",
            "vibrance",
            "highlight_bloom",
            "eye_enhance",
            "bokeh_blur",
            "film_grain",
            "vignette",
            "preset_intensity",
        ):
            if param_key in qs:
                try:
                    custom_params[param_key] = float(qs[param_key][0])
                except ValueError:
                    pass
        for b_key in (
            "skin_mask_aware",
            "auto_exposure_wb",
            "is_monochrome",
            "vintage_bw_tint",
            "retro_film",
            "neon_pop",
            "pencil_sketch",
            "pro_pencil_sketch",
            "traumatized_mode",
        ):
            if b_key in qs:
                custom_params[b_key] = qs[b_key][0] in ("1", "true", "True")
        for s_key in ("upscale_mode", "lut_name", "crop_aspect"):
            if s_key in qs and qs[s_key][0]:
                custom_params[s_key] = qs[s_key][0]
        return custom_params

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # 0. Server-Sent Events (SSE) for real-time folder watching
        if path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            q: queue.Queue = queue.Queue(maxsize=32)
            with _sse_clients_lock:
                _sse_clients.append(q)
            try:
                init_msg = (
                    f"event: connected\ndata: {json.dumps({'folder': str(engine.source_dir)})}\n\n".encode(
                        "utf-8"
                    )
                )
                self.wfile.write(init_msg)
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=15.0)
                        self.wfile.write(msg)
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except Exception:
                pass
            finally:
                with _sse_clients_lock:
                    if q in _sse_clients:
                        _sse_clients.remove(q)
            return

        # 1. API: Real-time folder scan, search, dHash deduplication & visual similarity
        if path == "/api/images":
            q = qs.get("q", [""])[0]
            category = qs.get("category", [""])[0]
            model = qs.get("model", [""])[0]
            min_rating = int(qs.get("min_rating", ["0"])[0] or 0)
            dedup = qs.get("deduplicate", ["0"])[0] in ("1", "true", "True")
            only_uploaded = qs.get("uploaded", ["0"])[0] in ("1", "true", "True")
            similar_to = qs.get("similar_to", [""])[0]
            shuffle_mode = qs.get("shuffle", ["0"])[0] in ("1", "true", "True")

            all_items = engine.scan_folder()
            if q or category or model or min_rating > 0 or dedup or only_uploaded or similar_to or shuffle_mode:
                filtered_items = engine.scan_folder(
                    search_query=q,
                    category_filter=category,
                    model_filter=model,
                    only_uploaded=only_uploaded,
                    min_rating=min_rating,
                    deduplicate=dedup,
                    similar_to=similar_to,
                    shuffle=shuffle_mode,
                )
            else:
                filtered_items = all_items

            categories = sorted(list({it["category"] for it in all_items}))
            models = sorted(list({it["model"] for it in all_items}))
            dup_hidden_count = sum(1 for it in all_items if not it.get("is_sharpest_in_group", True))
            uploaded_count = sum(1 for it in all_items if it.get("is_uploaded", False))

            self._send_json(
                {
                    "status": "ok",
                    "source_folder": str(engine.source_dir),
                    "recursive": engine.recursive_scan,
                    "total_in_folder": len(all_items),
                    "matched_count": len(filtered_items),
                    "dup_hidden_count": dup_hidden_count,
                    "uploaded_count": uploaded_count,
                    "query": q,
                    "similar_to": similar_to,
                    "categories": categories,
                    "models": models,
                    "presets": {k: v["name"] for k, v in PRESET_CONFIGS.items()},
                    "preset_configs": PRESET_CONFIGS,
                    "luts": engine.list_luts(),
                    "images": filtered_items,
                }
            )
            return

        # 1B. API: Presets
        if path == "/api/presets":
            self._send_json({"status": "ok", "presets": PRESET_CONFIGS})
            return

        # 1C. API: Moodboards & collections
        if path == "/api/boards":
            self._send_json({"status": "ok", "boards": engine.list_boards()})
            return

        if path.startswith("/api/boards/") and path.endswith("/items"):
            board_id = path[len("/api/boards/") : -len("/items")].strip("/")
            self._send_json({"status": "ok", "board_id": board_id, "items": engine.get_board_items(board_id)})
            return

        # 2. API: List available folders
        if path == "/api/folders":
            self._send_json(
                {
                    "status": "ok",
                    "active_folder": str(engine.source_dir),
                    "recursive": engine.recursive_scan,
                    "folders": engine.list_available_folders(),
                }
            )
            return

        # 3. API: List local videos for Video Frame Extractor
        if path == "/api/videos":
            self._send_json(
                {
                    "status": "ok",
                    "videos": engine.list_videos(),
                }
            )
            return

        # 4. API: AI Best-Frame Scanner for a video
        if path.startswith("/api/video/best-frames/"):
            vid_id = path.split("/api/video/best-frames/", 1)[1].strip("/")
            best_frames = engine.scan_video_best_frames(vid_id)
            self._send_json(
                {
                    "status": "ok",
                    "video_id": vid_id,
                    "best_frames": best_frames,
                }
            )
            return

        # 4B. API: Video Scene Cut Detection
        if path.startswith("/api/video/scenes/"):
            vid_id = path.split("/api/video/scenes/", 1)[1].strip("/")
            scenes = engine.scan_video_scenes(vid_id)
            self._send_json({"status": "ok", "video_id": vid_id, "scenes": scenes})
            return

        # 4C. API: 10s–60s Video Clip Preset Conversion Job Status
        if path.startswith("/api/video/clip-status/"):
            job_id = path.split("/api/video/clip-status/", 1)[1].strip("/")
            job_info = engine.get_video_clip_job_status(job_id)
            if not job_info:
                self._send_json({"status": "error", "error": "Clip job not found"}, 404)
                return
            self._send_json({"status": "ok", "job": job_info})
            return

        # 4D. API: Stream or Download Converted 10s–60s Preset MP4 Video Clip
        if path.startswith("/api/video/clip-file/"):
            job_id = path.split("/api/video/clip-file/", 1)[1].strip("/")
            clip_path = engine.get_video_clip_file(job_id)
            if not clip_path or not clip_path.exists():
                self._send_json({"error": "Converted video clip not found"}, 404)
                return
            dl = qs.get("download", ["0"])[0] == "1"
            dl_name = clip_path.name if dl else ""
            self._send_file(clip_path, download_name=dl_name, cache_seconds=300)
            return

        # 5. API: Preview video frame at timestamp
        if path.startswith("/api/video/frame/"):
            vid_id = path.split("/api/video/frame/", 1)[1].strip("/")
            ts = float(qs.get("t", ["0.0"])[0] or 0.0)
            frame_path = engine.preview_video_frame(vid_id, ts)
            if not frame_path:
                self._send_json({"error": "Could not decode video frame"}, 404)
                return
            self._send_file(frame_path, cache_seconds=60)
            return

        # 6. API: Batch ZIP Export of 4K Enhanced Images
        if path == "/api/export-zip":
            ids_str = qs.get("ids", [""])[0]
            preset = qs.get("preset", ["ultra_hot_4k"])[0]
            fmt = qs.get("format", ["jpg"])[0].lower()
            if ids_str:
                img_ids = [x.strip() for x in ids_str.split(",") if x.strip()]
            else:
                img_ids = [it["id"] for it in engine.scan_folder()]

            zip_path = engine.create_batch_zip_file(img_ids, preset=preset, out_format=fmt)
            dl_name = f"EliteBabes_4K_Batch_{preset}_{len(img_ids)}imgs.zip"
            try:
                self._send_file(zip_path, download_name=dl_name, cache_seconds=0)
            finally:
                zip_path.unlink(missing_ok=True)
            return

        # 7. API: Trigger & inspect AI enhancement metadata in real-time
        if path.startswith("/api/enhance/"):
            img_id = path.split("/api/enhance/", 1)[1].strip("/")
            preset = qs.get("preset", ["ultra_hot_4k"])[0]
            out_fmt = qs.get("format", ["jpg"])[0].lower()
            custom_params = self._parse_enhance_params(qs)

            out_path, report = engine.enhance_image(
                img_id,
                preset=preset,
                custom_params=custom_params or None,
                out_format=out_fmt,
            )
            if not out_path:
                self._send_json({"error": "Image ID not found"}, 404)
                return

            meta = engine.get_image_by_id(img_id)
            q_parts = [f"preset={urllib.parse.quote(preset)}", f"format={urllib.parse.quote(out_fmt)}"]
            for k, v in custom_params.items():
                if isinstance(v, float):
                    q_parts.append(f"{k}={v:.2f}")
                elif isinstance(v, bool):
                    q_parts.append(f"{k}={'1' if v else '0'}")
                else:
                    q_parts.append(f"{k}={urllib.parse.quote(str(v))}")
            query_suffix = "?" + "&".join(q_parts)

            self._send_json(
                {
                    "status": "enhanced",
                    "image": meta,
                    "report": report,
                    "enhanced_image_url": f"/api/image/enhanced/{img_id}{query_suffix}",
                    "download_url": f"/api/image/enhanced/{img_id}{query_suffix}&download=1",
                }
            )
            return

        # 8. Serve original image
        if path.startswith("/api/image/original/"):
            img_id = path.split("/api/image/original/", 1)[1].strip("/")
            meta = engine.get_image_by_id(img_id)
            if not meta:
                self._send_json({"error": "Original image not found"}, 404)
                return
            src_path = engine.source_dir / meta["filename"]
            dl = qs.get("download", ["0"])[0] == "1"
            dl_name = f"Original_{Path(meta['filename']).name}" if dl else ""
            self._send_file(src_path, download_name=dl_name)
            return

        # 8B. Serve Exact-Fit Resizer Engine image (No Zoom-In / No Zoom-Out / Zero Crop)
        if path.startswith("/api/resize/"):
            img_id = path.split("/api/resize/", 1)[1].strip("/")
            tw = int(qs.get("w", ["0"])[0] or 0)
            th = int(qs.get("h", ["0"])[0] or 0)
            mode = qs.get("mode", ["exact_uploaded"])[0]
            out_path, _ = engine.resize_image_exact(img_id, target_w=tw, target_h=th, mode=mode)
            if not out_path:
                self._send_json({"error": "Image not found"}, 404)
                return
            self._send_file(out_path)
            return

        # 9. Serve thumbnail
        if path.startswith("/api/image/thumb/"):
            img_id = path.split("/api/image/thumb/", 1)[1].strip("/")
            thumb_path = engine.get_thumbnail(img_id)
            self._send_file(thumb_path)
            return

        # 10. Serve AI-Enhanced 4K+ image
        if path.startswith("/api/image/enhanced/"):
            img_id = path.split("/api/image/enhanced/", 1)[1].strip("/")
            preset = qs.get("preset", ["ultra_hot_4k"])[0]
            out_fmt = qs.get("format", ["jpg"])[0].lower()
            if out_fmt not in ("jpg", "png", "webp"):
                out_fmt = "jpg"
            custom_params = self._parse_enhance_params(qs)

            out_path, _ = engine.enhance_image(
                img_id,
                preset=preset,
                custom_params=custom_params or None,
                out_format=out_fmt,
            )
            meta = engine.get_image_by_id(img_id)
            dl = qs.get("download", ["0"])[0] == "1"
            dl_name = ""
            if dl and meta:
                stem = Path(meta["filename"]).stem
                dl_name = f"EliteBabes_4K_Enhanced_{stem}_{preset}.{out_fmt}"
            self._send_file(out_path, download_name=dl_name, cache_seconds=300)
            return

        # 10B. Serve Side-by-Side Comparison Animated WebP Loop
        if path.startswith("/api/image/compare-loop/"):
            img_id = path.split("/api/image/compare-loop/", 1)[1].strip("/")
            preset = qs.get("preset", ["ultra_hot_4k"])[0]
            loop_path = engine.create_comparison_loop(img_id, preset)
            if not loop_path or not loop_path.exists():
                self._send_json({"error": "Failed to create comparison loop"}, 404)
                return
            dl = qs.get("download", ["0"])[0] == "1"
            dl_name = f"EliteBabes_Compare_Loop_{img_id}_{preset}.webp" if dl else ""
            self._send_file(loop_path, download_name=dl_name, cache_seconds=300)
            return

        # 10C. API: Random clean background-removed subject
        if path == "/api/image/nobg-random":
            exclude = qs.get("exclude", [""])[0]
            item = engine.get_random_nobg(exclude_id=exclude)
            if not item:
                self._send_json({"error": "No background-removed subjects available"}, 404)
                return
            self._send_json({"status": "ok", "subject": item})
            return

        # 10D. Serve transparent background-removed subject PNG (HD 1080p+ default)
        if path.startswith("/api/image/nobg/"):
            img_id = path.split("/api/image/nobg/", 1)[1].strip("/")
            dim = int(qs.get("dim", ["1080"])[0] or 1080)
            nobg_path = engine.remove_background(img_id, max_dim=dim)
            if not nobg_path or not nobg_path.exists():
                self._send_json({"error": "Failed to remove background"}, 404)
                return
            self._send_file(nobg_path, cache_seconds=3600)
            return

        # 11. Serve static frontend files
        if path == "/" or path == "/index.html":
            self._send_file(STATIC_DIR / "index.html", cache_seconds=0)
            return

        rel_path = path.lstrip("/")
        static_file = (STATIC_DIR / rel_path).resolve()
        if str(static_file).startswith(str(STATIC_DIR.resolve())) and static_file.is_file():
            self._send_file(static_file, cache_seconds=0)
            return

        self._send_json({"error": "Route not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        # 0. Media File Ingestion Upload directly to source folder (chunked stream + validation)
        if path == "/api/upload":
            raw_len = int(self.headers.get("Content-Length", 0) or 0)
            if raw_len <= 0:
                self._send_json({"status": "error", "error": "No file data received"}, 400)
                return

            raw_name = urllib.parse.unquote(self.headers.get("X-Filename", "") or qs.get("filename", [""])[0])
            if not raw_name:
                raw_name = f"upload_{int(time.time())}.jpg"
            model_hdr = urllib.parse.unquote(self.headers.get("X-Model", "") or qs.get("model", [""])[0])
            cat_hdr = urllib.parse.unquote(self.headers.get("X-Category", "") or qs.get("category", ["Uploaded"])[0]) or "Uploaded"
            title_hdr = urllib.parse.unquote(self.headers.get("X-Title", "") or qs.get("title", [""])[0])
            tags_hdr = urllib.parse.unquote(self.headers.get("X-Tags", "") or qs.get("tags", [""])[0])
            preset_hdr = urllib.parse.unquote(self.headers.get("X-Preset", "") or qs.get("preset", ["ultra_hot_4k"])[0]) or "ultra_hot_4k"
            auto_enh = (self.headers.get("X-Auto-Enhance", "0") or qs.get("auto_enhance", ["0"])[0]) in ("1", "true", "True")

            ctype = self.headers.get("Content-Type", "")
            tmp_path = VIDEO_PREVIEW_CACHE_DIR / f"upload_tmp_{int(time.time() * 1000)}_{threading.get_ident()}.bin"

            try:
                if "multipart/form-data" in ctype and "boundary=" in ctype:
                    # Handle standard multipart/form-data upload
                    raw_body = self.rfile.read(raw_len)
                    boundary = ctype.split("boundary=", 1)[1].split(";")[0].strip().encode("utf-8")
                    parts = raw_body.split(b"--" + boundary)
                    file_bytes = b""
                    for part in parts:
                        if b"Content-Disposition:" not in part or b"\r\n\r\n" not in part:
                            continue
                        hdr_block, content = part.split(b"\r\n\r\n", 1)
                        if content.endswith(b"\r\n"):
                            content = content[:-2]
                        hdr_str = hdr_block.decode("utf-8", errors="ignore")
                        if 'filename="' in hdr_str:
                            fn_extract = hdr_str.split('filename="', 1)[1].split('"', 1)[0]
                            if fn_extract:
                                raw_name = fn_extract
                            file_bytes = content
                            break
                    if not file_bytes:
                        self._send_json({"status": "error", "error": "No image part found in form data"}, 400)
                        return
                    tmp_path.write_bytes(file_bytes)
                else:
                    # Stream raw binary body in 64KB chunks
                    remaining = raw_len
                    with open(tmp_path, "wb") as f_out:
                        while remaining > 0:
                            chunk = self.rfile.read(min(65536, remaining))
                            if not chunk:
                                break
                            f_out.write(chunk)
                            remaining -= len(chunk)

                tag_list = [t.strip() for t in tags_hdr.split(",") if t.strip()] if tags_hdr else []
                ok, item_meta, err_msg = engine.ingest_uploaded_image(
                    tmp_path=tmp_path,
                    original_filename=raw_name,
                    model=model_hdr,
                    category=cat_hdr,
                    title=title_hdr,
                    tags=tag_list,
                    auto_enhance=auto_enh,
                    preset=preset_hdr,
                )
                if not ok or not item_meta:
                    self._send_json({"status": "error", "error": err_msg or "Failed to process uploaded image"}, 400)
                    return

                broadcast_sse(
                    "folder_changed",
                    {
                        "source_folder": str(engine.source_dir),
                        "new_image_id": item_meta["id"],
                        "timestamp": int(time.time()),
                    },
                )
                self._send_json(
                    {
                        "status": "ok",
                        "filename": item_meta["filename"],
                        "id": item_meta["id"],
                        "image": item_meta,
                    }
                )
            finally:
                tmp_path.unlink(missing_ok=True)
            return

        # 0B. Video Clip Upload directly to Video Studio (chunked stream)
        if path == "/api/video/upload":
            raw_len = int(self.headers.get("Content-Length", 0) or 0)
            if raw_len <= 0:
                self._send_json({"status": "error", "error": "No video data received"}, 400)
                return
            raw_name = urllib.parse.unquote(self.headers.get("X-Filename", "") or qs.get("filename", [""])[0])
            if not raw_name:
                raw_name = f"clip_{int(time.time())}.mp4"
            tmp_path = VIDEO_PREVIEW_CACHE_DIR / f"vupload_tmp_{int(time.time() * 1000)}_{threading.get_ident()}.bin"
            try:
                remaining = raw_len
                with open(tmp_path, "wb") as f_out:
                    while remaining > 0:
                        chunk = self.rfile.read(min(65536, remaining))
                        if not chunk:
                            break
                        f_out.write(chunk)
                        remaining -= len(chunk)
                ok, vinfo, err_msg = engine.ingest_uploaded_video(tmp_path, raw_name)
                if not ok or not vinfo:
                    self._send_json({"status": "error", "error": err_msg or "Invalid video file"}, 400)
                    return
                self._send_json({"status": "ok", "video": vinfo, "videos": engine.list_videos()})
            finally:
                tmp_path.unlink(missing_ok=True)
            return

        body = self._read_json_body()

        # 1. Update persistent SQLite metadata
        if path.startswith("/api/metadata/"):
            img_id = path.split("/api/metadata/", 1)[1].strip("/")
            updated = engine.update_image_metadata(img_id, body)
            if not updated:
                self._send_json({"error": "Image not found"}, 404)
                return
            self._send_json({"status": "ok", "image": updated})
            return

        # 2. Save custom preset
        if path == "/api/presets":
            name = str(body.get("name", "Custom 4K Preset"))
            params = body.get("params", {})
            key, cfg = engine.save_custom_preset(name, params)
            self._send_json(
                {
                    "status": "ok",
                    "preset_key": key,
                    "preset": cfg,
                    "preset_configs": PRESET_CONFIGS,
                }
            )
            return

        # 2B. Batch 4K Enhancement
        if path == "/api/batch/enhance":
            image_ids = body.get("image_ids", [])
            preset = str(body.get("preset", "ultra_hot_4k"))
            params = body.get("params")
            fmt = str(body.get("format", "jpg"))
            if not image_ids and body.get("all", False):
                image_ids = [it["id"] for it in engine.scan_folder()]
            res = engine.batch_enhance(image_ids, preset=preset, custom_params=params, out_format=fmt)
            self._send_json({"status": "ok", "result": res})
            return

        # 3. Switch active source directory
        if path == "/api/source-folder":
            folder_path = str(body.get("path", "")).strip()
            recursive = bool(body.get("recursive", False))
            ok, msg = engine.set_source_dir(folder_path, recursive=recursive)
            if not ok:
                self._send_json({"status": "error", "error": msg}, 400)
                return
            broadcast_sse("folder_changed", {"source_folder": msg, "timestamp": int(time.time())})
            self._send_json(
                {
                    "status": "ok",
                    "source_folder": msg,
                    "recursive": engine.recursive_scan,
                    "folders": engine.list_available_folders(),
                }
            )
            return

        # 4. Extract video keyframe and enhance to 4K
        if path == "/api/video/extract":
            vid_id = str(body.get("video_id", "")).strip()
            ts = float(body.get("timestamp", 0.0) or 0.0)
            preset = str(body.get("preset", "ultra_hot_4k"))
            new_item = engine.extract_video_frame_to_gallery(vid_id, ts, preset=preset)
            if not new_item:
                self._send_json({"status": "error", "error": "Failed to extract video frame"}, 400)
                return
            broadcast_sse(
                "folder_changed",
                {
                    "source_folder": str(engine.source_dir),
                    "new_image_id": new_item["id"],
                    "timestamp": int(time.time()),
                },
            )
            self._send_json({"status": "ok", "image": new_item})
            return

        # 5. Extract animated 4K WebP loop from video
        if path == "/api/video/extract-loop":
            vid_id = str(body.get("video_id", "")).strip()
            ts = float(body.get("timestamp", 0.0) or 0.0)
            preset = str(body.get("preset", "ultra_hot_4k"))
            new_item = engine.extract_video_loop_to_gallery(vid_id, ts, duration_sec=2.4, preset=preset)
            if not new_item:
                self._send_json({"status": "error", "error": "Failed to extract animated loop"}, 400)
                return
            broadcast_sse(
                "folder_changed",
                {
                    "source_folder": str(engine.source_dir),
                    "new_image_id": new_item["id"],
                    "timestamp": int(time.time()),
                },
            )
            self._send_json({"status": "ok", "image": new_item})
            return

        # 5B. Convert 10s–60s Video Clip into any of the 14 AI Presets (MP4 + Audio + Temporal EMA)
        if path == "/api/video/convert-clip":
            vid_id = str(body.get("video_id", "")).strip()
            ts = float(body.get("timestamp", 0.0) or 0.0)
            duration_sec = float(body.get("duration_sec", 15.0) or 15.0)
            preset = str(body.get("preset", "ultra_hot_4k"))
            raw_res = body.get("resolution_p", 0)
            resolution_p = int(raw_res) if raw_res is not None and str(raw_res) != "" else 0
            raw_fps = body.get("fps", 0)
            fps_out = int(raw_fps) if raw_fps is not None and str(raw_fps) != "" else 0
            ok, job_info, err_msg = engine.start_video_clip_preset_job(
                vid_id=vid_id,
                start_sec=ts,
                duration_sec=duration_sec,
                preset=preset,
                resolution_p=resolution_p,
                fps_out=fps_out,
            )
            if not ok:
                self._send_json({"status": "error", "error": err_msg or "Failed to start clip conversion"}, 400)
                return
            self._send_json({"status": "ok", "job": job_info})
            return

        # 5C. Cancel ongoing video preset conversion job
        if path == "/api/video/cancel-clip" or path.startswith("/api/video/cancel-clip/"):
            job_id = str(body.get("job_id", "")).strip() or path.split("/api/video/cancel-clip/", 1)[-1].strip("/")
            ok = engine.cancel_video_job(job_id)
            self._send_json({"status": "ok" if ok else "error", "cancelled": ok})
            return

        # 6. Boards: create new moodboard
        if path == "/api/boards":
            name = str(body.get("name", "New Moodboard")).strip()
            desc = str(body.get("description", "")).strip()
            board = engine.create_board(name, desc)
            self._send_json({"status": "ok", "board": board})
            return

        # 7. Boards: add image to moodboard
        if path.startswith("/api/boards/") and path.endswith("/items"):
            board_id = path[len("/api/boards/") : -len("/items")].strip("/")
            img_id = str(body.get("img_id", "")).strip()
            if not img_id:
                self._send_json({"error": "Missing img_id"}, 400)
                return
            ok = engine.add_to_board(board_id, img_id)
            self._send_json({"status": "ok" if ok else "error"})
            return

        self._send_json({"error": "POST route not found"}, 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/presets/"):
            preset_key = path.split("/api/presets/", 1)[1].strip("/")
            ok = engine.delete_custom_preset(preset_key)
            if not ok:
                self._send_json({"error": "Cannot delete preset"}, 400)
                return
            self._send_json({"status": "ok", "preset_configs": PRESET_CONFIGS})
            return

        if "/api/boards/" in path and "/items/" in path:
            parts = path.split("/api/boards/", 1)[1].split("/items/", 1)
            board_id = parts[0].strip("/")
            img_id = parts[1].strip("/")
            ok = engine.remove_from_board(board_id, img_id)
            self._send_json({"status": "ok" if ok else "error"})
            return

        if path.startswith("/api/boards/"):
            board_id = path.split("/api/boards/", 1)[1].strip("/")
            ok = engine.delete_board(board_id)
            self._send_json({"status": "ok" if ok else "error"})
            return

        self._send_json({"error": "DELETE route not found"}, 404)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_server(host: str = "0.0.0.0", port: int = 8765):
    threading.Thread(target=prewarm_thumbnails, daemon=True).start()
    threading.Thread(target=folder_watcher_loop, daemon=True).start()
    try:
        server = ReusableThreadingHTTPServer((host, port), EliteBabesRequestHandler)
    except OSError as exc:
        if exc.errno == 98:
            for alt_port in range(port + 1, port + 20):
                try:
                    server = ReusableThreadingHTTPServer((host, alt_port), EliteBabesRequestHandler)
                    print(f"[Server] Port {port} was busy; automatically bound to port {alt_port}")
                    port = alt_port
                    break
                except OSError:
                    continue
            else:
                raise
        else:
            raise
    print(f"============================================================")
    print(f" EliteBabes.com Clone & AI Image Enhancer Engine ACTIVE")
    print(f" Local Source Folder : {engine.source_dir}")
    print(f" Web Interface URL   : http://{host}:{port}")
    print(f" Privacy Mode        : 100% Local (Zero External Uploads)")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down cleanly...")
        server.server_close()


if __name__ == "__main__":
    import os
    import sys

    cli_port = int(os.environ.get("PORT", "8765"))
    for arg in sys.argv[1:]:
        if arg.isdigit():
            cli_port = int(arg)
            break
        if arg.startswith("--port="):
            try:
                cli_port = int(arg.split("=", 1)[1])
                break
            except ValueError:
                pass
    run_server(port=cli_port)
