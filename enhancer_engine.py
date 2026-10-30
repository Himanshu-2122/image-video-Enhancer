#!/usr/bin/env python3
"""
EliteBabes Reverse-Engineered AI Image Enhancer Engine
Core scanning, SQLite metadata persistence, 3D .cube LUT grading, skin-mask aware
frequency separation, eye & catchlight enhancement, bokeh depth-of-field blur,
auto-exposure/WB, aspect-ratio smart framing, dHash duplicate detection,
visual similarity search, AI best-frame video scanner, animated WebP loop enhancer,
and batch ZIP export. Strictly operates on local files with 100% privacy.
"""

import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

VIDEOS_ROOT_DIR = Path("/home/himanshu/Videos")
SOURCE_IMAGE_DIR = Path("/home/himanshu/Videos/img")
PROJECT_DIR = Path("/home/himanshu/Projects/image-shower")
CACHE_DIR = PROJECT_DIR / ".cache"
THUMB_CACHE_DIR = CACHE_DIR / "thumbs"
ENHANCED_CACHE_DIR = CACHE_DIR / "enhanced"
VIDEO_PREVIEW_CACHE_DIR = CACHE_DIR / "video_previews"
VIDEO_CLIPS_CACHE_DIR = CACHE_DIR / "video_clips"
UPLOADED_VIDEOS_DIR = CACHE_DIR / "uploaded_videos"
NOBG_CACHE_DIR = CACHE_DIR / "nobg"
LUTS_DIR = PROJECT_DIR / "luts"
MODELS_DIR = PROJECT_DIR / "models"
SILUETA_MODEL_PATH = MODELS_DIR / "silueta.onnx"
U2NETP_MODEL_PATH = MODELS_DIR / "u2netp.onnx"
YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
REALESRGAN_MODEL_PATH = MODELS_DIR / "realesr-general-x4v3.onnx"
DB_PATH = CACHE_DIR / "elitebabes_meta.db"

CACHE_MAX_ENHANCED_BYTES = 180 * 1024 * 1024  # Cap .cache/enhanced at 180 MB (LRU auto-prune)
CACHE_MAX_PREVIEWS_BYTES = 35 * 1024 * 1024   # Cap .cache/video_previews at 35 MB
CACHE_MAX_THUMBS_BYTES = 50 * 1024 * 1024     # Cap .cache/thumbs at 50 MB
CACHE_MAX_CLIPS_BYTES = 160 * 1024 * 1024     # Cap .cache/video_clips at 160 MB

try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}

PRESET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "real_esrgan_master": {
        "name": "AI Real-ESRGAN Deep 4K",
        "icon": "🤖",
        "category": "Master Flagship",
        "desc": "Deep neural super-resolution + YuNet eye pop & natural pore preservation",
        "target_long_edge": 3840,
        "skin_smooth": 0.50,
        "detail_sharpen": 1.45,
        "micro_contrast": 1.25,
        "depth_shadows": 1.15,
        "warmth": 1.05,
        "vibrance": 1.15,
        "highlight_bloom": 0.12,
        "eye_enhance": 0.65,
        "bokeh_blur": 0.0,
        "film_grain": 0.0,
        "vignette": 0.0,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": True,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "real_esrgan_ai",
        "lut_name": "Crisp_Studio_Daylight.cube",
        "builtin": True,
    },
    "ultra_hot_4k": {
        "name": "Ultra-Hot 4K Premium",
        "icon": "🔥",
        "category": "Master Flagship",
        "desc": "4K upscale, radiant skin glow, eye catchlights & razor details",
        "target_long_edge": 3840,
        "skin_smooth": 0.45,
        "detail_sharpen": 1.55,
        "micro_contrast": 1.35,
        "depth_shadows": 1.25,
        "warmth": 1.12,
        "vibrance": 1.22,
        "highlight_bloom": 0.15,
        "eye_enhance": 0.45,
        "bokeh_blur": 0.0,
        "film_grain": 0.0,
        "vignette": 0.0,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "none",
        "builtin": True,
    },
    "skin_perfection": {
        "name": "Silk Skin & Glamour Glow",
        "icon": "✨",
        "category": "Portrait Glamour",
        "desc": "Frequency-separated skin smoothing + f/1.4 bokeh & golden studio glow",
        "target_long_edge": 3840,
        "skin_smooth": 0.70,
        "detail_sharpen": 1.35,
        "micro_contrast": 1.20,
        "depth_shadows": 1.15,
        "warmth": 1.18,
        "vibrance": 1.18,
        "highlight_bloom": 0.22,
        "eye_enhance": 0.60,
        "bokeh_blur": 0.25,
        "film_grain": 0.0,
        "vignette": 0.15,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": True,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "Golden_Hour_Glam.cube",
        "builtin": True,
    },
    "razor_sharp_hdr": {
        "name": "Razor-Sharp 4K+ HDR Depth",
        "icon": "💎",
        "category": "HDR & Clarity",
        "desc": "Maximum micro-contrast, 4096p IBP upscale, eye pop & 3D shadow depth",
        "target_long_edge": 4096,
        "skin_smooth": 0.25,
        "detail_sharpen": 1.85,
        "micro_contrast": 1.55,
        "depth_shadows": 1.40,
        "warmth": 1.06,
        "vibrance": 1.28,
        "highlight_bloom": 0.10,
        "eye_enhance": 0.75,
        "bokeh_blur": 0.0,
        "film_grain": 0.0,
        "vignette": 0.0,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "ibp_super_res",
        "lut_name": "Crisp_Studio_Daylight.cube",
        "builtin": True,
    },
    "cinema_noir": {
        "name": "Cinema Luxury & Deep Shadows",
        "icon": "🎬",
        "category": "Cinematic",
        "desc": "Filmic S-curve shadows, creamy bokeh, rich highlights & cinema LUT",
        "target_long_edge": 3840,
        "skin_smooth": 0.40,
        "detail_sharpen": 1.45,
        "micro_contrast": 1.45,
        "depth_shadows": 1.50,
        "warmth": 1.10,
        "vibrance": 1.15,
        "highlight_bloom": 0.18,
        "eye_enhance": 0.50,
        "bokeh_blur": 0.35,
        "film_grain": 0.12,
        "vignette": 0.25,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "Teal_Orange_Cinema.cube",
        "builtin": True,
    },
    "velvia_vivid": {
        "name": "Fuji Velvia & Vivid Color Pop",
        "icon": "🌈",
        "category": "Vibrant Editorial",
        "desc": "Punchy tropical greens, oceanic cyans, vibrant saturated tones & razor edge pop",
        "target_long_edge": 3840,
        "skin_smooth": 0.35,
        "detail_sharpen": 1.65,
        "micro_contrast": 1.45,
        "depth_shadows": 1.30,
        "warmth": 1.04,
        "vibrance": 1.45,
        "highlight_bloom": 0.12,
        "eye_enhance": 0.65,
        "bokeh_blur": 0.0,
        "film_grain": 0.05,
        "vignette": 0.10,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "none",
        "builtin": True,
    },
    "golden_hour_sunset": {
        "name": "Golden Hour Amber Radiance",
        "icon": "🌅",
        "category": "Warm Radiance",
        "desc": "Sun-kissed amber skin glow, warm specular highlights, soft bloom & creamy depth",
        "target_long_edge": 3840,
        "skin_smooth": 0.55,
        "detail_sharpen": 1.30,
        "micro_contrast": 1.25,
        "depth_shadows": 1.20,
        "warmth": 1.35,
        "vibrance": 1.25,
        "highlight_bloom": 0.35,
        "eye_enhance": 0.50,
        "bokeh_blur": 0.20,
        "film_grain": 0.08,
        "vignette": 0.20,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "Golden_Hour_Glam.cube",
        "builtin": True,
    },
    "monochrome_fine_art": {
        "name": "Fine Art Platinum B&W",
        "icon": "🖤",
        "category": "Monochrome Master",
        "desc": "Panchromatic silver halide tonality, rich deep blacks, radiant skin midtones",
        "target_long_edge": 3840,
        "skin_smooth": 0.38,
        "detail_sharpen": 1.80,
        "micro_contrast": 1.65,
        "depth_shadows": 1.55,
        "warmth": 1.00,
        "vibrance": 1.00,
        "highlight_bloom": 0.08,
        "eye_enhance": 0.70,
        "bokeh_blur": 0.0,
        "film_grain": 0.18,
        "vignette": 0.30,
        "preset_intensity": 1.0,
        "is_monochrome": True,
        "neon_pop": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "ibp_super_res",
        "lut_name": "none",
        "builtin": True,
    },
    "vintage_polaroid_1979": {
        "name": "35mm Analog Film & Organic Grain",
        "icon": "🎞️",
        "category": "Vintage Analog",
        "desc": "Authentic 35mm film grain, lifted matte shadows, nostalgic warmth & optical vignette",
        "target_long_edge": 3840,
        "skin_smooth": 0.30,
        "detail_sharpen": 1.25,
        "micro_contrast": 1.15,
        "depth_shadows": 1.10,
        "warmth": 1.18,
        "vibrance": 1.10,
        "highlight_bloom": 0.20,
        "eye_enhance": 0.40,
        "bokeh_blur": 0.15,
        "film_grain": 0.32,
        "vignette": 0.38,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "none",
        "builtin": True,
    },
    "cyberpunk_neon": {
        "name": "Tokyo Neon & Cyber Nightlife",
        "icon": "⚡",
        "category": "Editorial Neon",
        "desc": "Electric magenta/cyan split, deep midnight blacks, glowing neon specular reflections",
        "target_long_edge": 3840,
        "skin_smooth": 0.40,
        "detail_sharpen": 1.75,
        "micro_contrast": 1.60,
        "depth_shadows": 1.50,
        "warmth": 0.92,
        "vibrance": 1.55,
        "highlight_bloom": 0.40,
        "eye_enhance": 0.75,
        "bokeh_blur": 0.0,
        "film_grain": 0.08,
        "vignette": 0.25,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": True,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "Teal_Orange_Cinema.cube",
        "builtin": True,
    },
    "high_key_studio": {
        "name": "High-Key Porcelain Studio",
        "icon": "🕊️",
        "category": "Ethereal Beauty",
        "desc": "Airy illuminated studio lighting, porcelain skin tone, minimal shadow, dreamlike bloom",
        "target_long_edge": 3840,
        "skin_smooth": 0.75,
        "detail_sharpen": 1.20,
        "micro_contrast": 1.05,
        "depth_shadows": 0.92,
        "warmth": 0.98,
        "vibrance": 1.12,
        "highlight_bloom": 0.30,
        "eye_enhance": 0.55,
        "bokeh_blur": 0.25,
        "film_grain": 0.0,
        "vignette": 0.0,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "pencil_sketch": False,
        "auto_exposure_wb": True,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "Crisp_Studio_Daylight.cube",
        "builtin": True,
    },
    "pencil_sketch_master": {
        "name": "Master Graphite Pencil Sketch",
        "icon": "✏️",
        "category": "Fine-Art Sketch",
        "desc": "Realistic 2B/6B graphite shading, XDoG anatomical linework, directional cross-hatching & archival paper grain",
        "target_long_edge": 3840,
        "skin_smooth": 0.50,
        "detail_sharpen": 1.75,
        "micro_contrast": 1.50,
        "depth_shadows": 1.45,
        "warmth": 1.04,
        "vibrance": 1.00,
        "highlight_bloom": 0.0,
        "eye_enhance": 0.70,
        "bokeh_blur": 0.0,
        "film_grain": 0.18,
        "vignette": 0.16,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "pencil_sketch": True,
        "pro_pencil_sketch": False,
        "auto_exposure_wb": True,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "none",
        "builtin": True,
    },
    "pro_realistic_pencil": {
        "name": "Pro Realistic Pencil Portrait",
        "icon": "🖋️",
        "category": "Hyper-Realistic Sketch",
        "desc": "Photorealistic 2H–8B portrait likeness, Edge-Tangent Flow (ETF) directional strokes, 4-scale centered Retinex shading & kneaded-eraser catchlights",
        "target_long_edge": 3840,
        "skin_smooth": 0.42,
        "detail_sharpen": 1.85,
        "micro_contrast": 1.45,
        "depth_shadows": 1.35,
        "warmth": 1.01,
        "vibrance": 1.00,
        "highlight_bloom": 0.0,
        "eye_enhance": 0.85,
        "bokeh_blur": 0.0,
        "film_grain": 0.14,
        "vignette": 0.10,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "neon_pop": False,
        "pencil_sketch": True,
        "pro_pencil_sketch": True,
        "auto_exposure_wb": True,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "ibp_super_res",
        "lut_name": "none",
        "builtin": True,
    },
    "vintage_bw": {
        "name": "Vintage Black & White",
        "icon": "📽️",
        "category": "Vintage Monochrome",
        "desc": "Classic monochrome look with rich silver-gelatin contrast, archival tonal depth & subtle film grain",
        "target_long_edge": 3840,
        "skin_smooth": 0.40,
        "detail_sharpen": 1.55,
        "micro_contrast": 1.50,
        "depth_shadows": 1.40,
        "warmth": 1.04,
        "vibrance": 1.00,
        "highlight_bloom": 0.08,
        "eye_enhance": 0.65,
        "bokeh_blur": 0.0,
        "film_grain": 0.22,
        "vignette": 0.28,
        "preset_intensity": 1.0,
        "is_monochrome": True,
        "vintage_bw_tint": True,
        "retro_film": False,
        "neon_pop": False,
        "pencil_sketch": False,
        "pro_pencil_sketch": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "none",
        "builtin": True,
    },
    "retro": {
        "name": "Retro",
        "icon": "📻",
        "category": "Retro Analog",
        "desc": "Warm faded colors, lifted matte shadows, nostalgic split-toned highlights & subtle analog film effect",
        "target_long_edge": 3840,
        "skin_smooth": 0.35,
        "detail_sharpen": 1.30,
        "micro_contrast": 1.18,
        "depth_shadows": 1.08,
        "warmth": 1.16,
        "vibrance": 0.88,
        "highlight_bloom": 0.22,
        "eye_enhance": 0.45,
        "bokeh_blur": 0.10,
        "film_grain": 0.24,
        "vignette": 0.26,
        "preset_intensity": 1.0,
        "is_monochrome": False,
        "vintage_bw_tint": False,
        "retro_film": True,
        "neon_pop": False,
        "pencil_sketch": False,
        "pro_pencil_sketch": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "lanczos_edge",
        "lut_name": "Golden_Hour_Glam.cube",
        "builtin": True,
    },
    "traumatized": {
        "name": "TRAUMATIZED — Nightmare Mode",
        "icon": "💀",
        "category": "Uncanny Meme",
        "desc": "Viral Traumatized Mr. Incredible meme aesthetic: high-contrast nightmare monochrome, sunken eye shadows, dark facial shading & exaggerated wrinkles",
        "target_long_edge": 3840,
        "skin_smooth": 0.0,
        "detail_sharpen": 2.15,
        "micro_contrast": 1.95,
        "depth_shadows": 1.90,
        "warmth": 0.94,
        "vibrance": 0.0,
        "highlight_bloom": 0.04,
        "eye_enhance": 0.85,
        "bokeh_blur": 0.0,
        "film_grain": 0.32,
        "vignette": 0.58,
        "preset_intensity": 1.0,
        "is_monochrome": True,
        "traumatized_mode": True,
        "vintage_bw_tint": False,
        "retro_film": False,
        "neon_pop": False,
        "pencil_sketch": False,
        "pro_pencil_sketch": False,
        "auto_exposure_wb": False,
        "crop_aspect": "original",
        "skin_mask_aware": True,
        "upscale_mode": "ibp_super_res",
        "lut_name": "none",
        "builtin": True,
    },
}


class AIImageEnhancerEngine:
    """
    Core reverse-engineered enhancement, portrait intelligence, dHash deduplication,
    visual similarity, 3D LUT, and smart video extraction engine.
    """

    def __init__(self, source_dir: Path = SOURCE_IMAGE_DIR):
        self.source_dir = source_dir.resolve()
        self.recursive_scan = False
        self._db_lock = threading.Lock()
        THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ENHANCED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        VIDEO_PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        VIDEO_CLIPS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        UPLOADED_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        NOBG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        LUTS_DIR.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        self._meta_cache: Dict[str, Dict] = {}
        self._id_to_meta: Dict[str, Dict] = {}
        self._lut_cache: Dict[str, np.ndarray] = {}
        self._feature_cache: Dict[str, Dict[str, Any]] = {}
        self._video_list_cache: Optional[Tuple[float, List[Dict[str, Any]]]] = None
        self._video_clip_jobs: Dict[str, Dict[str, Any]] = {}
        self._video_clip_lock = threading.Lock()
        self._video_clip_sem = threading.BoundedSemaphore(1)
        self._nobg_lock = threading.Lock()
        self._enhance_sem = threading.BoundedSemaphore(2)
        self._ort_session = None
        self._ort_lock = threading.Lock()
        self._face_detector = None
        self._face_detector_lock = threading.Lock()
        self._realesrgan_session = None
        self._realesrgan_lock = threading.Lock()
        self._subject_mask_cache: Dict[str, np.ndarray] = {}

        self._init_db()
        self._ensure_default_luts()
        self._load_custom_presets_from_db()
        self._load_signatures_from_db()
        self.prune_disk_caches()

    def _get_ort_session(self):
        """Lazy-load high-precision Silueta (44MB) or U2NetP (4.5MB) ONNX session on first request."""
        if self._ort_session is not None:
            return self._ort_session
        if not HAS_ORT:
            return None
        with self._ort_lock:
            if self._ort_session is not None:
                return self._ort_session
            # Prefer high-precision Silueta for human portraits, fallback to U2NetP
            target_model = SILUETA_MODEL_PATH if SILUETA_MODEL_PATH.exists() else U2NETP_MODEL_PATH
            if target_model.exists():
                try:
                    opts = ort.SessionOptions()
                    opts.intra_op_num_threads = 2
                    opts.inter_op_num_threads = 1
                    opts.enable_mem_pattern = True
                    opts.enable_cpu_mem_arena = False
                    self._ort_session = ort.InferenceSession(
                        str(target_model), sess_options=opts, providers=["CPUExecutionProvider"]
                    )
                    print(f"[Engine] Lazy-loaded segmentation model: {target_model.name}")
                except Exception as exc:
                    print(f"[Engine] ONNX init warning: {exc}")
        return self._ort_session

    def _get_face_detector(self):
        """Lazy-load YuNet AI face and eye landmark detector."""
        if not HAS_CV2 or not hasattr(cv2, "FaceDetectorYN") or not YUNET_MODEL_PATH.exists():
            return None
        if self._face_detector is not None:
            return self._face_detector
        with self._face_detector_lock:
            if self._face_detector is not None:
                return self._face_detector
            try:
                self._face_detector = cv2.FaceDetectorYN.create(
                    str(YUNET_MODEL_PATH), "", (320, 320), score_threshold=0.55, nms_threshold=0.3
                )
                print("[Engine] Initialized YuNet AI Face & Eye Detector")
            except Exception as exc:
                print(f"[Engine] YuNet detector error: {exc}")
        return self._face_detector

    def _detect_faces_and_eyes(self, rgb: np.ndarray) -> List[Dict[str, Any]]:
        """Ultra-fast (15ms) YuNet face detection & 5-point landmark localization."""
        detector = self._get_face_detector()
        if detector is None:
            return []
        h, w = rgb.shape[:2]
        scale = min(1.0, 640.0 / max(w, h, 1))
        pw, ph = max(16, int(round(w * scale))), max(16, int(round(h * scale)))
        proxy = cv2.resize(rgb, (pw, ph), interpolation=cv2.INTER_AREA) if scale < 1.0 else rgb
        bgr = cv2.cvtColor(proxy, cv2.COLOR_RGB2BGR)

        with self._face_detector_lock:
            detector.setInputSize((pw, ph))
            _, faces = detector.detect(bgr)

        if faces is None or len(faces) == 0:
            return []

        inv_s = 1.0 / scale
        results = []
        for f in faces:
            box = (f[0:4] * inv_s).astype(int)
            r_eye = (f[4:6] * inv_s).astype(float)
            l_eye = (f[6:8] * inv_s).astype(float)
            nose = (f[8:10] * inv_s).astype(float)
            r_mouth = (f[10:12] * inv_s).astype(float)
            l_mouth = (f[12:14] * inv_s).astype(float)
            conf = float(f[14])
            results.append({
                "box": box,
                "right_eye": r_eye,
                "left_eye": l_eye,
                "nose": nose,
                "right_mouth": r_mouth,
                "left_mouth": l_mouth,
                "conf": conf,
            })
        return results

    def _get_subject_mask(self, rgb: np.ndarray) -> np.ndarray:
        """Extract 0.0-1.0 person silhouette foreground mask using Silueta ONNX model."""
        h, w = rgb.shape[:2]
        ort_sess = self._get_ort_session()
        if ort_sess is None:
            # Centered subject prior fallback
            cy, cx = h / 2.0, w / 2.0
            y_idx, x_idx = np.ogrid[:h, :w]
            dist = np.sqrt(((x_idx - cx) / (w * 0.42)) ** 2 + ((y_idx - cy) / (h * 0.46)) ** 2)
            return np.clip(1.0 - dist, 0.0, 1.0).astype(np.float32)

        try:
            disp = cv2.resize(rgb, (320, 320), interpolation=cv2.INTER_AREA)
            arr = disp.astype(np.float32) / 255.0
            arr[:, :, 0] = (arr[:, :, 0] - 0.485) / 0.229
            arr[:, :, 1] = (arr[:, :, 1] - 0.456) / 0.224
            arr[:, :, 2] = (arr[:, :, 2] - 0.406) / 0.225
            input_tensor = arr.transpose((2, 0, 1))[np.newaxis, ...].astype(np.float32)

            input_name = ort_sess.get_inputs()[0].name
            output_name = ort_sess.get_outputs()[0].name
            outputs = ort_sess.run([output_name], {input_name: input_tensor})
            raw_mask = outputs[0][0, 0, :, :]

            clean_alpha = np.clip((raw_mask - 0.25) / 0.50, 0.0, 1.0)
            clean_alpha = clean_alpha * clean_alpha * (3.0 - 2.0 * clean_alpha)
            clean_u8 = (clean_alpha * 255.0).astype(np.uint8)
            clean_u8 = cv2.bilateralFilter(clean_u8, 5, 30, 30)
            return cv2.resize(clean_u8.astype(np.float32) / 255.0, (w, h), interpolation=cv2.INTER_LINEAR)
        except Exception as exc:
            print(f"[SubjectMask] Inference error: {exc}")
            return np.ones((h, w), dtype=np.float32)

    def _get_realesrgan_session(self):
        """Lazy-load Real-ESRGAN neural super-resolution ONNX model."""
        if not HAS_ORT or not REALESRGAN_MODEL_PATH.exists():
            return None
        if self._realesrgan_session is not None:
            return self._realesrgan_session
        with self._realesrgan_lock:
            if self._realesrgan_session is not None:
                return self._realesrgan_session
            try:
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 2
                opts.inter_op_num_threads = 1
                self._realesrgan_session = ort.InferenceSession(
                    str(REALESRGAN_MODEL_PATH), sess_options=opts, providers=["CPUExecutionProvider"]
                )
                print(f"[Engine] Lazy-loaded Real-ESRGAN AI Super-Resolution model: {REALESRGAN_MODEL_PATH.name}")
            except Exception as exc:
                print(f"[Engine] Real-ESRGAN init error: {exc}")
        return self._realesrgan_session

    def _upscale_realesrgan(self, rgb: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        """Deep neural 4x super-resolution with tiling & high-frequency detail synthesis."""
        sess = self._get_realesrgan_session()
        if sess is None:
            return cv2.resize(rgb, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        try:
            h, w = rgb.shape[:2]
            # Downscale input proxy if original is already huge to keep inference responsive (<3 sec)
            max_in = 360
            if max(w, h) > max_in:
                scale_in = float(max_in) / float(max(w, h))
                in_w, in_h = max(16, int(round(w * scale_in))), max(16, int(round(h * scale_in)))
                work_rgb = cv2.resize(rgb, (in_w, in_h), interpolation=cv2.INTER_AREA)
            else:
                work_rgb = rgb

            tensor = (work_rgb.astype(np.float32) / 255.0).transpose((2, 0, 1))[np.newaxis, ...]
            input_name = sess.get_inputs()[0].name
            output_name = sess.get_outputs()[0].name
            out = sess.run([output_name], {input_name: tensor})[0]
            sr_rgb = np.clip(out[0].transpose((1, 2, 0)) * 255.0, 0, 255).astype(np.uint8)

            if sr_rgb.shape[1] != target_w or sr_rgb.shape[0] != target_h:
                sr_rgb = cv2.resize(sr_rgb, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
            return sr_rgb
        except Exception as exc:
            print(f"[Engine] Real-ESRGAN execution fallback: {exc}")
            return cv2.resize(rgb, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

    def prune_disk_caches(
        self,
        max_enhanced_bytes: int = CACHE_MAX_ENHANCED_BYTES,
        max_previews_bytes: int = CACHE_MAX_PREVIEWS_BYTES,
        max_thumbs_bytes: int = CACHE_MAX_THUMBS_BYTES,
    ) -> Dict[str, Any]:
        """Automatically evict oldest cached files (LRU) and stray test files to keep storage minimal."""
        freed_bytes = 0
        removed_files = 0

        # 1. Remove any stray root test_*.png / test_*.webp files in .cache/
        if CACHE_DIR.exists():
            for stray in CACHE_DIR.glob("test_*"):
                if stray.is_file():
                    try:
                        sz = stray.stat().st_size
                        stray.unlink()
                        freed_bytes += sz
                        removed_files += 1
                    except Exception:
                        pass

        # 2. Enforce LRU caps on cache subdirectories
        for folder, max_bytes in (
            (ENHANCED_CACHE_DIR, max_enhanced_bytes),
            (VIDEO_PREVIEW_CACHE_DIR, max_previews_bytes),
            (THUMB_CACHE_DIR, max_thumbs_bytes),
            (VIDEO_CLIPS_CACHE_DIR, CACHE_MAX_CLIPS_BYTES),
        ):
            if not folder.exists():
                continue
            try:
                files = []
                total_sz = 0
                for f in folder.iterdir():
                    if f.is_file():
                        st = f.stat()
                        files.append((st.st_mtime, st.st_size, f))
                        total_sz += st.st_size
                if total_sz > max_bytes:
                    # Sort oldest first
                    files.sort(key=lambda x: x[0])
                    target_sz = int(max_bytes * 0.80)
                    for mtime, sz, fpath in files:
                        if total_sz <= target_sz:
                            break
                        try:
                            fpath.unlink()
                            total_sz -= sz
                            freed_bytes += sz
                            removed_files += 1
                            # Also remove companion _meta.json if present
                            meta_companion = fpath.with_name(f"{fpath.stem}_meta.json")
                            if meta_companion.exists():
                                m_sz = meta_companion.stat().st_size
                                meta_companion.unlink()
                                total_sz -= m_sz
                                freed_bytes += m_sz
                        except Exception:
                            pass
            except Exception:
                pass

        return {
            "removed_files": removed_files,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        }

    # =========================================================================
    # SQLITE PERSISTENCE (Metadata, Ratings, Favorites, Tags, Custom Presets)
    # =========================================================================
    def _init_db(self):
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS image_metadata (
                        img_id TEXT PRIMARY KEY,
                        filename TEXT,
                        title TEXT,
                        model TEXT,
                        category TEXT,
                        rating INTEGER DEFAULT 0,
                        favorite INTEGER DEFAULT 0,
                        tags_json TEXT DEFAULT '[]',
                        updated_at INTEGER
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_presets (
                        preset_key TEXT PRIMARY KEY,
                        name TEXT,
                        config_json TEXT,
                        created_at INTEGER
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS boards (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        description TEXT DEFAULT '',
                        created_at INTEGER
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS board_items (
                        board_id TEXT,
                        img_id TEXT,
                        added_at INTEGER,
                        PRIMARY KEY (board_id, img_id)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS image_signatures (
                        cache_key TEXT PRIMARY KEY,
                        width INTEGER,
                        height INTEGER,
                        fmt TEXT,
                        is_animated INTEGER DEFAULT 0,
                        dhash_hex TEXT,
                        sharpness REAL,
                        palette_json TEXT,
                        vec_blob BLOB,
                        updated_at INTEGER
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def _load_signatures_from_db(self):
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM image_signatures")
                for r in cur.fetchall():
                    try:
                        ck = r["cache_key"]
                        dhash_hex = r["dhash_hex"] or "0000000000000000"
                        dhash_int = int(dhash_hex, 16)
                        palette = json.loads(r["palette_json"]) if r["palette_json"] else ["#1c1c1c", "#d4af37", "#f2ece1", "#801010", "#2b2b2b"]
                        vec_blob = r["vec_blob"]
                        if vec_blob and len(vec_blob) == 36 * 4:
                            vec = np.frombuffer(vec_blob, dtype=np.float32).copy()
                        else:
                            vec = np.zeros(36, dtype=np.float32)
                        self._feature_cache[ck] = {
                            "width": int(r["width"] or 0),
                            "height": int(r["height"] or 0),
                            "fmt": str(r["fmt"] or "JPG"),
                            "is_animated": bool(r["is_animated"]),
                            "dhash": dhash_int,
                            "dhash_hex": dhash_hex,
                            "sharpness": float(r["sharpness"] or 50.0),
                            "vec": vec,
                            "palette": palette,
                        }
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                conn.close()

    def _save_signatures_to_db(self, new_sigs: List[Tuple[str, Dict[str, Any]]]):
        if not new_sigs:
            return
        now = int(time.time())
        rows = []
        for ck, sig in new_sigs:
            rows.append(
                (
                    ck,
                    int(sig.get("width", 0)),
                    int(sig.get("height", 0)),
                    str(sig.get("fmt", "JPG")),
                    1 if sig.get("is_animated") else 0,
                    str(sig.get("dhash_hex", "0000000000000000")),
                    float(sig.get("sharpness", 50.0)),
                    json.dumps(sig.get("palette", [])),
                    sig["vec"].astype(np.float32).tobytes(),
                    now,
                )
            )
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO image_signatures
                    (cache_key, width, height, fmt, is_animated, dhash_hex, sharpness, palette_json, vec_blob, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.commit()
            except Exception:
                pass
            finally:
                conn.close()

    def _get_db_overrides(self) -> Dict[str, Dict[str, Any]]:
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM image_metadata")
                rows = cur.fetchall()
                result = {}
                for r in rows:
                    try:
                        tags = json.loads(r["tags_json"]) if r["tags_json"] else []
                    except Exception:
                        tags = []
                    result[r["img_id"]] = {
                        "title": r["title"],
                        "model": r["model"],
                        "category": r["category"],
                        "rating": int(r["rating"] or 0),
                        "favorite": bool(r["favorite"]),
                        "tags": tags,
                    }
                return result
            finally:
                conn.close()

    def update_image_metadata(self, img_id: str, payload: Dict[str, Any]) -> Optional[Dict]:
        """Persist user edits for model, category, title, rating, favorite, or tags."""
        current = self.get_image_by_id(img_id)
        if not current:
            return None

        title = str(payload.get("title", current["title"])).strip() or current["title"]
        model = str(payload.get("model", current["model"])).strip() or current["model"]
        category = str(payload.get("category", current["category"])).strip() or current["category"]
        rating = max(0, min(5, int(payload.get("rating", current.get("rating", 0)))))
        favorite = 1 if payload.get("favorite", current.get("favorite", False)) else 0

        raw_tags = payload.get("tags", current.get("tags", []))
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [str(t).strip() for t in raw_tags if str(t).strip()]
        else:
            tags = current.get("tags", [])
        tags = list(dict.fromkeys(tags))

        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO image_metadata (img_id, filename, title, model, category, rating, favorite, tags_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(img_id) DO UPDATE SET
                        title=excluded.title,
                        model=excluded.model,
                        category=excluded.category,
                        rating=excluded.rating,
                        favorite=excluded.favorite,
                        tags_json=excluded.tags_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        img_id,
                        current["filename"],
                        title,
                        model,
                        category,
                        rating,
                        favorite,
                        json.dumps(tags),
                        int(time.time()),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        self._meta_cache.clear()
        return self.get_image_by_id(img_id)

    def ingest_uploaded_image(
        self,
        tmp_path: Path,
        original_filename: str,
        model: str = "",
        category: str = "Uploaded",
        title: str = "",
        tags: Optional[List[str]] = None,
        auto_enhance: bool = False,
        preset: str = "ultra_hot_4k",
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Validate, store, and index a user-uploaded picture with persistent SQLite metadata."""
        if not tmp_path.exists() or tmp_path.stat().st_size <= 0:
            tmp_path.unlink(missing_ok=True)
            return False, None, "Uploaded file is empty"

        detected_ext = ""
        try:
            with Image.open(tmp_path) as im:
                im.verify()
            with Image.open(tmp_path) as im2:
                w, h = im2.size
                if w <= 0 or h <= 0:
                    tmp_path.unlink(missing_ok=True)
                    return False, None, "Invalid image dimensions"
                fmt_upper = (im2.format or "").upper()
                fmt_map = {
                    "JPEG": ".jpg",
                    "PNG": ".png",
                    "WEBP": ".webp",
                    "BMP": ".bmp",
                    "TIFF": ".tiff",
                }
                detected_ext = fmt_map.get(fmt_upper, "")
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            return False, None, f"Invalid or unsupported image file ({exc})"

        raw_clean = Path(original_filename or f"upload_{int(time.time())}.jpg").name
        stem = re.sub(r"[^\w\-. ]+", "_", Path(raw_clean).stem).strip(" ._") or f"upload_{int(time.time())}"
        ext = Path(raw_clean).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            ext = detected_ext if detected_ext in SUPPORTED_EXTENSIONS else ".jpg"

        safe_name = f"{stem}{ext}"
        dest_path = self.source_dir / safe_name
        counter = 1
        while dest_path.exists():
            dest_path = self.source_dir / f"{stem}_{counter}{ext}"
            counter += 1

        shutil.move(str(tmp_path), str(dest_path))

        rel_name = str(dest_path.relative_to(self.source_dir))
        img_id = self._file_id(rel_name)

        parsed = self.parse_filename_metadata(dest_path.name)
        clean_model = model.strip() or (stem[:36] if parsed["model"] == "Featured Babe" else parsed["model"])
        clean_cat = category.strip() or "Uploaded"
        clean_title = title.strip() or f"{clean_model} — {clean_cat}"
        merged_tags = ["Uploaded", "4K Ready"]
        if tags:
            for t in tags:
                if t and str(t).strip():
                    merged_tags.append(str(t).strip())
        for t in parsed.get("tags", []):
            if t not in merged_tags:
                merged_tags.append(t)

        now_ts = int(time.time())
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                conn.execute(
                    """
                    INSERT INTO image_metadata (img_id, filename, title, model, category, rating, favorite, tags_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(img_id) DO UPDATE SET
                        filename=excluded.filename,
                        title=excluded.title,
                        model=excluded.model,
                        category=excluded.category,
                        tags_json=excluded.tags_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        img_id,
                        rel_name,
                        clean_title,
                        clean_model,
                        clean_cat,
                        0,
                        0,
                        json.dumps(merged_tags),
                        now_ts,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        self._meta_cache.clear()
        self.get_thumbnail(img_id)
        if auto_enhance:
            self.enhance_image(img_id, preset=preset)

        item_meta = self.get_image_by_id(img_id)
        return True, item_meta, ""

    def _load_custom_presets_from_db(self):
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM custom_presets ORDER BY created_at ASC")
                for row in cur.fetchall():
                    try:
                        cfg = json.loads(row["config_json"])
                        cfg["name"] = row["name"]
                        cfg["builtin"] = False
                        PRESET_CONFIGS[row["preset_key"]] = cfg
                    except Exception:
                        pass
            finally:
                conn.close()

    def save_custom_preset(self, name: str, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        clean_name = name.strip() or "Custom 4K Preset"
        slug = re.sub(r"[^a-z0-9_]+", "_", clean_name.lower()).strip("_")
        preset_key = f"custom_{slug}_{int(time.time()) % 10000}"

        base = dict(PRESET_CONFIGS["ultra_hot_4k"])
        base["name"] = clean_name
        base["desc"] = "Custom user-calibrated neural & optical preset"
        base["builtin"] = False
        for k in (
            "target_long_edge",
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
            if k in params and params[k] is not None:
                base[k] = float(params[k])
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
            if b_key in params:
                base[b_key] = bool(params[b_key])
        for s_key in ("upscale_mode", "lut_name", "crop_aspect"):
            if s_key in params and params[s_key]:
                base[s_key] = str(params[s_key])

        PRESET_CONFIGS[preset_key] = base
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO custom_presets (preset_key, name, config_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (preset_key, clean_name, json.dumps(base), int(time.time())),
                )
                conn.commit()
            finally:
                conn.close()

        return preset_key, base

    def delete_custom_preset(self, preset_key: str) -> bool:
        if preset_key not in PRESET_CONFIGS or PRESET_CONFIGS[preset_key].get("builtin", False):
            return False
        del PRESET_CONFIGS[preset_key]
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                conn.execute("DELETE FROM custom_presets WHERE preset_key = ?", (preset_key,))
                conn.commit()
            finally:
                conn.close()
        return True

    # =========================================================================
    # MOODBOARDS & PIN-STYLE BOARDS PERSISTENCE
    # =========================================================================
    def list_boards(self) -> List[Dict[str, Any]]:
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT b.id, b.name, b.description, b.created_at, COUNT(bi.img_id) as item_count
                    FROM boards b
                    LEFT JOIN board_items bi ON b.id = bi.board_id
                    GROUP BY b.id
                    ORDER BY b.created_at DESC
                    """
                )
                return [dict(r) for r in cur.fetchall()]
            except Exception:
                return []
            finally:
                conn.close()

    def create_board(self, name: str, description: str = "") -> Dict[str, Any]:
        clean_name = name.strip() or "Untitled Moodboard"
        board_id = "board_" + hashlib.md5(f"{clean_name}:{time.time()}".encode("utf-8")).hexdigest()[:8]
        now = int(time.time())
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO boards (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                    (board_id, clean_name, description.strip(), now),
                )
                conn.commit()
                return {"id": board_id, "name": clean_name, "description": description.strip(), "created_at": now, "item_count": 0}
            finally:
                conn.close()

    def delete_board(self, board_id: str) -> bool:
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM boards WHERE id = ?", (board_id,))
                cur.execute("DELETE FROM board_items WHERE board_id = ?", (board_id,))
                conn.commit()
                return True
            finally:
                conn.close()

    def add_to_board(self, board_id: str, img_id: str) -> bool:
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT OR IGNORE INTO board_items (board_id, img_id, added_at) VALUES (?, ?, ?)",
                    (board_id, img_id, int(time.time())),
                )
                conn.commit()
                return True
            finally:
                conn.close()

    def remove_from_board(self, board_id: str, img_id: str) -> bool:
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM board_items WHERE board_id = ? AND img_id = ?", (board_id, img_id))
                conn.commit()
                return True
            finally:
                conn.close()

    def get_board_items(self, board_id: str) -> List[str]:
        with self._db_lock:
            conn = sqlite3.connect(str(DB_PATH))
            try:
                cur = conn.cursor()
                cur.execute("SELECT img_id FROM board_items WHERE board_id = ? ORDER BY added_at DESC", (board_id,))
                return [r[0] for r in cur.fetchall()]
            except Exception:
                return []
            finally:
                conn.close()

    # =========================================================================
    # 3D COLOR LUT (.cube) GENERATOR & TRILINEAR INTERPOLATOR
    # =========================================================================
    def _ensure_default_luts(self):
        luts_spec = {
            "Golden_Hour_Glam.cube": ("Golden Hour Glam", (1.06, 1.01, 0.92), 1.08),
            "Teal_Orange_Cinema.cube": ("Teal & Orange Cinema", (1.08, 0.99, 0.90), 1.15),
            "Velvet_Rose_VIP.cube": ("Velvet Rose VIP", (1.07, 0.96, 1.02), 1.10),
            "Crisp_Studio_Daylight.cube": ("Crisp Studio Daylight", (1.02, 1.02, 1.04), 1.12),
        }
        size = 17
        for fname, (title, rgb_gains, contrast) in luts_spec.items():
            fpath = LUTS_DIR / fname
            if fpath.exists():
                continue
            lines = [
                f'TITLE "{title}"',
                f"LUT_3D_SIZE {size}",
                "DOMAIN_MIN 0.0 0.0 0.0",
                "DOMAIN_MAX 1.0 1.0 1.0",
            ]
            for b_i in range(size):
                for g_i in range(size):
                    for r_i in range(size):
                        r = r_i / (size - 1)
                        g = g_i / (size - 1)
                        b = b_i / (size - 1)
                        luma = 0.299 * r + 0.587 * g + 0.114 * b

                        if "Teal_Orange" in fname:
                            shadow_weight = max(0.0, 1.0 - luma * 1.8)
                            high_weight = max(0.0, (luma - 0.35) * 1.4)
                            r = r + high_weight * 0.06 - shadow_weight * 0.04
                            g = g + shadow_weight * 0.02
                            b = b + shadow_weight * 0.07 - high_weight * 0.05
                        else:
                            r *= rgb_gains[0]
                            g *= rgb_gains[1]
                            b *= rgb_gains[2]

                        r = 0.5 + (r - 0.5) * contrast
                        g = 0.5 + (g - 0.5) * contrast
                        b = 0.5 + (b - 0.5) * contrast

                        r = min(1.0, max(0.0, r))
                        g = min(1.0, max(0.0, g))
                        b = min(1.0, max(0.0, b))
                        lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
            fpath.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def list_luts(self) -> List[Dict[str, str]]:
        luts = [{"id": "none", "name": "None (Native AI Color Grading)"}]
        if LUTS_DIR.exists():
            for f in sorted(LUTS_DIR.glob("*.cube")):
                label = f.stem.replace("_", " ")
                luts.append({"id": f.name, "name": f"🎨 {label}"})
        return luts

    def _load_cube_lut(self, lut_name: str) -> Optional[np.ndarray]:
        if not lut_name or lut_name == "none":
            return None
        if lut_name in self._lut_cache:
            return self._lut_cache[lut_name]

        lut_path = (LUTS_DIR / Path(lut_name).name).resolve()
        if not lut_path.exists():
            return None

        size = 0
        data_rows = []
        for raw_line in lut_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.upper().startswith("LUT_3D_SIZE"):
                parts = line.split()
                if len(parts) >= 2:
                    size = int(parts[1])
                continue
            if line[0].isdigit() or line[0] in "+-.":
                parts = line.split()
                if len(parts) == 3:
                    try:
                        data_rows.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    except ValueError:
                        pass

        if size <= 1 or len(data_rows) != size * size * size:
            return None

        lut_arr = np.array(data_rows, dtype=np.float32).reshape((size, size, size, 3))
        self._lut_cache[lut_name] = lut_arr
        return lut_arr

    def _apply_3d_lut(self, rgb: np.ndarray, lut_name: str, strength: float = 0.75) -> np.ndarray:
        lut = self._load_cube_lut(lut_name)
        if lut is None:
            return rgb
        size = lut.shape[0]
        scale = size - 1

        lut_u8 = np.clip(lut * 255.0, 0, 255).astype(np.uint8)
        idx_lut = np.clip(np.rint(np.arange(256, dtype=np.float32) * (scale / 255.0)), 0, scale).astype(np.uint8)
        idx_map = cv2.LUT(rgb, idx_lut)
        mapped = lut_u8[idx_map[:, :, 2], idx_map[:, :, 1], idx_map[:, :, 0]]
        return cv2.addWeighted(rgb, 1.0 - strength, mapped, strength, 0)

    # =========================================================================
    # PERCEPTUAL HASH (dHash), SHARPNESS SCORE & VISUAL SIMILARITY EMBEDDING
    # =========================================================================
    def _compute_image_signature(
        self, fpath: Path, cache_key: str, width: int = 0, height: int = 0, fmt: str = "JPG", is_animated: bool = False
    ) -> Tuple[Dict[str, Any], bool]:
        """Compute 64-bit dHash, Laplacian sharpness score, and HSV visual feature vector."""
        if cache_key in self._feature_cache:
            cached = self._feature_cache[cache_key]
            if cached.get("width", 0) > 0:
                return cached, False

        dhash_int = 0
        sharpness = 50.0
        feature_vec = np.zeros(36, dtype=np.float32)
        palette = ["#1c1c1c", "#d4af37", "#f2ece1", "#801010", "#2b2b2b"]

        try:
            if HAS_CV2:
                read_flag = cv2.IMREAD_REDUCED_COLOR_4 if fpath.suffix.lower() in (".jpg", ".jpeg") else cv2.IMREAD_COLOR
                bgr = cv2.imread(str(fpath), read_flag)
                if bgr is None and read_flag != cv2.IMREAD_COLOR:
                    bgr = cv2.imread(str(fpath), cv2.IMREAD_COLOR)
                if bgr is not None:
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                    # 1. 64-bit difference hash (9x8 grayscale resize)
                    small_g = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
                    diff = small_g[:, 1:] > small_g[:, :-1]
                    bits = diff.flatten()
                    for idx, b_val in enumerate(bits):
                        if b_val:
                            dhash_int |= 1 << idx

                    # 2. Laplacian variance sharpness score on normalized 480p frame
                    h, w = gray.shape[:2]
                    norm_g = cv2.resize(gray, (480, max(1, int(480 * h / max(w, 1)))), interpolation=cv2.INTER_AREA)
                    sharpness = round(float(cv2.Laplacian(norm_g, cv2.CV_16S).var()), 1)

                    # 3. Spatial + HSV visual similarity embedding (top/bottom color + luma distribution)
                    small_bgr = cv2.resize(bgr, (64, 64), interpolation=cv2.INTER_AREA)
                    hsv = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2HSV)
                    h_top = cv2.calcHist([hsv[:32, :]], [0, 1], None, [6, 3], [0, 180, 0, 256]).flatten()
                    h_bot = cv2.calcHist([hsv[32:, :]], [0, 1], None, [6, 3], [0, 180, 0, 256]).flatten()
                    raw_vec = np.concatenate([h_top, h_bot]).astype(np.float32)
                    norm_val = float(np.linalg.norm(raw_vec))
                    if norm_val > 1e-6:
                        feature_vec = raw_vec / norm_val

                    # 4. K-means dominant color palette (5 dominant hex colors)
                    thumb_bgr = cv2.resize(bgr, (36, 36), interpolation=cv2.INTER_AREA)
                    pixels = thumb_bgr.reshape(-1, 3).astype(np.float32)
                    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
                    try:
                        _, labels, centers = cv2.kmeans(pixels, 5, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
                        counts = np.bincount(labels.flatten())
                        sorted_idx = np.argsort(counts)[::-1]
                        extracted = []
                        for c_i in sorted_idx:
                            b_c, g_c, r_c = centers[c_i]
                            extracted.append(f"#{int(round(r_c)):02x}{int(round(g_c)):02x}{int(round(b_c)):02x}")
                        if extracted:
                            palette = extracted
                    except Exception:
                        pass
        except Exception:
            pass

        sig = {
            "width": width,
            "height": height,
            "fmt": fmt,
            "is_animated": is_animated,
            "dhash": dhash_int,
            "dhash_hex": f"{dhash_int:016x}",
            "sharpness": sharpness,
            "vec": feature_vec,
            "palette": palette,
        }
        self._feature_cache[cache_key] = sig
        return sig, True

    @staticmethod
    def _hamming_distance(h1: int, h2: int) -> int:
        return (h1 ^ h2).bit_count()

    # =========================================================================
    # FOLDER MANAGEMENT & SCANNING (WITH DEDUPLICATION & SIMILARITY)
    # =========================================================================
    def list_available_folders(self) -> List[Dict[str, Any]]:
        folders = []
        candidates = [SOURCE_IMAGE_DIR, VIDEOS_ROOT_DIR]
        if VIDEOS_ROOT_DIR.exists():
            for child in sorted(VIDEOS_ROOT_DIR.iterdir()):
                if child.is_dir() and not child.name.startswith("."):
                    candidates.append(child)

        seen = set()
        for folder in candidates:
            resolved = folder.resolve()
            if str(resolved) in seen or not resolved.exists():
                continue
            seen.add(str(resolved))
            try:
                img_count = sum(
                    1
                    for f in resolved.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
                )
            except Exception:
                img_count = 0
            folders.append(
                {
                    "path": str(resolved),
                    "name": resolved.name if resolved != VIDEOS_ROOT_DIR else "Videos (Root)",
                    "image_count": img_count,
                    "active": resolved == self.source_dir,
                }
            )
        return folders

    def set_source_dir(self, folder_path: str, recursive: bool = False) -> Tuple[bool, str]:
        target = Path(folder_path).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            return False, f"Directory not found: {folder_path}"
        self.source_dir = target
        self.recursive_scan = bool(recursive)
        self._meta_cache.clear()
        return True, str(self.source_dir)

    def _file_id(self, rel_path: str) -> str:
        key = f"{self.source_dir}:{rel_path}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()[:12]

    def parse_filename_metadata(self, filename: str) -> Dict[str, Any]:
        stem = Path(filename).stem
        stem_clean = re.sub(r"^EliteBabes_4K_Enhanced_", "", stem)

        model = "Featured Babe"
        category = "Exclusive"
        timestamp = ""
        tags = ["4K Ready", "Exclusive"]

        ts_match = re.search(r"(\d{2}[:_]\d{2}[:_]\d{2})", stem_clean)
        if ts_match:
            timestamp = ts_match.group(1).replace("_", ":")

        upper = stem_clean.upper()
        if "TUSHY" in upper:
            category = "Tushy Glam"
            tags.append("Tushy")
            if "LANA" in upper:
                model = "Lana"
                tags.append("Lana")
            elif "CHLOE" in upper:
                model = "Chloe"
                tags.append("Chloe")
            elif "EVA" in upper:
                model = "Eva"
                tags.append("Eva")
            elif "MAYA" in upper:
                model = "Maya"
                tags.append("Maya")
            elif "MIA" in upper:
                model = "Mia"
                tags.append("Mia")
            elif "104251" in upper:
                model = "Bella"
                tags.append("Bella")
        elif "BLACKED" in upper:
            category = "Luxury Studio"
            tags.append("Blacked")
            if "LANA" in upper:
                model = "Lana"
                tags.append("Lana")
        elif "JASMINE" in upper or "CASTING" in upper:
            model = "Jasmine"
            category = "Casting"
            tags.extend(["Jasmine", "Casting"])
        elif "MYDADDY" in upper:
            model = "Elena"
            category = "Studio VIP"
            tags.extend(["Elena", "VIP"])
        elif "CLIP" in upper:
            model = "Aria"
            category = "Cinema Clips"
            tags.extend(["Aria", "Clips"])
        elif "SCREENSHOT" in upper:
            model = "Jasmine"
            category = "Backstage"
            tags.extend(["Jasmine", "Backstage"])

        if "2160P" in upper:
            tags.append("2160P Source")
        if "LOOP" in upper:
            tags.append("4K Animated Loop")

        clean_title = f"{model} — {category}"
        if timestamp:
            clean_title += f" ({timestamp})"

        return {
            "model": model,
            "category": category,
            "timestamp": timestamp,
            "title": clean_title,
            "tags": list(dict.fromkeys(tags)),
        }

    def scan_folder(
        self,
        search_query: str = "",
        category_filter: str = "",
        model_filter: str = "",
        only_favorites: bool = False,
        only_uploaded: bool = False,
        min_rating: int = 0,
        deduplicate: bool = False,
        similar_to: str = "",
        shuffle: bool = False,
    ) -> List[Dict]:
        """Real-time scan with dHash burst duplicate grouping and visual similarity ranking."""
        if not self.source_dir.exists():
            return []

        overrides = self._get_db_overrides()
        all_scanned: List[Dict] = []

        if self.recursive_scan:
            file_paths = sorted(
                [
                    p
                    for p in self.source_dir.rglob("*")
                    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
                ]
            )
        else:
            file_paths = sorted(
                [
                    p
                    for p in self.source_dir.iterdir()
                    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
                ]
            )

        new_sigs_to_persist: List[Tuple[str, Dict[str, Any]]] = []

        for fpath in file_paths:
            rel_name = str(fpath.relative_to(self.source_dir))
            try:
                stat = fpath.stat()
            except OSError:
                continue
            if stat.st_size <= 0:
                continue
            img_id = self._file_id(rel_name)
            cache_key = f"{img_id}:{stat.st_mtime_ns}:{stat.st_size}"

            if cache_key not in self._meta_cache:
                parsed = self.parse_filename_metadata(fpath.name)
                cached_sig = self._feature_cache.get(cache_key)
                if cached_sig and cached_sig.get("width", 0) > 0:
                    width = cached_sig["width"]
                    height = cached_sig["height"]
                    fmt = cached_sig["fmt"]
                    is_animated = cached_sig["is_animated"]
                    sig = cached_sig
                else:
                    is_animated = False
                    try:
                        with Image.open(fpath) as im:
                            width, height = im.size
                            fmt = im.format or fpath.suffix.lstrip(".").upper()
                            is_animated = bool(getattr(im, "is_animated", False))
                    except Exception:
                        width, height, fmt = 0, 0, "PNG"

                    sig, is_new_sig = self._compute_image_signature(
                        fpath, cache_key, width=width, height=height, fmt=fmt, is_animated=is_animated
                    )
                    if is_new_sig and width > 0:
                        new_sigs_to_persist.append((cache_key, sig))

                scale = max(1.0, 3840.0 / max(width, height, 1))
                enh_w = int(round(width * scale))
                enh_h = int(round(height * scale))
                gcd_val = int(np.gcd(width, height)) if (width > 0 and height > 0) else 1
                aspect_str = f"{width // gcd_val}:{height // gcd_val}" if gcd_val > 0 else "16:9"

                self._meta_cache[cache_key] = {
                    "id": img_id,
                    "filename": rel_name,
                    "title": parsed["title"],
                    "model": parsed["model"],
                    "category": parsed["category"],
                    "timestamp": parsed["timestamp"],
                    "tags": parsed["tags"],
                    "rating": 0,
                    "favorite": False,
                    "width": width,
                    "height": height,
                    "aspect_ratio": round(width / max(height, 1), 4),
                    "aspect_label": aspect_str,
                    "enhanced_width": enh_w,
                    "enhanced_height": enh_h,
                    "format": fmt,
                    "is_animated": is_animated,
                    "sharpness_score": sig["sharpness"],
                    "palette": sig.get("palette", ["#1c1c1c", "#d4af37", "#f2ece1", "#801010", "#2b2b2b"]),
                    "dhash_hex": sig["dhash_hex"],
                    "_dhash_int": sig["dhash"],
                    "_vec": sig["vec"],
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "mtime": int(stat.st_mtime),
                    "original_url": f"/api/image/original/{img_id}",
                    "thumb_url": f"/api/image/thumb/{img_id}",
                    "enhanced_url": f"/api/image/enhanced/{img_id}",
                }

            meta = dict(self._meta_cache[cache_key])
            if img_id in overrides:
                ov = overrides[img_id]
                meta["title"] = ov["title"] or meta["title"]
                meta["model"] = ov["model"] or meta["model"]
                meta["category"] = ov["category"] or meta["category"]
                meta["rating"] = ov["rating"]
                meta["favorite"] = ov["favorite"]
                if ov["tags"]:
                    meta["tags"] = ov["tags"]
            tags_lower = [str(t).lower() for t in meta.get("tags", [])]
            meta["is_uploaded"] = (
                "uploaded" in tags_lower
                or str(meta.get("category", "")).lower() == "uploaded"
                or str(meta.get("filename", "")).lower().startswith(("upload_", "uploaded_"))
            )
            self._id_to_meta[img_id] = meta
            all_scanned.append(meta)

        if new_sigs_to_persist:
            self._save_signatures_to_db(new_sigs_to_persist)

        # Group near-duplicate burst shots using 64-bit dHash (Hamming distance <= 10)
        groups: List[List[Dict]] = []
        for item in all_scanned:
            placed = False
            for grp in groups:
                if self._hamming_distance(item["_dhash_int"], grp[0]["_dhash_int"]) <= 10:
                    grp.append(item)
                    placed = True
                    break
            if not placed:
                groups.append([item])

        for grp_idx, grp in enumerate(groups):
            best_item = max(grp, key=lambda x: x["sharpness_score"])
            for member in grp:
                member["dup_group_id"] = grp_idx
                member["dup_count"] = len(grp)
                member["is_sharpest_in_group"] = member["id"] == best_item["id"]

        # Visual similarity anchor if requested
        target_vec = None
        if similar_to:
            for it in all_scanned:
                if it["id"] == similar_to:
                    target_vec = it["_vec"]
                    break

        q = search_query.strip().lower()
        cat_f = category_filter.strip().lower()
        mod_f = model_filter.strip().lower()

        filtered: List[Dict] = []
        for meta in all_scanned:
            if deduplicate and not meta["is_sharpest_in_group"]:
                continue
            if only_favorites and not meta["favorite"]:
                continue
            if only_uploaded and not meta.get("is_uploaded", False):
                continue
            if min_rating > 0 and meta["rating"] < min_rating:
                continue
            if cat_f and cat_f != "all" and meta["category"].lower() != cat_f:
                continue
            if mod_f and mod_f != "all" and meta["model"].lower() != mod_f:
                continue
            if q:
                searchable = " ".join(
                    [
                        meta["filename"],
                        meta["title"],
                        meta["model"],
                        meta["category"],
                        " ".join(meta["tags"]),
                    ]
                ).lower()
                if q not in searchable:
                    continue

            clean_meta = {k: v for k, v in meta.items() if not k.startswith("_")}
            if target_vec is not None:
                sim = float(np.dot(target_vec, meta["_vec"]))
                clean_meta["similarity_pct"] = max(0, min(100, int(round(sim * 100))))
            else:
                clean_meta["similarity_pct"] = None
            filtered.append(clean_meta)

        if target_vec is not None:
            filtered.sort(key=lambda x: x.get("similarity_pct") or 0, reverse=True)
            filtered = [x for x in filtered if (x.get("similarity_pct") or 0) >= 55]
        elif shuffle:
            import random
            random.shuffle(filtered)

        return filtered

    def get_image_by_id(self, img_id: str) -> Optional[Dict]:
        if img_id in self._id_to_meta:
            return {k: v for k, v in self._id_to_meta[img_id].items() if not k.startswith("_")}
        all_items = self.scan_folder()
        for item in all_items:
            if item["id"] == img_id:
                return item
        return None

    def get_thumbnail(self, img_id: str, max_side: int = 720) -> Optional[Path]:
        meta = self.get_image_by_id(img_id)
        if not meta:
            return None

        src_path = self.source_dir / meta["filename"]
        if meta.get("is_animated"):
            return src_path

        thumb_path = THUMB_CACHE_DIR / f"{img_id}_{max_side}.jpg"
        if thumb_path.exists() and thumb_path.stat().st_mtime >= src_path.stat().st_mtime:
            return thumb_path

        if HAS_CV2:
            bgr = cv2.imread(str(src_path), cv2.IMREAD_COLOR)
            if bgr is not None:
                h, w = bgr.shape[:2]
                if max(w, h) > max_side:
                    scale = max_side / float(max(w, h))
                    tw = max(1, int(round(w * scale)))
                    th = max(1, int(round(h * scale)))
                    bgr = cv2.resize(bgr, (tw, th), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(thumb_path), bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
                return thumb_path

        with Image.open(src_path) as im:
            im = im.convert("RGB")
            im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            im.save(thumb_path, "JPEG", quality=90, optimize=True)

        return thumb_path

    # =========================================================================
    # EXACT-FIT IMAGE RESIZER ENGINE (NO ZOOM-IN / NO ZOOM-OUT / ZERO CROP)
    # =========================================================================
    def resize_image_exact(
        self,
        img_id: str,
        target_w: int = 0,
        target_h: int = 0,
        mode: str = "exact_uploaded",
    ) -> Tuple[Optional[Path], Dict[str, Any]]:
        """
        Dedicated Image Resizer Engine:
        - 'exact_uploaded': Preserves 100% exact uploaded dimensions (width x height), zero zoom-in, zero zoom-out, zero crop.
        - 'exact_fit': Resizes to fit within target_w x target_h preserving 100% of the uploaded frame without cropping.
        - 'exact_dimensions': Resizes to exact target_w x target_h using Lanczos4.
        """
        meta = self.get_image_by_id(img_id)
        if not meta:
            return None, {}

        src_path = self.source_dir / meta["filename"]
        orig_w, orig_h = int(meta["width"]), int(meta["height"])

        if mode == "exact_uploaded" or (target_w <= 0 and target_h <= 0):
            # If the raw source file is a large uncompressed PNG (>1.2MB) or 4K frame,
            # serve a lightweight 1080p exact-aspect WebP/JPEG preview for gallery grid cards
            # so browser RAM and network stay minimal while preserving 100% exact framing!
            if meta.get("size_bytes", 0) > 1_200_000 and not meta.get("is_animated"):
                preview_path = self.get_thumbnail(img_id, max_side=1280)
                if preview_path and preview_path.exists():
                    return preview_path, {
                        "mode": "exact_uploaded",
                        "original_resolution": f"{orig_w}x{orig_h}",
                        "output_resolution": f"{orig_w}x{orig_h}",
                        "aspect_label": meta.get("aspect_label", "Native"),
                        "scale_factor": 1.0,
                        "cropped_pixels": 0,
                    }
            return src_path, {
                "mode": "exact_uploaded",
                "original_resolution": f"{orig_w}x{orig_h}",
                "output_resolution": f"{orig_w}x{orig_h}",
                "aspect_label": meta.get("aspect_label", "Native"),
                "scale_factor": 1.0,
                "cropped_pixels": 0,
            }

        tw = target_w if target_w > 0 else orig_w
        th = target_h if target_h > 0 else orig_h
        if mode == "exact_fit":
            scale = min(tw / max(orig_w, 1), th / max(orig_h, 1))
            out_w = max(1, int(round(orig_w * scale)))
            out_h = max(1, int(round(orig_h * scale)))
        else:
            out_w, out_h = tw, th
            scale = round(out_w / max(orig_w, 1), 3)

        out_path = THUMB_CACHE_DIR / f"resized_{img_id}_{mode}_{out_w}x{out_h}.jpg"
        if not out_path.exists() or out_path.stat().st_mtime < src_path.stat().st_mtime:
            with Image.open(src_path) as im:
                im = im.convert("RGB")
                resized = im.resize((out_w, out_h), Image.Resampling.LANCZOS)
                resized.save(out_path, "JPEG", quality=92, optimize=True)

        return out_path, {
            "mode": mode,
            "original_resolution": f"{orig_w}x{orig_h}",
            "output_resolution": f"{out_w}x{out_h}",
            "aspect_label": meta.get("aspect_label", "Native"),
            "scale_factor": round(float(scale), 4),
            "cropped_pixels": 0,
        }

    # =========================================================================
    # ACCURATE NEURAL & GRABCUT BACKGROUND REMOVAL (TRANSPARENT ALPHA PNG)
    # =========================================================================
    def remove_background(self, img_id: str, max_dim: int = 1920) -> Optional[Path]:
        """Extract main subject with transparent background using high-precision Silueta ONNX inference or GrabCut."""
        meta = self.get_image_by_id(img_id)
        if not meta:
            return None

        out_file = NOBG_CACHE_DIR / f"{img_id}_nobg_{max_dim}.png"
        if out_file.exists() and out_file.stat().st_size > 1000:
            return out_file

        src_path = self.source_dir / meta["filename"]
        if not src_path.exists():
            return None

        with self._nobg_lock:
            if out_file.exists() and out_file.stat().st_size > 1000:
                return out_file

            NOBG_CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # 1. High-precision Neural Network (Silueta 44MB or U2NetP)
            ort_sess = self._get_ort_session()
            if ort_sess is not None:
                try:
                    with Image.open(src_path).convert("RGB") as orig_im:
                        orig_w, orig_h = orig_im.size
                        effective_dim = max(10, int(max_dim)) if int(max_dim) > 0 else max(orig_w, orig_h)
                        scale = min(1.0, float(effective_dim) / max(orig_w, orig_h, 1))
                        dw, dh = max(10, int(round(orig_w * scale))), max(10, int(round(orig_h * scale)))
                        disp_im = orig_im.resize((dw, dh), Image.Resampling.LANCZOS)

                        # Neural inference at 320x320
                        u_in = disp_im.resize((320, 320), Image.Resampling.BILINEAR)
                        arr = np.array(u_in).astype(np.float32) / 255.0
                        arr[:, :, 0] = (arr[:, :, 0] - 0.485) / 0.229
                        arr[:, :, 1] = (arr[:, :, 1] - 0.456) / 0.224
                        arr[:, :, 2] = (arr[:, :, 2] - 0.406) / 0.225
                        input_tensor = arr.transpose((2, 0, 1))[np.newaxis, ...].astype(np.float32)

                        input_name = ort_sess.get_inputs()[0].name
                        output_name = ort_sess.get_outputs()[0].name
                        outputs = ort_sess.run([output_name], {input_name: input_tensor})

                        mask = outputs[0][0, 0, :, :]
                        # High-precision Hermite smoothstep thresholding
                        clean_alpha = np.clip((mask - 0.25) / 0.50, 0.0, 1.0)
                        clean_alpha = clean_alpha * clean_alpha * (3.0 - 2.0 * clean_alpha)
                        mask_uint = (clean_alpha * 255.0).astype(np.uint8)

                        # Upscale mask and refine edges with bilateral edge filter
                        if HAS_CV2:
                            mask_up = cv2.resize(mask_uint, (dw, dh), interpolation=cv2.INTER_LINEAR)
                            mask_uint = cv2.bilateralFilter(mask_up, d=5, sigmaColor=35, sigmaSpace=35)
                            mask_img = Image.fromarray(mask_uint)
                        else:
                            mask_img = Image.fromarray(mask_uint).resize((dw, dh), Image.Resampling.BILINEAR)

                        cutout = disp_im.copy()
                        cutout.putalpha(mask_img)

                        # Center into a symmetric square canvas for smooth clockwise rotation
                        bbox = cutout.getbbox()
                        if bbox:
                            bx1, by1, bx2, by2 = bbox
                            bw, bh = bx2 - bx1, by2 - by1
                            side = max(bw, bh) + 16
                            square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                            cropped = cutout.crop(bbox)
                            square.paste(cropped, ((side - bw) // 2, (side - bh) // 2), cropped)
                            cutout = square

                        tmp_file = out_file.with_name(f"{out_file.stem}_tmp_{os.getpid()}_{threading.get_ident()}.png")
                        cutout.save(tmp_file, "PNG", optimize=True)
                        tmp_file.replace(out_file)
                        return out_file
                except Exception as exc:
                    print(f"[NoBG] ONNX extraction error: {exc}")
                    print(f"[NoBG] ONNX extraction error: {exc}")

            # 2. Robust OpenCV GrabCut Fallback with skin-prior
            if HAS_CV2:
                try:
                    bgr = cv2.imread(str(src_path))
                    if bgr is not None:
                        h, w = bgr.shape[:2]
                        scale = min(1.0, float(max_dim) / max(w, h, 1))
                        sw, sh = max(10, int(round(w * scale))), max(10, int(round(h * scale)))
                        small = cv2.resize(bgr, (sw, sh), interpolation=cv2.INTER_AREA)

                        mask = np.zeros((sh, sw), np.uint8)
                        bgdModel = np.zeros((1, 65), np.float64)
                        fgdModel = np.zeros((1, 65), np.float64)
                        rect = (int(sw * 0.05), int(sh * 0.04), int(sw * 0.90), int(sh * 0.92))
                        cv2.grabCut(small, mask, rect, bgdModel, fgdModel, 3, cv2.GC_INIT_WITH_RECT)

                        # Skin-mask prior refinement
                        ycrcb = cv2.cvtColor(small, cv2.COLOR_BGR2YCrCb)
                        skin = (
                            (ycrcb[:, :, 1] >= 133)
                            & (ycrcb[:, :, 1] <= 173)
                            & (ycrcb[:, :, 2] >= 77)
                            & (ycrcb[:, :, 2] <= 127)
                        )
                        mask[skin & (mask == cv2.GC_PR_BGD)] = cv2.GC_PR_FGD
                        cv2.grabCut(small, mask, None, bgdModel, fgdModel, 1, cv2.GC_INIT_WITH_MASK)

                        alpha = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)
                        alpha = cv2.bilateralFilter(alpha, 9, 75, 75)

                        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                        im_pil = Image.fromarray(rgb)
                        im_pil.putalpha(Image.fromarray(alpha))

                        bbox = im_pil.getbbox()
                        if bbox:
                            bx1, by1, bx2, by2 = bbox
                            bw, bh = bx2 - bx1, by2 - by1
                            side = max(bw, bh) + 24
                            square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                            cropped = im_pil.crop(bbox)
                            square.paste(cropped, ((side - bw) // 2, (side - bh) // 2), cropped)
                            im_pil = square

                        tmp_file = out_file.with_name(f"{out_file.stem}_tmp_{os.getpid()}_{threading.get_ident()}.png")
                        im_pil.save(tmp_file, "PNG", optimize=True)
                        tmp_file.replace(out_file)
                        return out_file
                except Exception as exc:
                    print(f"[NoBG] GrabCut fallback error: {exc}")

        return None

    def get_random_nobg(self, exclude_id: str = "") -> Optional[Dict[str, Any]]:
        """Select a random image and guarantee its clean background-removed cutout is ready."""
        import random
        all_items = self.scan_folder()
        if not all_items:
            return None

        candidates = [it for it in all_items if it["id"] != exclude_id] or all_items
        random.shuffle(candidates)

        for candidate in candidates[:8]:
            p = self.remove_background(candidate["id"])
            if p and p.exists() and p.stat().st_size > 1000:
                return {
                    "id": candidate["id"],
                    "title": candidate["title"],
                    "model": candidate["model"],
                    "category": candidate["category"],
                    "nobg_url": f"/api/image/nobg/{candidate['id']}?t={int(p.stat().st_mtime)}",
                    "thumb_url": f"/api/resize/{candidate['id']}?mode=exact_uploaded",
                }

        return None

    def prewarm_nobg_cache(self, count: int = 15):
        """Pre-extract random subjects in the background so 10-second transitions have zero delay."""
        try:
            import random
            items = self.scan_folder()
            if not items:
                return
            sample_set = random.sample(items, min(count, len(items)))
            for it in sample_set:
                self.remove_background(it["id"])
        except Exception as exc:
            print(f"[Prewarm NoBG] Warning: {exc}")

    # =========================================================================
    # RGB & LUMINANCE HISTOGRAM TELEMETRY
    # =========================================================================
    def compute_histogram_data(self, img_path: Path, bins: int = 64) -> Dict[str, List[float]]:
        try:
            if HAS_CV2:
                bgr = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
                if bgr is not None:
                    h, w = bgr.shape[:2]
                    if max(h, w) > 640:
                        bgr = cv2.resize(bgr, (640, int(640 * h / max(w, 1))), interpolation=cv2.INTER_AREA)
                    b_hist = cv2.calcHist([bgr], [0], None, [bins], [0, 256]).flatten()
                    g_hist = cv2.calcHist([bgr], [1], None, [bins], [0, 256]).flatten()
                    r_hist = cv2.calcHist([bgr], [2], None, [bins], [0, 256]).flatten()
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                    l_hist = cv2.calcHist([gray], [0], None, [bins], [0, 256]).flatten()

                    peak = max(
                        float(np.max(r_hist)),
                        float(np.max(g_hist)),
                        float(np.max(b_hist)),
                        float(np.max(l_hist)),
                        1.0,
                    )
                    return {
                        "r": [round(float(x) / peak, 3) for x in r_hist],
                        "g": [round(float(x) / peak, 3) for x in g_hist],
                        "b": [round(float(x) / peak, 3) for x in b_hist],
                        "luma": [round(float(x) / peak, 3) for x in l_hist],
                    }
        except Exception:
            pass
        return {"r": [], "g": [], "b": [], "luma": []}

    # =========================================================================
    # SMART SUBJECT-AWARE ASPECT-RATIO CROPPING
    # =========================================================================
    def _apply_smart_aspect_crop(
        self,
        rgb: np.ndarray,
        crop_aspect: str,
        skin_mask_2d: np.ndarray,
        faces: Optional[List[Dict[str, Any]]] = None,
    ) -> np.ndarray:
        """Crop frame to target aspect ratio centered on detected face or subject centroid with photographic headroom."""
        if not crop_aspect or crop_aspect == "original":
            return rgb

        ratios = {
            "16:9": 16.0 / 9.0,
            "9:16": 9.0 / 16.0,
            "4:5": 4.0 / 5.0,
            "1:1": 1.0,
            "2:3": 2.0 / 3.0,
        }
        target_r = ratios.get(crop_aspect)
        if not target_r:
            return rgb

        h, w = rgb.shape[:2]
        curr_r = w / max(h, 1)
        if abs(curr_r - target_r) < 0.02:
            return rgb

        # Prioritize primary detected face for perfect portrait headroom
        if faces and len(faces) > 0:
            primary_face = max(faces, key=lambda f: f["box"][2] * f["box"][3])
            fb = primary_face["box"]
            cx = float(fb[0] + fb[2] / 2.0)
            # Center on eyes/upper face with ~35% headroom in vertical crop
            cy = float(fb[1] + fb[3] * 0.40)
        else:
            # Fallback to subject centroid from skin/subject mask
            ys, xs = np.where(skin_mask_2d > 0.25)
            if len(xs) > 50:
                cx = float(np.mean(xs))
                cy = float(np.mean(ys) * 0.88)
            else:
                cx, cy = w / 2.0, h / 2.0

        if curr_r > target_r:
            new_w = int(round(h * target_r))
            new_h = h
            x0 = int(round(cx - new_w / 2.0))
            x0 = max(0, min(w - new_w, x0))
            y0 = 0
        else:
            new_w = w
            new_h = int(round(w / target_r))
            x0 = 0
            y0 = int(round(cy - new_h * 0.35))
            y0 = max(0, min(h - new_h, y0))

        return rgb[y0 : y0 + new_h, x0 : x0 + new_w]

    # =========================================================================
    # MULTI-STAGE 4K+ ENHANCEMENT PIPELINE (PORTRAIT AI + BOKEH + EYE POP + LUT)
    # =========================================================================
    def enhance_image(
        self,
        img_id: str,
        preset: str = "ultra_hot_4k",
        custom_params: Optional[Dict[str, Any]] = None,
        out_format: str = "jpg",
    ) -> Tuple[Optional[Path], Dict]:
        t0 = time.perf_counter()
        meta = self.get_image_by_id(img_id)
        if not meta:
            return None, {}

        src_path = self.source_dir / meta["filename"]
        if meta.get("is_animated"):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return src_path, {
                "cached": True,
                "elapsed_ms": elapsed_ms,
                "preset": preset,
                "preset_name": "4K Animated Loop",
                "original_resolution": f"{meta['width']}x{meta['height']}",
                "enhanced_resolution": f"{meta['width']}x{meta['height']}",
                "file_size_mb": meta["size_mb"],
                "skin_coverage_pct": 35.0,
                "histograms": {"original": {}, "enhanced": {}},
                "pipeline_stages": ["4K Animated Keyframe Loop", "Per-Frame Optical Grading"],
            }

        cfg = dict(PRESET_CONFIGS.get(preset, PRESET_CONFIGS["ultra_hot_4k"]))
        if custom_params:
            for k, v in custom_params.items():
                if v is not None and k in (
                    "target_long_edge",
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
                    cfg[k] = float(v)
                elif k in (
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
                    cfg[k] = bool(v)
                elif k in ("upscale_mode", "lut_name", "crop_aspect") and v:
                    cfg[k] = str(v)

        skin_mask_flag = 1 if cfg.get("skin_mask_aware", True) else 0
        auto_wb_flag = 1 if cfg.get("auto_exposure_wb", False) else 0
        mono_flag = 1 if cfg.get("is_monochrome", False) else 0
        vbw_flag = 1 if cfg.get("vintage_bw_tint", False) else 0
        retro_flag = 1 if cfg.get("retro_film", False) else 0
        neon_flag = 1 if cfg.get("neon_pop", False) else 0
        pro_sketch_flag = 1 if cfg.get("pro_pencil_sketch", False) else 0
        sketch_flag = 1 if (cfg.get("pencil_sketch", False) or pro_sketch_flag) else 0
        trauma_flag = 1 if cfg.get("traumatized_mode", False) else 0
        eye_val = float(cfg.get("eye_enhance", 0.45))
        bokeh_val = float(cfg.get("bokeh_blur", 0.0))
        grain_val = float(cfg.get("film_grain", 0.0))
        vignette_val = float(cfg.get("vignette", 0.0))
        intensity_val = float(cfg.get("preset_intensity", 1.0))
        crop_aspect = str(cfg.get("crop_aspect", "original"))
        upscale_mode = str(cfg.get("upscale_mode", "lanczos_edge"))
        lut_name = str(cfg.get("lut_name", "none"))
        fmt_ext = out_format.lower().lstrip(".")
        if fmt_ext not in ("jpg", "png", "webp"):
            fmt_ext = "jpg"

        param_sig = (
            f"{preset}_{int(cfg['target_long_edge'])}_"
            f"{cfg['skin_smooth']:.2f}_{cfg['detail_sharpen']:.2f}_"
            f"{cfg['micro_contrast']:.2f}_{cfg['depth_shadows']:.2f}_"
            f"{cfg['warmth']:.2f}_{cfg['vibrance']:.2f}_{cfg['highlight_bloom']:.2f}_"
            f"eye{eye_val:.2f}_bk{bokeh_val:.2f}_wb{auto_wb_flag}_"
            f"gr{grain_val:.2f}_vg{vignette_val:.2f}_in{intensity_val:.2f}_"
            f"mo{mono_flag}_vbw{vbw_flag}_ret{retro_flag}_ne{neon_flag}_sk{sketch_flag}_psk{pro_sketch_flag}_tr{trauma_flag}_"
            f"cr{crop_aspect.replace(':', '')}_sm{skin_mask_flag}_{upscale_mode}_{Path(lut_name).stem}"
        )
        out_filename = f"{img_id}_{param_sig}.{fmt_ext}"
        out_path = ENHANCED_CACHE_DIR / out_filename
        hist_cache_path = ENHANCED_CACHE_DIR / f"{img_id}_{param_sig}_meta.json"

        stages = []
        if auto_wb_flag:
            stages.append("Smart Skin-Protective Auto-Exposure & WB")
        if crop_aspect != "original":
            stages.append(f"Subject-Centered {crop_aspect} Framing")
        if upscale_mode == "real_esrgan_ai":
            stages.append("Real-ESRGAN Deep Neural Super-Resolution (4x)")
        elif upscale_mode == "ibp_super_res":
            stages.append("4K+ IBP Neural Super-Resolution")
        else:
            stages.append("4K+ Edge-Guided Super-Resolution")
        stages.append(
            "Pore-Retained Skin Frequency Separation"
            if skin_mask_flag
            else "Global Frequency-Separated Texture Refinement"
        )
        if eye_val > 0.05:
            stages.append("YuNet Landmark Iris Pop & Eye Catchlight")
        if bokeh_val > 0.05:
            stages.append("f/1.4 Silueta Subject-Separated Bokeh Blur")
        stages.append("CLAHE Local Depth & Filmic S-Curve")
        if lut_name and lut_name != "none":
            stages.append(f"3D LUT ({Path(lut_name).stem.replace('_', ' ')})")
        if neon_flag:
            stages.append("Tokyo Neon Specular & Split-Tone Chromatic Pop")
        if retro_flag:
            stages.append("Retro Matte Black-Lift & Nostalgic Split-Toning")
        if vbw_flag:
            stages.append("Vintage Silver-Gelatin B&W Contrast & Warm Archival Tint")
        elif mono_flag:
            stages.append("Panchromatic Platinum B&W Zone System")
        if pro_sketch_flag:
            stages.append("4-Scale Centered Retinex Graphite Shading (2H–8B)")
            stages.append("Edge-Tangent Flow (ETF) Directional Pencil Strokes")
            stages.append("Sub-Pixel XDoG + Scharr Contours & Kneaded-Eraser Catchlights")
        elif sketch_flag:
            stages.append("Multi-Scale Color-Dodge Graphite Shading (2B/4B/6B)")
            stages.append("XDoG + Anisotropic Scharr Contour Linework")
            stages.append("Directional Cross-Hatching & Archival Cotton Paper Tooth")
        if vignette_val > 0.02:
            stages.append(f"Optical Lens Vignette Falloff ({int(vignette_val * 100)}%)")
        if grain_val > 0.02 and not sketch_flag:
            stages.append(f"35mm Organic Film Grain Simulation ({int(grain_val * 100)}%)")
        if abs(intensity_val - 1.0) > 0.04:
            stages.append(f"Preset Blend Intensity ({int(intensity_val * 100)}%)")
        stages.append("Halo-Free Noise-Cored Micro-Sharpening")

        if out_path.exists() and out_path.stat().st_mtime >= src_path.stat().st_mtime:
            with Image.open(out_path) as enh_im:
                ew, eh = enh_im.size
            cached_extra = {}
            if hist_cache_path.exists():
                try:
                    cached_extra = json.loads(hist_cache_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            if "histograms" not in cached_extra:
                cached_extra["histograms"] = {
                    "original": self.compute_histogram_data(src_path),
                    "enhanced": self.compute_histogram_data(out_path),
                }
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return out_path, {
                "cached": True,
                "elapsed_ms": elapsed_ms,
                "preset": preset,
                "preset_name": cfg["name"],
                "original_resolution": f"{meta['width']}x{meta['height']}",
                "enhanced_resolution": f"{ew}x{eh}",
                "file_size_mb": round(out_path.stat().st_size / (1024 * 1024), 2),
                "skin_coverage_pct": cached_extra.get("skin_coverage_pct", 0.0),
                "sharpness_score": meta.get("sharpness_score", 0.0),
                "upscale_mode": upscale_mode,
                "lut_name": lut_name,
                "skin_mask_aware": bool(skin_mask_flag),
                "histograms": cached_extra.get("histograms", {}),
                "pipeline_stages": stages,
            }

        skin_coverage_pct = 0.0
        with self._enhance_sem:
            if out_path.exists() and out_path.stat().st_mtime >= src_path.stat().st_mtime:
                with Image.open(out_path) as enh_im:
                    ew, eh = enh_im.size
                cached_extra = {}
                if hist_cache_path.exists():
                    try:
                        cached_extra = json.loads(hist_cache_path.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                return out_path, {
                    "cached": True,
                    "elapsed_ms": elapsed_ms,
                    "preset": preset,
                    "preset_name": cfg["name"],
                    "original_resolution": f"{meta['width']}x{meta['height']}",
                    "enhanced_resolution": f"{ew}x{eh}",
                    "file_size_mb": round(out_path.stat().st_size / (1024 * 1024), 2),
                    "skin_coverage_pct": cached_extra.get("skin_coverage_pct", 0.0),
                    "sharpness_score": meta.get("sharpness_score", 0.0),
                    "upscale_mode": upscale_mode,
                    "lut_name": lut_name,
                    "skin_mask_aware": bool(skin_mask_flag),
                    "histograms": cached_extra.get("histograms", {}),
                    "pipeline_stages": stages,
                }

            if HAS_CV2:
                bgr = cv2.imread(str(src_path), cv2.IMREAD_COLOR)
                icc_bytes = None
                try:
                    with Image.open(src_path) as src_im_check:
                        icc_bytes = src_im_check.info.get("icc_profile")
                except Exception:
                    pass

                if bgr is None:
                    with Image.open(src_path) as pil_im:
                        bgr = cv2.cvtColor(np.array(pil_im.convert("RGB")), cv2.COLOR_RGB2BGR)
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                del bgr

                rgb, skin_coverage_pct = self._enhance_cv2_pipeline(rgb, cfg)
                orig_h, orig_w = rgb.shape[:2]

                if upscale_mode == "exact_1to1":
                    new_w, new_h = orig_w, orig_h
                else:
                    target_edge = int(cfg["target_long_edge"])
                    scale = max(1.0, target_edge / max(orig_w, orig_h, 1))
                    new_w = int(round(orig_w * scale))
                    new_h = int(round(orig_h * scale))

                if new_w != orig_w or new_h != orig_h:
                    if upscale_mode == "real_esrgan_ai":
                        rgb = self._upscale_realesrgan(rgb, new_w, new_h)
                    elif upscale_mode == "ibp_super_res":
                        up = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
                        down = cv2.resize(up, (orig_w, orig_h), interpolation=cv2.INTER_AREA)
                        # Compute IBP residual per channel in int16 to avoid 4K 3D float32 allocation
                        out_chans = []
                        for c in range(3):
                            err_c = rgb[:, :, c].astype(np.int16) - down[:, :, c].astype(np.int16)
                            err_up_c = cv2.resize(err_c, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
                            res_c = up[:, :, c].astype(np.int16) + ((err_up_c * 166) >> 8)
                            out_chans.append(np.clip(res_c, 0, 255).astype(np.uint8))
                            del err_c, err_up_c, res_c
                        del up, down, rgb
                        rgb = cv2.merge(out_chans)
                        del out_chans
                    else:
                        rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

                # Halo-Free, Noise-Cored Luminance Sharpening (Zero white ringing, zero color fringing)
                sharp_amount = float(cfg["detail_sharpen"])
                if sharp_amount > 0.5:
                    lab_s = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
                    l_chan = lab_s[:, :, 0].astype(np.float32)
                    l_blur = cv2.GaussianBlur(l_chan, (0, 0), sigmaX=1.1)
                    delta = l_chan - l_blur

                    # Noise coring: suppress small grain/noise deltas
                    noise_coring = np.clip((np.abs(delta) - 2.5) / 2.0, 0.0, 1.0)
                    gain = float((sharp_amount - 0.5) * 0.85)
                    # Overshoot clamp: avoid ugly white halo rings
                    max_overshoot = 24.0
                    delta_clamped = np.clip(delta * noise_coring * gain, -max_overshoot, max_overshoot)

                    lab_s[:, :, 0] = np.clip(l_chan + delta_clamped, 0, 255).astype(np.uint8)
                    rgb = cv2.cvtColor(lab_s, cv2.COLOR_LAB2RGB)
                    del lab_s, l_chan, l_blur, delta, delta_clamped

                # Export with 4:4:4 Chroma Subsampling & ICC profile preservation
                out_pil = Image.fromarray(rgb)
                del rgb
                save_kwargs = {}
                if icc_bytes:
                    save_kwargs["icc_profile"] = icc_bytes

                if fmt_ext == "png":
                    out_pil.save(out_path, format="PNG", optimize=True, **save_kwargs)
                elif fmt_ext == "webp":
                    out_pil.save(out_path, format="WEBP", quality=94, **save_kwargs)
                else:
                    out_pil.save(out_path, format="JPEG", quality=95, optimize=True, subsampling=0, **save_kwargs)
                del out_pil
            else:
                with Image.open(src_path) as pil_im:
                    pil_im = pil_im.convert("RGB")
                    orig_w, orig_h = pil_im.size
                    target_edge = int(cfg["target_long_edge"])
                    scale = max(1.0, min(2.5, target_edge / max(orig_w, orig_h, 1)))
                    new_w = int(round(orig_w * scale))
                    new_h = int(round(orig_h * scale))
                    if new_w != orig_w or new_h != orig_h:
                        pil_im = pil_im.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    enh_pil = self._enhance_pil_pipeline(pil_im, cfg)
                    enh_pil.save(out_path, "JPEG", quality=95, optimize=True, subsampling=0)

            histograms = {
                "original": self.compute_histogram_data(src_path),
                "enhanced": self.compute_histogram_data(out_path),
            }
            try:
                hist_cache_path.write_text(
                    json.dumps({"skin_coverage_pct": skin_coverage_pct, "histograms": histograms}),
                    encoding="utf-8",
                )
            except Exception:
                pass
            self.prune_disk_caches()

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return out_path, {
            "cached": False,
            "elapsed_ms": elapsed_ms,
            "preset": preset,
            "preset_name": cfg["name"],
            "original_resolution": f"{meta['width']}x{meta['height']}",
            "enhanced_resolution": f"{new_w}x{new_h}",
            "file_size_mb": round(out_path.stat().st_size / (1024 * 1024), 2),
            "skin_coverage_pct": skin_coverage_pct,
            "sharpness_score": meta.get("sharpness_score", 0.0),
            "upscale_mode": upscale_mode,
            "lut_name": lut_name,
            "skin_mask_aware": bool(skin_mask_flag),
            "histograms": histograms,
            "pipeline_stages": stages,
        }

    def _detect_skin_mask(
        self,
        rgb: np.ndarray,
        faces: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[np.ndarray, float]:
        """Adaptive skin detection: samples real complexion from detected face, falls back to broad YCrCb+HSV."""
        h, w = rgb.shape[:2]
        scale_m = min(1.0, 640.0 / max(w, h, 1))
        mw, mh = max(8, int(round(w * scale_m))), max(8, int(round(h * scale_m)))
        small = cv2.resize(rgb, (mw, mh), interpolation=cv2.INTER_AREA) if scale_m < 1.0 else rgb

        ycrcb = cv2.cvtColor(small, cv2.COLOR_RGB2YCrCb)
        hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)

        # Adaptive skin bounds derived from detected face
        if faces and len(faces) > 0:
            fb = faces[0]["box"]
            fx1 = max(0, int(fb[0] * scale_m))
            fy1 = max(0, int(fb[1] * scale_m))
            fx2 = min(mw, int((fb[0] + fb[2]) * scale_m))
            fy2 = min(mh, int((fb[1] + fb[3]) * scale_m))
            if (fx2 - fx1) > 10 and (fy2 - fy1) > 10:
                face_ycrcb = ycrcb[fy1:fy2, fx1:fx2]
                med_cr = float(np.median(face_ycrcb[:, :, 1]))
                med_cb = float(np.median(face_ycrcb[:, :, 2]))
                cr_low = int(np.clip(med_cr - 24, 125, 175))
                cr_high = int(np.clip(med_cr + 24, 135, 185))
                cb_low = int(np.clip(med_cb - 22, 70, 130))
                cb_high = int(np.clip(med_cb + 22, 85, 138))
                mask_ycrcb = cv2.inRange(
                    ycrcb,
                    np.array([30, cr_low, cb_low], dtype=np.uint8),
                    np.array([255, cr_high, cb_high], dtype=np.uint8),
                )
            else:
                mask_ycrcb = cv2.inRange(
                    ycrcb,
                    np.array([40, 132, 75], dtype=np.uint8),
                    np.array([250, 178, 130], dtype=np.uint8),
                )
        else:
            mask_ycrcb = cv2.inRange(
                ycrcb,
                np.array([40, 132, 75], dtype=np.uint8),
                np.array([250, 178, 130], dtype=np.uint8),
            )

        mask_hsv = cv2.inRange(
            hsv,
            np.array([0, 18, 50], dtype=np.uint8),
            np.array([28, 195, 255], dtype=np.uint8),
        )
        combined = cv2.bitwise_and(mask_ycrcb, mask_hsv)

        # Morphological noise cleanup (removes random wall/floor specks)
        clean_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, clean_kernel)

        coverage_pct = round(float(np.count_nonzero(combined)) * 100.0 / max(combined.size, 1), 1)
        feathered_s = cv2.GaussianBlur(combined.astype(np.float32) * np.float32(1.0 / 255.0), (0, 0), sigmaX=max(1.5, 4.0 * scale_m))
        feathered = cv2.resize(feathered_s, (w, h), interpolation=cv2.INTER_LINEAR) if scale_m < 1.0 else feathered_s
        return feathered[:, :, np.newaxis], coverage_pct

    def _enhance_cv2_pipeline(self, rgb: np.ndarray, cfg: Dict) -> Tuple[np.ndarray, float]:
        """Low-RAM, AI-guided OpenCV + NumPy enhancement pipeline with Portrait Intelligence, YuNet & Silueta."""
        # Detect faces and 5-point facial landmarks (eyes, nose, mouth)
        faces = self._detect_faces_and_eyes(rgb)

        skin_mask, skin_coverage_pct = self._detect_skin_mask(rgb, faces=faces)
        skin_mask_2d = skin_mask[:, :, 0]
        del skin_mask

        # 0A. Smart Aspect-Ratio Framing centered on subject/face
        crop_aspect = str(cfg.get("crop_aspect", "original"))
        if crop_aspect and crop_aspect != "original":
            rgb = self._apply_smart_aspect_crop(rgb, crop_aspect, skin_mask_2d, faces=faces)
            faces = self._detect_faces_and_eyes(rgb)
            skin_mask, skin_coverage_pct = self._detect_skin_mask(rgb, faces=faces)
            skin_mask_2d = skin_mask[:, :, 0]
            del skin_mask

        h, w = rgb.shape[:2]
        scale_m = min(1.0, 640.0 / max(w, h, 1))
        mw, mh = max(8, int(round(w * scale_m))), max(8, int(round(h * scale_m)))
        feathered_small = cv2.resize(skin_mask_2d, (mw, mh), interpolation=cv2.INTER_AREA) if scale_m < 1.0 else skin_mask_2d

        preset_intensity = float(cfg.get("preset_intensity", 1.0))
        need_orig_blend = abs(preset_intensity - 1.0) > 0.02
        orig_raw_rgb = rgb.copy() if need_orig_blend else None

        # 0B. Smart Skin-Protective Auto-Exposure & Robust White-Balance Normalization
        if cfg.get("auto_exposure_wb", False):
            lab_wb = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
            l_w, a_w, b_w = cv2.split(lab_wb)
            del lab_wb

            # Robust illuminant estimation: measure chrominance only on neutral/low-saturation midtones
            hsv_wb = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
            sat = hsv_wb[:, :, 1]
            del hsv_wb
            neutral_mask = (sat < 60) & (l_w > 40) & (l_w < 220)
            if np.count_nonzero(neutral_mask) > 100:
                a_mean = float(np.mean(a_w[neutral_mask]))
                b_mean = float(np.mean(b_w[neutral_mask]))
            else:
                a_mean = float(cv2.mean(a_w)[0])
                b_mean = float(cv2.mean(b_w)[0])

            # Soft shift towards balanced neutral warmth without turning red dresses cyan
            a_shift = float(np.clip((a_mean - 128.0) * 0.35, -12.0, 12.0))
            b_shift = float(np.clip((b_mean - 130.0) * 0.35, -14.0, 14.0))
            a_lut = np.clip(np.arange(256, dtype=np.float32) - a_shift, 0, 255).astype(np.uint8)
            b_lut = np.clip(np.arange(256, dtype=np.float32) - b_shift, 0, 255).astype(np.uint8)
            a_w = cv2.LUT(a_w, a_lut)
            b_w = cv2.LUT(b_w, b_lut)

            if skin_coverage_pct > 3.0:
                l_small = cv2.resize(l_w, (mw, mh), interpolation=cv2.INTER_AREA) if scale_m < 1.0 else l_w
                skin_luma = float(np.mean(l_small[feathered_small > 0.3]))
            else:
                skin_luma = float(cv2.mean(l_w)[0])
            if skin_luma > 10.0:
                gamma = float(np.clip(np.log(148.0 / 255.0) / np.log(max(skin_luma, 15.0) / 255.0), 0.78, 1.28))
                l_lut = np.clip(255.0 * np.power(np.arange(256, dtype=np.float32) / 255.0, gamma), 0, 255).astype(np.uint8)
                l_w = cv2.LUT(l_w, l_lut)

            rgb = cv2.cvtColor(cv2.merge((l_w, a_w, b_w)), cv2.COLOR_LAB2RGB)
            del l_w, a_w, b_w

        use_skin_mask = bool(cfg.get("skin_mask_aware", True))

        # 1. Frequency separation skin smoothing with Authentic Micro-Pore Retention (Never Plastic)
        smooth_strength = float(cfg["skin_smooth"])
        if smooth_strength > 0.05:
            small = cv2.resize(rgb, (max(1, w // 2), max(1, h // 2)), interpolation=cv2.INTER_AREA)
            sigma_color = int(18 + smooth_strength * 26)
            sigma_space = int(7 + smooth_strength * 12)
            smoothed_small = cv2.bilateralFilter(small, d=7, sigmaColor=sigma_color, sigmaSpace=sigma_space)
            smoothed = cv2.resize(smoothed_small, (w, h), interpolation=cv2.INTER_LINEAR)
            del small, smoothed_small

            # Extract genuine fine skin pores (high-pass band) to prevent waxy doll look
            fine_blur = cv2.GaussianBlur(rgb, (0, 0), sigmaX=0.9).astype(np.float32)
            micro_pores = rgb.astype(np.float32) - fine_blur
            del fine_blur

            coarse_blur = cv2.GaussianBlur(rgb, (0, 0), sigmaX=1.8).astype(np.float32)
            blemish_layer = coarse_blur - smoothed.astype(np.float32)
            del coarse_blur

            if use_skin_mask:
                eff_mask = (skin_mask_2d[:, :, None] * float(smooth_strength * 0.75)).astype(np.float32)
            else:
                eff_mask = np.full((h, w, 1), float(smooth_strength * 0.70), dtype=np.float32)

            # Smooth blotches & redness while injecting authentic pore texture (28% retention)
            rgb_f = rgb.astype(np.float32)
            rgb_smoothed = rgb_f - (blemish_layer * eff_mask) + (micro_pores * eff_mask * 0.28)
            rgb = np.clip(rgb_smoothed, 0, 255).astype(np.uint8)
            del rgb_f, rgb_smoothed, blemish_layer, micro_pores, eff_mask, smoothed

        # 2. Iris Micro-Contrast & Catchlight Enhancer (Landmark-Guided directly on Eyes)
        eye_enhance = float(cfg.get("eye_enhance", 0.45))
        if eye_enhance > 0.05 and not cfg.get("traumatized_mode", False):
            eye_mask = np.zeros((h, w), dtype=np.float32)
            if faces:
                for f in faces:
                    re, le = f["right_eye"], f["left_eye"]
                    eye_dist = float(np.linalg.norm(re - le))
                    rad_x = max(5, int(eye_dist * 0.18))
                    rad_y = max(4, int(eye_dist * 0.13))
                    cv2.ellipse(eye_mask, (int(round(re[0])), int(round(re[1]))), (rad_x, rad_y), 0, 0, 360, 1.0, -1)
                    cv2.ellipse(eye_mask, (int(round(le[0])), int(round(le[1]))), (rad_x, rad_y), 0, 0, 360, 1.0, -1)
                eye_mask = cv2.GaussianBlur(eye_mask, (0, 0), sigmaX=max(1.5, 3.0 * scale_m))
            else:
                k_s = max(3, int(round(25 * scale_m)) | 1)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_s, k_s))
                skin_dilated = cv2.dilate((feathered_small > 0.25).astype(np.uint8) * 255, kernel, iterations=2)
                f_zone_s = (skin_dilated > 0).astype(np.float32) * (
                    np.float32(1.0) - np.clip(feathered_small * np.float32(1.3), np.float32(0.0), np.float32(1.0))
                )
                f_zone_s = cv2.GaussianBlur(f_zone_s, (0, 0), sigmaX=max(1.0, 4.0 * scale_m))
                eye_mask = cv2.resize(f_zone_s, (w, h), interpolation=cv2.INTER_LINEAR) if scale_m < 1.0 else f_zone_s

            if np.count_nonzero(eye_mask > 0.05) > 0:
                gray_u8 = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
                catch_pop = np.clip((gray_u8.astype(np.float32) - 170.0) * float(eye_enhance * 0.35), 0.0, float(eye_enhance * 26.0))
                catch_pop *= eye_mask

                eye_mask_3d = eye_mask[:, :, None]
                blur_eyes = cv2.GaussianBlur(rgb, (0, 0), sigmaX=1.2).astype(np.float32)
                diff_eyes = (rgb.astype(np.float32) - blur_eyes) * (eye_mask_3d * float(eye_enhance * 1.5))
                rgb = np.clip(rgb.astype(np.float32) + diff_eyes + catch_pop[:, :, None], 0, 255).astype(np.uint8)
                del blur_eyes, diff_eyes, catch_pop, eye_mask, eye_mask_3d

        # 3. f/1.4 Subject-Separated Bokeh Blur (Silueta Person Segmentation: Hair & Clothes 100% Protected)
        bokeh_strength = float(cfg.get("bokeh_blur", 0.0))
        if bokeh_strength > 0.05:
            fg_mask_2d = self._get_subject_mask(rgb)
            sigma_bg = 4.0 + bokeh_strength * 20.0
            bw_h, bw_w = max(2, h // 2), max(2, w // 2)
            rgb_half = cv2.resize(rgb, (bw_w, bw_h), interpolation=cv2.INTER_AREA)
            bg_blurred_half = cv2.GaussianBlur(rgb_half, (0, 0), sigmaX=sigma_bg * 0.5)
            bg_gray_h = cv2.cvtColor(bg_blurred_half, cv2.COLOR_RGB2GRAY)
            _, bokeh_spots = cv2.threshold(bg_gray_h, 195, 255, cv2.THRESH_BINARY)
            bokeh_discs = cv2.dilate(bokeh_spots, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            bg_boosted_half = cv2.addWeighted(
                bg_blurred_half,
                1.0,
                cv2.bitwise_and(bg_blurred_half, bg_blurred_half, mask=bokeh_discs),
                bokeh_strength * 0.45,
                0,
            )
            bg_boosted = cv2.resize(bg_boosted_half, (w, h), interpolation=cv2.INTER_LINEAR)
            del rgb_half, bg_blurred_half, bg_gray_h, bokeh_spots, bokeh_discs, bg_boosted_half

            fg_3d = fg_mask_2d[:, :, None]
            rgb = np.clip(rgb.astype(np.float32) * fg_3d + bg_boosted.astype(np.float32) * (1.0 - fg_3d), 0, 255).astype(np.uint8)
            del bg_boosted, fg_mask_2d, fg_3d

        # 4 & 5. Local Depth, Shadows & Golden Warmth in LAB color space (via 256-entry LUTs)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        del lab

        clip_limit = max(0.8, (cfg["micro_contrast"] - 0.8) * 2.2)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l_chan)

        clahe_mix = min(0.65, max(0.15, (cfg["micro_contrast"] - 1.0) * 0.9 + 0.25))
        l_mixed = cv2.addWeighted(l_clahe, clahe_mix, l_chan, 1.0 - clahe_mix, 0)
        del l_chan, l_clahe

        depth_strength = float(cfg["depth_shadows"])
        if abs(depth_strength - 1.0) > 0.02:
            x = np.linspace(0, 1, 256, dtype=np.float32)
            contrast_k = 1.0 + (depth_strength - 1.0) * 0.85
            curve = np.power(x, contrast_k) / (
                np.power(x, contrast_k) + np.power(1.0 - x, contrast_k) + 1e-6
            )
            lut = np.clip((curve * 255.0) * 0.55 + np.arange(256, dtype=np.float32) * 0.45, 0, 255).astype(np.uint8)
            l_mixed = cv2.LUT(l_mixed, lut)

        warmth = float(cfg["warmth"])
        if abs(warmth - 1.0) > 0.01:
            a_lut = np.clip(np.arange(256, dtype=np.float32) + (warmth - 1.0) * 14.0, 0, 255).astype(np.uint8)
            b_lut = np.clip(np.arange(256, dtype=np.float32) + (warmth - 1.0) * 22.0, 0, 255).astype(np.uint8)
            a_chan = cv2.LUT(a_chan, a_lut)
            b_chan = cv2.LUT(b_chan, b_lut)

        rgb = cv2.cvtColor(cv2.merge((l_mixed, a_chan, b_chan)), cv2.COLOR_LAB2RGB)
        del l_mixed, a_chan, b_chan

        # 6. Smart Vibrance via 256-entry Saturation LUT
        vibrance = float(cfg["vibrance"])
        if abs(vibrance - 1.0) > 0.02:
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
            h_c, s_c, v_c = cv2.split(hsv)
            del hsv
            s_idx = np.arange(256, dtype=np.float32)
            vib_gain = (vibrance - 1.0) * (1.0 - (s_idx / 255.0) * 0.65)
            s_lut = np.clip(s_idx * (1.0 + vib_gain), 0, 255).astype(np.uint8)
            s_c = cv2.LUT(s_c, s_lut)
            rgb = cv2.cvtColor(cv2.merge((h_c, s_c, v_c)), cv2.COLOR_HSV2RGB)
            del h_c, s_c, v_c

        # 7. Optional 3D .cube LUT Grading
        lut_name = str(cfg.get("lut_name", "none"))
        if lut_name and lut_name != "none":
            rgb = self._apply_3d_lut(rgb, lut_name, strength=0.72)

        # 8. Specular highlight bloom for glamorous lighting (computed at 1/4 resolution)
        bloom = float(cfg.get("highlight_bloom", 0.15))
        if bloom > 0.02:
            bh_s, bw_s = max(2, h // 4), max(2, w // 4)
            small_b = cv2.resize(rgb, (bw_s, bh_s), interpolation=cv2.INTER_AREA)
            gray_b = cv2.cvtColor(small_b, cv2.COLOR_RGB2GRAY)
            _, bright_mask = cv2.threshold(gray_b, 210, 255, cv2.THRESH_BINARY)
            bright_regions = cv2.bitwise_and(small_b, small_b, mask=bright_mask)
            glow_small = cv2.GaussianBlur(bright_regions, (0, 0), sigmaX=3.0)
            glow = cv2.resize(glow_small, (w, h), interpolation=cv2.INTER_LINEAR)
            rgb = cv2.addWeighted(rgb, 1.0, glow, bloom * 0.55, 0)
            del small_b, gray_b, bright_mask, bright_regions, glow_small, glow

        # 9. Tokyo Neon Specular & Split-Tone Chromatic Pop
        if cfg.get("neon_pop", False):
            hsv_neon = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
            hn, sn, vn = cv2.split(hsv_neon)
            del hsv_neon
            neon_mask = (((hn >= 80) & (hn <= 125)) | ((hn >= 140) & (hn <= 175)))
            sn_boost = np.clip(sn.astype(np.float32) * 1.45, 0, 255).astype(np.uint8)
            vn_boost = np.clip(vn.astype(np.float32) * 1.20, 0, 255).astype(np.uint8)
            sn = np.where(neon_mask, sn_boost, sn)
            vn = np.where(neon_mask, vn_boost, vn)
            rgb = cv2.cvtColor(cv2.merge((hn, sn, vn)), cv2.COLOR_HSV2RGB)
            del hn, sn, vn, neon_mask, sn_boost, vn_boost

        # 9B. Retro Analog Film Emulation (warm faded colors, lifted matte shadows & nostalgic split-toning via 256-entry LUTs)
        if cfg.get("retro_film", False) and not cfg.get("is_monochrome", False) and not cfg.get("pencil_sketch", False):
            x_r = np.linspace(0.0, 1.0, 256, dtype=np.float32)
            # Matte faded S-curve: lift blacks to ~20 and compress peak highlights to ~244
            s_curve = np.power(x_r, 1.12) / (np.power(x_r, 1.12) + np.power(1.0 - x_r, 1.12) + 1e-6)
            faded_base = 20.0 + s_curve * 224.0
            sh_w = np.clip(1.0 - x_r * 1.6, 0.0, 1.0)
            hi_w = np.clip((x_r - 0.35) * 1.5, 0.0, 1.0)
            lut_r = np.clip(faded_base + hi_w * 11.0 + sh_w * 6.0, 0, 255).astype(np.uint8)
            lut_g = np.clip(faded_base + hi_w * 5.0 + sh_w * 2.0, 0, 255).astype(np.uint8)
            lut_b = np.clip(faded_base - hi_w * 14.0 + sh_w * 4.0, 0, 255).astype(np.uint8)
            r_c, g_c, b_c = cv2.split(rgb)
            rgb = cv2.merge((cv2.LUT(r_c, lut_r), cv2.LUT(g_c, lut_g), cv2.LUT(b_c, lut_b)))
            del r_c, g_c, b_c

        # 10. Panchromatic Platinum Fine-Art & Vintage Silver-Gelatin B&W Zone System
        if cfg.get("is_monochrome", False) and not cfg.get("pencil_sketch", False) and not cfg.get("traumatized_mode", False):
            is_vintage_bw = bool(cfg.get("vintage_bw_tint", False))
            # Classic red/orange filter weights for dramatic portrait skin luminosity & dark skies
            luma_mat = np.array([[0.52, 0.38, 0.10] if is_vintage_bw else [0.48, 0.42, 0.10]], dtype=np.float32)
            gray_u = cv2.transform(rgb, luma_mat)
            clahe_mono = cv2.createCLAHE(clipLimit=2.65 if is_vintage_bw else 2.4, tileGridSize=(8, 8))
            gray_clahe = clahe_mono.apply(gray_u)
            x_m = np.linspace(0, 1, 256, dtype=np.float32)
            gamma_m = 1.32 if is_vintage_bw else 1.25
            curve_m = np.power(x_m, gamma_m) / (np.power(x_m, gamma_m) + np.power(1.0 - x_m, gamma_m) + 1e-6)
            if is_vintage_bw:
                # Lifted vintage silver-halide darkroom blacks + subtle warm archival paper tone
                toned_base = 8.0 + curve_m * 242.0
                mid_tint = 4.0 * x_m * (1.0 - x_m)
                lut_mr = np.clip(toned_base + mid_tint * 6.0, 0, 255).astype(np.uint8)
                lut_mg = np.clip(toned_base + mid_tint * 3.0, 0, 255).astype(np.uint8)
                lut_mb = np.clip(toned_base - mid_tint * 5.0, 0, 255).astype(np.uint8)
                rgb = cv2.merge((cv2.LUT(gray_clahe, lut_mr), cv2.LUT(gray_clahe, lut_mg), cv2.LUT(gray_clahe, lut_mb)))
            else:
                lut_m = np.clip(curve_m * 255.0, 0, 255).astype(np.uint8)
                gray_toned = cv2.LUT(gray_clahe, lut_m)
                rgb = cv2.cvtColor(gray_toned, cv2.COLOR_GRAY2RGB)
                del gray_toned
            del gray_u, gray_clahe

        # 10B. Master & Pro Hyper-Realistic Graphite Pencil Sketch Engine
        is_sketch = bool(cfg.get("pencil_sketch", False) or cfg.get("pro_pencil_sketch", False))
        if is_sketch:
            rgb = self._apply_realistic_pencil_sketch(rgb, skin_mask_2d, cfg)

        # 10C. Traumatized Mr. Incredible Nightmare Mode
        if cfg.get("traumatized_mode", False):
            rgb = self._apply_traumatized_nightmare(rgb, skin_mask_2d, faces, cfg)

        # 11. Optical Lens Vignette Corner Falloff (computed at 1/4 resolution, applied per-channel)
        vignette_amount = float(cfg.get("vignette", 0.0))
        if vignette_amount > 0.02:
            vh_s, vw_s = max(8, h // 4), max(8, w // 4)
            cy, cx = vh_s / 2.0, vw_s / 2.0
            max_dist = float(np.sqrt(cx**2 + cy**2))
            y_idx, x_idx = np.ogrid[:vh_s, :vw_s]
            dist = np.sqrt((x_idx - cx)**2 + (y_idx - cy)**2).astype(np.float32) / max_dist
            falloff = np.clip((dist - np.float32(0.35)) / np.float32(0.65), np.float32(0.0), np.float32(1.0))
            if is_sketch:
                vig_small = np.float32(1.0) - np.power(falloff, 2.1) * np.float32(vignette_amount * 0.32)
            elif cfg.get("traumatized_mode", False):
                vig_small = np.float32(1.0) - np.power(falloff, 1.4) * np.float32(vignette_amount * 0.95)
            else:
                vig_small = np.float32(1.0) - np.power(falloff, 1.8) * np.float32(vignette_amount * 0.85)
            vig_mask = cv2.resize(vig_small, (w, h), interpolation=cv2.INTER_LINEAR)
            out_chans = [np.clip(rgb[:, :, c].astype(np.float32) * vig_mask, 0, 255).astype(np.uint8) for c in range(3)]
            rgb = cv2.merge(out_chans)
            del vig_small, vig_mask, out_chans

        # 12. 35mm Organic Film Grain Simulation (tiled 512x512 Gaussian noise + 256-entry midtone LUT)
        grain_amount = float(cfg.get("film_grain", 0.0))
        if grain_amount > 0.02 and not is_sketch:
            tiles = self._get_sketch_stroke_tiles()
            noise_tile = (tiles["paper"] * np.float32(grain_amount * 26.0)).astype(np.int16)
            ts = tiles["tile_sz"]
            gray_u8 = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            l_norm = np.arange(256, dtype=np.float32) / 255.0
            mid_lut = np.clip(4.0 * l_norm * (1.0 - l_norm) * 255.0, 0, 255).astype(np.uint8)
            mid_w = cv2.LUT(gray_u8, mid_lut)
            del gray_u8
            reps_y = (h + ts - 1) // ts
            reps_x = (w + ts - 1) // ts
            full_noise = cv2.repeat(noise_tile, reps_y, reps_x)[:h, :w]
            grain_delta = ((full_noise.astype(np.int32) * mid_w.astype(np.int32)) >> 8).astype(np.int16)
            del full_noise, mid_w
            out_chans = [np.clip(rgb[:, :, c].astype(np.int16) + grain_delta, 0, 255).astype(np.uint8) for c in range(3)]
            rgb = cv2.merge(out_chans)
            del grain_delta, out_chans

        # 13. Dynamic Preset Blend Intensity (0% Raw to 150% Overdrive)
        if need_orig_blend and orig_raw_rgb is not None:
            if preset_intensity <= 1.0:
                rgb = cv2.addWeighted(rgb, preset_intensity, orig_raw_rgb, 1.0 - preset_intensity, 0)
            else:
                boost_gain = preset_intensity - 1.0
                diff = cv2.subtract(rgb, orig_raw_rgb)
                rgb = cv2.addWeighted(rgb, 1.0, diff, boost_gain, 0)

        return rgb, skin_coverage_pct

    @staticmethod
    def _fast_gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
        """Multi-resolution Gaussian blur that accelerates wide-radius Retinex/Dodge blurs by 10x."""
        if sigma <= 0.5:
            return img.copy()
        if sigma <= 6.0:
            return cv2.GaussianBlur(img, (0, 0), sigmaX=sigma)
        h, w = img.shape[:2]
        factor = min(8, max(2, int(sigma / 4.0)))
        sw, sh = max(2, w // factor), max(2, h // factor)
        small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
        blurred_small = cv2.GaussianBlur(small, (0, 0), sigmaX=sigma / factor)
        return cv2.resize(blurred_small, (w, h), interpolation=cv2.INTER_LINEAR)

    def _get_sketch_stroke_tiles(self) -> Dict[str, np.ndarray]:
        """Precompute and cache seamless 512x512 multi-orientation graphite stroke and cotton paper tiles."""
        cached = getattr(self, "_sketch_tiles_cache", None)
        if cached is not None:
            return cached

        tile_sz = 512
        rng = np.random.RandomState(2026)
        base_noise = rng.normal(0.0, 1.0, (tile_sz, tile_sz)).astype(np.float32)
        base_noise2 = rng.normal(0.0, 1.0, (tile_sz, tile_sz)).astype(np.float32)

        def make_periodic_stroke_tile(noise_tile: np.ndarray, angle_deg: float, length: int = 13) -> np.ndarray:
            pad = length
            padded = np.pad(noise_tile, ((pad, pad), (pad, pad)), mode="wrap")
            kern = np.zeros((length, length), dtype=np.float32)
            c = (length - 1) / 2.0
            rad = np.deg2rad(angle_deg)
            dx, dy = np.cos(rad), np.sin(rad)
            for t in np.linspace(-c, c, length * 2):
                x = int(round(c + t * dx))
                y = int(round(c + t * dy))
                if 0 <= x < length and 0 <= y < length:
                    kern[y, x] += 1.0
            kern /= max(float(np.sum(kern)), 1e-5)
            filtered = cv2.filter2D(padded, cv2.CV_32F, kern, borderType=cv2.BORDER_REFLECT_101)
            cropped = filtered[pad : pad + tile_sz, pad : pad + tile_sz]
            return (cropped - float(np.mean(cropped))) / max(float(np.std(cropped)), 1e-5)

        paper_padded = np.pad(base_noise, ((6, 6), (6, 6)), mode="wrap")
        paper_blur = cv2.GaussianBlur(paper_padded, (0, 0), sigmaX=0.9)[6 : 6 + tile_sz, 6 : 6 + tile_sz]
        paper_tile = (paper_blur - float(np.mean(paper_blur))) / max(float(np.std(paper_blur)), 1e-5)

        tiles = {
            "s_0": make_periodic_stroke_tile(base_noise, 0.0, 13),
            "s_45": make_periodic_stroke_tile(base_noise, 45.0, 13),
            "s_90": make_periodic_stroke_tile(base_noise, 90.0, 13),
            "s_135": make_periodic_stroke_tile(base_noise2, 135.0, 13),
            "paper": paper_tile,
            "tile_sz": tile_sz,
        }
        self._sketch_tiles_cache = tiles
        return tiles

    def _apply_realistic_pencil_sketch(
        self, rgb: np.ndarray, skin_mask_2d: np.ndarray, cfg: Dict[str, Any]
    ) -> np.ndarray:
        """
        Professional Hyper-Realistic Graphite Pencil Portrait Engine (Low-RAM Block-Tiled Architecture):
        1. Orthochromatic-Panchromatic portrait luminance + dual-scale CLAHE (hair strands + 3D bone structure)
        2. Full-resolution Tortillon (paper blending stump) edge-preserving bilateral skin conditioning
        3. 4-Scale Centered Retinex / Color-Dodge Shading (2H / HB / 2B / 4B / 6B / 8B) — in-place accumulated
        4. Coherent Multi-Scale XDoG + Sub-Pixel Anisotropic Scharr Structural Linework
        5. Structure-Tensor Edge-Tangent Flow (ETF) Directional Pencil Strokes (512x512 block-tiled)
        6. Kneaded-Eraser Specular Eye Catchlights & Authentic Staedtler Lumograph Lead on Bristol Paper
        """
        h, w = rgb.shape[:2]
        res_scale = max(0.65, min(h, w) / 1080.0)
        is_pro_mode = bool(cfg.get("pro_pencil_sketch", False))

        # 1. Orthochromatic-Panchromatic Portrait Luminance via cv2.transform
        luma_mat = np.array([[0.28, 0.56, 0.16]], dtype=np.float32)
        luma_raw = cv2.transform(rgb, luma_mat).astype(np.float32)
        luma_u8 = luma_raw.astype(np.uint8)

        clahe_fine = cv2.createCLAHE(clipLimit=2.15, tileGridSize=(8, 8)).apply(luma_u8)
        clahe_form = cv2.createCLAHE(clipLimit=1.75, tileGridSize=(4, 4)).apply(luma_u8)
        luma_f = cv2.addWeighted(luma_raw, 0.45, clahe_form.astype(np.float32), 0.30, 0.0)
        cv2.scaleAdd(clahe_fine.astype(np.float32), 0.25, luma_f, dst=luma_f)
        del clahe_fine, clahe_form, luma_u8

        luma_smooth = cv2.bilateralFilter(luma_f.astype(np.uint8), d=5, sigmaColor=22, sigmaSpace=6).astype(
            np.float32
        )

        use_skin = bool(cfg.get("skin_mask_aware", True))
        skin_smooth_val = float(cfg.get("skin_smooth", 0.45))
        if use_skin:
            stump_weight = np.clip(
                skin_mask_2d * np.float32(0.45 + skin_smooth_val * 0.35) + np.float32(0.08),
                np.float32(0.0),
                np.float32(0.72),
            )
        else:
            stump_weight = np.full((h, w), np.float32(min(0.68, skin_smooth_val * 0.55)), dtype=np.float32)

        base_luma = luma_f
        base_luma *= np.float32(1.0) - stump_weight
        luma_smooth *= stump_weight
        base_luma += luma_smooth
        del luma_smooth

        # 2. 4-Scale Centered Retinex / Color-Dodge Graphite Form accumulated in-place
        depth_val = float(cfg.get("depth_shadows", 1.35))
        contrast_val = float(cfg.get("micro_contrast", 1.45))
        gamma_boost = float(max(0.75, 1.0 + (depth_val - 1.25) * 0.45 + (contrast_val - 1.35) * 0.40))

        dodge_shaded = np.zeros((h, w), dtype=np.float32)
        num_luma = base_luma + np.float32(2.0)
        c_micro = 0.16 if is_pro_mode else 0.22

        for idx, (s_val, knee, p_exp) in enumerate(
            (
                (max(1.2, 1.8 * res_scale), 1.014, 2.0),
                (max(3.5, 5.5 * res_scale), 1.022, 2.4),
                (max(11.0, 18.0 * res_scale), 1.032, 2.55),
                (max(34.0, 56.0 * res_scale), 1.040, 2.35),
            )
        ):
            b_arr = self._fast_gaussian_blur(base_luma, s_val)
            b_arr *= np.float32(knee)
            b_arr += np.float32(2.0)
            np.divide(num_luma, b_arr, out=b_arr)
            np.clip(b_arr, np.float32(0.0), np.float32(1.0), out=b_arr)
            cv2.pow(b_arr, p_exp * gamma_boost, dst=b_arr)
            if idx == 0:
                b_arr *= np.float32(c_micro) * (np.float32(1.0) - np.float32(0.58) * stump_weight)
            elif idx == 1:
                b_arr *= np.float32(0.28) * (np.float32(1.0) - np.float32(0.22) * stump_weight)
            elif idx == 2:
                b_arr *= np.float32(0.30) + np.float32(0.08) * stump_weight
            else:
                b_arr *= (
                    np.float32(1.0 - c_micro - 0.58)
                    + np.float32(0.58 * c_micro + 0.28 * 0.22 - 0.08) * stump_weight
                )
            dodge_shaded += b_arr
            del b_arr
        del num_luma

        # 3. Accurate 3D Chiaroscuro Tonal Value Mapping
        high_clip = np.float32(0.965 if is_pro_mode else 0.925)
        tonal_curve = np.clip(
            (base_luma * np.float32(1.0 / 255.0) - np.float32(0.015)) / high_clip,
            np.float32(0.0),
            np.float32(1.0),
        )
        cv2.pow(tonal_curve, 1.06 if is_pro_mode else 0.96, dst=tonal_curve)
        tonal_mix = np.float32(0.56 if is_pro_mode else 0.44)
        tonal_curve *= tonal_mix
        tonal_curve += np.float32(1.0 - tonal_mix)
        dodge_shaded *= tonal_curve
        graphite_form = dodge_shaded
        del tonal_curve

        # 4. Precision Anatomical Linework (Multi-Scale XDoG + Sub-Pixel Anisotropic Scharr Contours)
        sharp_val = float(cfg.get("detail_sharpen", 1.80))
        sharp_gain = np.float32(max(0.65, 0.75 + (sharp_val - 1.0) * 0.45))

        g1 = self._fast_gaussian_blur(base_luma, max(0.6, 0.75 * res_scale))
        g2 = self._fast_gaussian_blur(base_luma, max(1.2, 1.50 * res_scale))
        g1 -= g2
        del g2
        g1 *= np.float32(-1.0 / 255.0)
        g1 -= np.float32(0.0025) + stump_weight * np.float32(0.0055)
        g1 *= np.float32(20.5) * sharp_gain
        np.clip(g1, np.float32(0.0), np.float32(0.85), out=g1)
        xdog_line = np.float32(1.0) - g1
        del g1

        gx = cv2.Scharr(base_luma, cv2.CV_32F, 1, 0)
        gy = cv2.Scharr(base_luma, cv2.CV_32F, 0, 1)
        del base_luma
        gx *= np.float32(1.0 / 16.0)
        gy *= np.float32(1.0 / 16.0)
        grad_mag = cv2.magnitude(gx, gy)
        grad_norm = grad_mag * np.float32(1.0 / 255.0)
        scharr_line = np.clip(
            (grad_norm - (np.float32(0.045) + stump_weight * np.float32(0.072))) * (np.float32(0.88) * sharp_gain),
            np.float32(0.0),
            np.float32(0.84),
        )
        scharr_line = np.float32(1.0) - scharr_line

        xdog_line *= np.float32(0.52)
        scharr_line *= np.float32(0.48)
        xdog_line += scharr_line
        del scharr_line
        graphite_form *= xdog_line
        del xdog_line
        sketch_val = np.clip(graphite_form, np.float32(0.0), np.float32(1.0), out=graphite_form)

        # 5. Structure-Tensor Edge-Tangent Flow (ETF) Directional Pencil Strokes (512x512 Block-Tiled)
        grain_cfg = float(cfg.get("film_grain", 0.14 if is_pro_mode else 0.18))
        hatch_strength = float((0.09 if is_pro_mode else 0.12) + grain_cfg * 0.35)
        if hatch_strength > 0.015:
            tiles = self._get_sketch_stroke_tiles()
            tile_sz = tiles["tile_sz"]
            t0_tile = tiles["s_0"]
            t45_tile = tiles["s_45"]
            t90_tile = tiles["s_90"]
            t135_tile = tiles["s_135"]
            tpaper_tile = tiles["paper"]
            c_skin_damp = np.float32(0.48 if is_pro_mode else 0.35)
            c_h_prim = np.float32(0.65 * hatch_strength)
            c_h_cross = np.float32(0.45 * hatch_strength)
            c_h_tooth = np.float32(0.30 * hatch_strength)

            for y0 in range(0, h, tile_sz):
                y1 = min(h, y0 + tile_sz)
                bh = y1 - y0
                s0_b = t0_tile[:bh, :]
                s45_b = t45_tile[:bh, :]
                s90_b = t90_tile[:bh, :]
                s135_b = t135_tile[:bh, :]
                sp_b = tpaper_tile[:bh, :]
                for x0 in range(0, w, tile_sz):
                    x1 = min(w, x0 + tile_sz)
                    bw = x1 - x0
                    gx_b = gx[y0:y1, x0:x1]
                    gy_b = gy[y0:y1, x0:x1]
                    mag_b = grad_mag[y0:y1, x0:x1] + np.float32(1e-5)
                    tx_b = -gy_b / mag_b
                    ty_b = gx_b / mag_b
                    p0 = tx_b * tx_b
                    p45 = np.float32(0.5) * np.square(tx_b + ty_b)
                    p90 = ty_b * ty_b
                    p135 = np.float32(0.5) * np.square(ty_b - tx_b)
                    p_sum = p0 + p45 + p90 + p135 + np.float32(1e-5)
                    flow_b = (
                        p0 * s0_b[:, :bw] + p45 * s45_b[:, :bw] + p90 * s90_b[:, :bw] + p135 * s135_b[:, :bw]
                    ) / p_sum

                    aniso_b = np.clip(grad_norm[y0:y1, x0:x1] * np.float32(4.2), np.float32(0.0), np.float32(1.0))
                    prim_b = aniso_b * flow_b + (np.float32(1.0) - aniso_b) * s45_b[:, :bw]

                    sv_b = sketch_val[y0:y1, x0:x1]
                    st_b = stump_weight[y0:y1, x0:x1]
                    dark_b = np.float32(1.0) - sv_b
                    w_prim = (
                        cv2.pow(dark_b, 0.78)
                        * (np.float32(1.0) - np.float32(0.22) * dark_b)
                        * (np.float32(1.0) - c_skin_damp * st_b)
                    )
                    w_cross = cv2.pow(dark_b, 1.70) * (np.float32(1.0) - np.float32(0.32) * st_b)
                    w_tooth = cv2.pow(dark_b, 0.55) * (np.float32(1.0) - np.float32(0.25) * dark_b)

                    sv_b += (
                        w_prim * prim_b * c_h_prim
                        + w_cross * s135_b[:, :bw] * c_h_cross
                        + w_tooth * sp_b[:, :bw] * c_h_tooth
                    )
                    np.clip(sv_b, np.float32(0.0), np.float32(1.0), out=sv_b)

        del gx, gy, grad_mag, grad_norm, stump_weight

        # 6. Kneaded-Eraser Specular Highlights (Crisp eye catchlights & specular glints)
        eye_val = float(cfg.get("eye_enhance", 0.75))
        if eye_val > 0.05:
            luma_raw -= np.float32(226.0)
            luma_raw *= np.float32(1.0 / 28.0)
            np.clip(luma_raw, np.float32(0.0), np.float32(1.0), out=luma_raw)
            luma_raw *= np.float32(0.14 + eye_val * 0.08)
            sketch_val += luma_raw
            np.clip(sketch_val, np.float32(0.0), np.float32(1.0), out=sketch_val)
        del luma_raw

        # 7. Authentic Staedtler Lumograph Graphite Reflectance & Fine-Art Bristol/Cotton Paper Tone
        warmth_val = float(cfg.get("warmth", 1.01 if is_pro_mode else 1.04))
        warm_shift = warmth_val - 1.0
        paper_r = float(np.clip(250.0 + warm_shift * 60.0, 236.0, 255.0))
        paper_g = float(np.clip(249.0 + warm_shift * 28.0, 236.0, 254.0))
        paper_b = float(np.clip(246.0 - warm_shift * 90.0, 212.0, 255.0))
        lead_r, lead_g, lead_b = (14.0, 15.0, 17.0) if is_pro_mode else (18.0, 19.0, 22.0)

        out_r = np.clip(lead_r + sketch_val * np.float32(paper_r - lead_r), 0, 255).astype(np.uint8)
        out_g = np.clip(lead_g + sketch_val * np.float32(paper_g - lead_g), 0, 255).astype(np.uint8)
        out_b = np.clip(lead_b + sketch_val * np.float32(paper_b - lead_b), 0, 255).astype(np.uint8)
        del sketch_val
        return cv2.merge((out_r, out_g, out_b))

    def _apply_traumatized_nightmare(
        self,
        rgb: np.ndarray,
        skin_mask_2d: np.ndarray,
        faces: Optional[List[Dict[str, Any]]],
        cfg: Dict[str, Any],
    ) -> np.ndarray:
        """
        Recreates the iconic viral Traumatized Mr. Incredible meme aesthetic:
        - Dramatic high-contrast black-and-white chiaroscuro grading.
        - Deep sunken orbital sockets, prominent dark eye bags & heavy brow shading.
        - Shocked, unblinking thousand-yard stare with high-contrast sclera & crushed pupils.
        - Gaunt sunken cheekbones & deep nasolabial grimace folds.
        - Multi-scale Black Top-Hat wrinkle extraction & anatomical forehead stress furrows.
        - Desaturated, pale and ghostly grey skin tones preserving full recognizable facial identity.
        """
        h, w = rgb.shape[:2]
        res_scale = max(1.0, min(w, h) / 1000.0)

        # 1. High-Contrast Panchromatic Monochrome Base
        luma_mat = np.array([[0.48, 0.42, 0.10]], dtype=np.float32)
        gray = cv2.transform(rgb, luma_mat)
        if gray.ndim == 3:
            gray = gray[:, :, 0]
        gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)

        # 2. Extreme Multi-Scale CLAHE (Local Chiaroscuro Contrast & Micro-Texture Definition)
        clahe_fine = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
        clahe_coarse = cv2.createCLAHE(clipLimit=3.4, tileGridSize=(16, 16))
        gray_cf = clahe_fine.apply(gray_u8)
        gray_cc = clahe_coarse.apply(gray_u8)
        gray_clahe = cv2.addWeighted(gray_cf, 0.70, gray_cc, 0.30, 0)

        # 3. Harsh Nightmare S-Curve: Deep crushing of dark midtones + cold highlight retention
        x_c = np.linspace(0.0, 1.0, 256, dtype=np.float32)
        gamma_s = 1.74
        curve_s = np.power(x_c, gamma_s) / (np.power(x_c, gamma_s) + np.power(1.0 - x_c, gamma_s) + 1e-6)
        lut_s = np.clip(curve_s * 255.0, 0, 255).astype(np.uint8)
        base_luma = cv2.LUT(gray_clahe, lut_s).astype(np.float32)

        # 4. Multi-Scale Morphological Black Top-Hat: Extract every micro-crease, pore, blemish & fold
        k_fine_sz = max(3, int(round(3 * res_scale)) | 1)
        k_small_sz = max(5, int(round(7 * res_scale)) | 1)
        k_med_sz = max(9, int(round(15 * res_scale)) | 1)
        k_horiz_w = max(15, int(round(29 * res_scale)) | 1)
        k_horiz_h = max(2, int(round(2 * res_scale)))

        k_fine = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_fine_sz, k_fine_sz))
        k_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_small_sz, k_small_sz))
        k_med = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_med_sz, k_med_sz))
        k_horiz = cv2.getStructuringElement(cv2.MORPH_RECT, (k_horiz_w, k_horiz_h))

        bth_f = cv2.morphologyEx(gray_clahe, cv2.MORPH_BLACKHAT, k_fine).astype(np.float32)
        bth_s = cv2.morphologyEx(gray_clahe, cv2.MORPH_BLACKHAT, k_small).astype(np.float32)
        bth_m = cv2.morphologyEx(gray_clahe, cv2.MORPH_BLACKHAT, k_med).astype(np.float32)
        bth_h = cv2.morphologyEx(gray_clahe, cv2.MORPH_BLACKHAT, k_horiz).astype(np.float32)

        natural_wrinkles = bth_f * 0.95 + bth_s * 1.45 + bth_m * 1.55 + bth_h * 1.35

        # High-pass micro-texture enhancement (prevents doll skin, exposes raw skin grit)
        blur_fine = cv2.GaussianBlur(gray_clahe, (0, 0), sigmaX=max(0.8, 1.1 * res_scale)).astype(np.float32)
        micro_edges = np.clip(blur_fine - gray_clahe.astype(np.float32), 0.0, 45.0)
        natural_wrinkles += micro_edges * 1.35

        # Face zone mask
        face_zone = np.clip(skin_mask_2d * 1.40, 0.0, 1.0)

        # 5. Anatomical Meme Horror Features (Sunken Sockets, Stress Creases, Gaunt Contours)
        eye_shadow_mask = np.zeros((h, w), dtype=np.float32)
        eye_aperture_mask = np.zeros((h, w), dtype=np.float32)
        cheek_shadow_mask = np.zeros((h, w), dtype=np.float32)
        synthetic_stress_lines = np.zeros((h, w), dtype=np.float32)

        if faces and len(faces) > 0:
            for f in faces:
                fb = f["box"]
                pad_x = int(fb[2] * 0.25)
                pad_y = int(fb[3] * 0.25)
                x1, y1 = max(0, fb[0] - pad_x), max(0, fb[1] - pad_y)
                x2, y2 = min(w, fb[0] + fb[2] + pad_x), min(h, fb[1] + fb[3] + pad_y)
                face_box_mask = np.zeros((h, w), dtype=np.float32)
                cv2.rectangle(face_box_mask, (x1, y1), (x2, y2), 1.0, -1)
                face_box_mask = cv2.GaussianBlur(face_box_mask, (0, 0), sigmaX=max(4.0, fb[2] * 0.08))
                face_zone = np.maximum(face_zone, face_box_mask)

                re = f["right_eye"]
                le = f["left_eye"]
                nose = f["nose"]
                rm = f["right_mouth"]
                lm = f["left_mouth"]
                eye_dist = float(np.linalg.norm(re - le))
                if eye_dist < 6.0:
                    continue

                for eye_pt in (re, le):
                    ex, ey = int(round(eye_pt[0])), int(round(eye_pt[1]))
                    # A. Deep sunken socket (large dark orbital ellipse)
                    rx_sock = max(8, int(eye_dist * 0.38))
                    ry_sock = max(6, int(eye_dist * 0.34))
                    cv2.ellipse(eye_shadow_mask, (ex, ey), (rx_sock, ry_sock), 0, 0, 360, 0.78, -1)

                    # B. Pronounced lower eye bags / dark circles (under-eye crescent)
                    ey_bag = ey + int(eye_dist * 0.22)
                    rx_bag = max(7, int(eye_dist * 0.36))
                    ry_bag = max(5, int(eye_dist * 0.24))
                    cv2.ellipse(eye_shadow_mask, (ex, ey_bag), (rx_bag, ry_bag), 0, 0, 360, 0.95, -1)

                    # C. Heavy brow overhang shadow (upper orbital rim)
                    ey_brow = ey - int(eye_dist * 0.18)
                    rx_brow = max(8, int(eye_dist * 0.40))
                    ry_brow = max(5, int(eye_dist * 0.20))
                    cv2.ellipse(eye_shadow_mask, (ex, ey_brow), (rx_brow, ry_brow), 0, 0, 360, 0.75, -1)

                    # D. Under-eye bag crease line (sharp dark furrow under socket)
                    bag_line_y = ey + int(eye_dist * 0.30)
                    bag_p1 = (ex - int(eye_dist * 0.24), bag_line_y - int(eye_dist * 0.03))
                    bag_p2 = (ex + int(eye_dist * 0.24), bag_line_y + int(eye_dist * 0.03))
                    cv2.line(synthetic_stress_lines, bag_p1, bag_p2, 1.0, max(2, int(eye_dist * 0.045)))

                    # E. Eye aperture (for terrified thousand-yard stare contrast)
                    rx_inner = max(4, int(eye_dist * 0.14))
                    ry_inner = max(3, int(eye_dist * 0.11))
                    inner_mask = np.zeros((h, w), dtype=np.float32)
                    cv2.ellipse(inner_mask, (ex, ey), (rx_inner, ry_inner), 0, 0, 360, 1.0, -1)
                    eye_aperture_mask = np.maximum(eye_aperture_mask, inner_mask)

                # F. Glabella vertical frowning furrows (between the eyebrows)
                mid_x = int(round((re[0] + le[0]) * 0.5))
                mid_y = int(round((re[1] + le[1]) * 0.5 - eye_dist * 0.10))
                rx_g = max(4, int(eye_dist * 0.18))
                ry_g = max(5, int(eye_dist * 0.30))
                cv2.ellipse(eye_shadow_mask, (mid_x, mid_y), (rx_g, ry_g), 0, 0, 360, 0.82, -1)
                frown_spacing = max(2, int(eye_dist * 0.08))
                frown_len = int(eye_dist * 0.24)
                cv2.line(synthetic_stress_lines, (mid_x - frown_spacing, mid_y - frown_len), (mid_x - frown_spacing, mid_y + frown_len), 1.0, max(2, int(eye_dist * 0.04)))
                cv2.line(synthetic_stress_lines, (mid_x + frown_spacing, mid_y - frown_len), (mid_x + frown_spacing, mid_y + frown_len), 1.0, max(2, int(eye_dist * 0.04)))

                # G. Horizontal Forehead Stress Furrows (Iconic Mr. Incredible Creases)
                forehead_w = int(eye_dist * 0.85)
                forehead_start_y = int(min(re[1], le[1]) - eye_dist * 0.35)
                for idx in range(3):
                    line_y = forehead_start_y - int(idx * eye_dist * 0.18)
                    if line_y > 5:
                        pts = []
                        for xi in range(-forehead_w, forehead_w + 1, max(4, int(forehead_w / 8))):
                            wave = int(np.sin(xi * 0.08) * eye_dist * 0.04)
                            pts.append([mid_x + xi, line_y + wave])
                        pts_np = np.array(pts, dtype=np.int32)
                        cv2.polylines(synthetic_stress_lines, [pts_np], False, 0.85, max(2, int(eye_dist * 0.04)))

                # H. Gaunt Sunken Cheekbones
                rc_x = int(round(re[0] + eye_dist * 0.32))
                rc_y = int(round(nose[1] + eye_dist * 0.20))
                cv2.ellipse(cheek_shadow_mask, (rc_x, rc_y), (int(eye_dist * 0.30), int(eye_dist * 0.44)), 18, 0, 360, 0.72, -1)

                lc_x = int(round(le[0] - eye_dist * 0.32))
                lc_y = int(round(nose[1] + eye_dist * 0.20))
                cv2.ellipse(cheek_shadow_mask, (lc_x, lc_y), (int(eye_dist * 0.30), int(eye_dist * 0.44)), -18, 0, 360, 0.72, -1)

                # I. Deep Nasolabial Grimace Folds
                pt_rn = (int(round(nose[0] + eye_dist * 0.20)), int(round(nose[1])))
                pt_rm = (int(round(rm[0])), int(round(rm[1])))
                pt_ln = (int(round(nose[0] - eye_dist * 0.20)), int(round(nose[1])))
                pt_lm = (int(round(lm[0])), int(round(lm[1])))
                cv2.line(cheek_shadow_mask, pt_rn, pt_rm, 0.90, max(2, int(eye_dist * 0.10)))
                cv2.line(cheek_shadow_mask, pt_ln, pt_lm, 0.90, max(2, int(eye_dist * 0.10)))
                cv2.line(synthetic_stress_lines, pt_rn, pt_rm, 1.0, max(2, int(eye_dist * 0.05)))
                cv2.line(synthetic_stress_lines, pt_ln, pt_lm, 1.0, max(2, int(eye_dist * 0.05)))

                # J. Under-Chin & Jawline Horror Shadow
                chin_y = int(round(max(rm[1], lm[1]) + eye_dist * 0.34))
                chin_x = int(round((rm[0] + lm[0]) * 0.5))
                cv2.ellipse(cheek_shadow_mask, (chin_x, chin_y), (int(eye_dist * 0.60), int(eye_dist * 0.25)), 0, 0, 360, 0.80, -1)

        else:
            # Fallback if no landmarks detected: use skin mask vertical geometry
            skin_pts = np.argwhere(skin_mask_2d > 0.3)
            if len(skin_pts) > 100:
                ymin, xmin = skin_pts.min(axis=0)
                ymax, xmax = skin_pts.max(axis=0)
                box_h = ymax - ymin
                box_w = xmax - xmin
                eye_y = int(ymin + box_h * 0.35)
                left_x = int(xmin + box_w * 0.32)
                right_x = int(xmin + box_w * 0.68)
                e_dist = float(box_w * 0.36)
                rx = max(7, int(e_dist * 0.36))
                ry = max(5, int(e_dist * 0.30))
                cv2.ellipse(eye_shadow_mask, (left_x, eye_y), (rx, ry), 0, 0, 360, 0.82, -1)
                cv2.ellipse(eye_shadow_mask, (right_x, eye_y), (rx, ry), 0, 0, 360, 0.82, -1)
                cv2.ellipse(eye_shadow_mask, (left_x, int(eye_y + e_dist * 0.22)), (rx, int(ry * 0.7)), 0, 0, 360, 0.90, -1)
                cv2.ellipse(eye_shadow_mask, (right_x, int(eye_y + e_dist * 0.22)), (rx, int(ry * 0.7)), 0, 0, 360, 0.90, -1)
                cv2.ellipse(cheek_shadow_mask, (int(xmin + box_w * 0.22), int(ymin + box_h * 0.60)), (int(e_dist * 0.30), int(e_dist * 0.42)), 0, 0, 360, 0.70, -1)
                cv2.ellipse(cheek_shadow_mask, (int(xmin + box_w * 0.78), int(ymin + box_h * 0.60)), (int(e_dist * 0.30), int(e_dist * 0.42)), 0, 0, 360, 0.70, -1)

        # Blur masks smoothly
        sigma_blur = max(3.0, 16.0 * res_scale)
        eye_shadow_smooth = cv2.GaussianBlur(eye_shadow_mask, (0, 0), sigmaX=sigma_blur)
        cheek_shadow_smooth = cv2.GaussianBlur(cheek_shadow_mask, (0, 0), sigmaX=sigma_blur * 1.2)
        stress_lines_smooth = cv2.GaussianBlur(synthetic_stress_lines, (0, 0), sigmaX=max(1.2, 2.4 * res_scale))
        eye_aperture_smooth = cv2.GaussianBlur(eye_aperture_mask, (0, 0), sigmaX=max(1.5, 3.0 * res_scale))

        # Apply both natural and anatomical wrinkles into luminance
        all_wrinkles = (natural_wrinkles * 1.85 + stress_lines_smooth * 58.0) * face_zone
        luma_wrinkled = np.clip(base_luma - all_wrinkles, 0.0, 255.0)

        # Apply deep eye shadows and dark facial shading (hollow sockets & sunken cheeks)
        shadow_mult = np.clip(1.0 - (eye_shadow_smooth * 0.72) - (cheek_shadow_smooth * 0.60), 0.06, 1.0)
        luma_shadowed = luma_wrinkled * shadow_mult

        # Eye expression contrast: inside the eye aperture, push sclera bright and pupils dark
        if np.count_nonzero(eye_aperture_smooth > 0.05) > 0:
            gray_eyes = gray_clahe.astype(np.float32)
            sclera_mask = (gray_eyes > 115).astype(np.float32) * eye_aperture_smooth
            pupil_mask = (gray_eyes <= 115).astype(np.float32) * eye_aperture_smooth
            luma_shadowed = luma_shadowed + (sclera_mask * 55.0) - (pupil_mask * 48.0)
            luma_shadowed = np.clip(luma_shadowed, 0.0, 255.0)

        # 6. Desaturated, Pale and Slightly Grey Skin Tones with Horror Mood
        luma_final = np.clip(luma_shadowed, 0.0, 255.0)

        # Cold ghostly steel tone
        out_r = np.clip(luma_final * 0.94, 0, 255).astype(np.uint8)
        out_g = np.clip(luma_final * 0.97, 0, 255).astype(np.uint8)
        out_b = np.clip(luma_final * 1.02 + 2.0, 0, 255).astype(np.uint8)
        return cv2.merge((out_r, out_g, out_b))

    def _enhance_pil_pipeline(self, im: Image.Image, cfg: Dict) -> Image.Image:
        im = ImageOps.autocontrast(im, cutoff=0.3)
        im = ImageEnhance.Color(im).enhance(cfg["vibrance"])
        im = ImageEnhance.Contrast(im).enhance(cfg["depth_shadows"])
        im = ImageEnhance.Sharpness(im).enhance(cfg["detail_sharpen"])
        return im

    # =========================================================================
    # BATCH 4K ZIP ARCHIVE EXPORT
    # =========================================================================
    def create_batch_zip_file(
        self,
        image_ids: List[str],
        preset: str = "ultra_hot_4k",
        out_format: str = "jpg",
    ) -> Path:
        fmt_ext = out_format.lower().lstrip(".")
        if fmt_ext not in ("jpg", "png", "webp"):
            fmt_ext = "jpg"

        zip_hash = hashlib.md5(f"{','.join(sorted(image_ids))}_{preset}_{fmt_ext}".encode("utf-8")).hexdigest()[:12]
        zip_path = VIDEO_PREVIEW_CACHE_DIR / f"batch_{zip_hash}.zip"

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for img_id in image_ids:
                meta = self.get_image_by_id(img_id)
                if not meta:
                    continue
                out_path, _ = self.enhance_image(img_id, preset=preset, out_format=fmt_ext)
                if out_path and out_path.exists():
                    stem = Path(meta["filename"]).stem
                    arcname = f"EliteBabes_4K_{stem}_{preset}.{fmt_ext}"
                    zf.write(out_path, arcname=arcname)
        return zip_path

    def create_batch_zip(
        self,
        image_ids: List[str],
        preset: str = "ultra_hot_4k",
        out_format: str = "jpg",
    ) -> bytes:
        zip_path = self.create_batch_zip_file(image_ids, preset=preset, out_format=out_format)
        try:
            return zip_path.read_bytes()
        finally:
            zip_path.unlink(missing_ok=True)

    def batch_enhance(
        self,
        image_ids: List[str],
        preset: str = "ultra_hot_4k",
        custom_params: Optional[Dict[str, Any]] = None,
        out_format: str = "jpg",
    ) -> Dict[str, Any]:
        """Multi-threaded memory-bounded batch 4K enhancement."""
        import concurrent.futures
        results = []
        errors = 0

        def _worker(iid: str):
            try:
                p, rep = self.enhance_image(iid, preset=preset, custom_params=custom_params, out_format=out_format)
                return {"id": iid, "status": "ok" if p else "failed", "report": rep}
            except Exception as exc:
                return {"id": iid, "status": "error", "error": str(exc)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            futs = [ex.submit(_worker, iid) for iid in image_ids]
            for f in concurrent.futures.as_completed(futs):
                res = f.result()
                if res.get("status") == "ok":
                    results.append(res["id"])
                else:
                    errors += 1

        return {
            "total_requested": len(image_ids),
            "enhanced_count": len(results),
            "errors": errors,
            "preset": preset,
            "preset_name": PRESET_CONFIGS.get(preset, {}).get("name", preset),
        }

    # =========================================================================
    # LOCAL VIDEO DISCOVERY, AI BEST-FRAME SCANNER & ANIMATED LOOP EXTRACTOR
    # =========================================================================
    def list_videos(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._video_list_cache is not None and (now - self._video_list_cache[0]) < 30.0:
            return self._video_list_cache[1]

        videos: List[Dict[str, Any]] = []
        candidates: List[Path] = []
        if UPLOADED_VIDEOS_DIR.exists():
            for up_p in sorted(UPLOADED_VIDEOS_DIR.iterdir(), key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True):
                if up_p.is_file() and up_p.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                    candidates.append(up_p)

        if VIDEOS_ROOT_DIR.exists():
            for p in sorted(VIDEOS_ROOT_DIR.rglob("*")):
                try:
                    rel_parts = p.relative_to(VIDEOS_ROOT_DIR).parts
                    if len(rel_parts) <= 2 and p.is_file() and p.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                        candidates.append(p)
                except Exception:
                    continue

        for vpath in candidates[:60]:
            vid_id = hashlib.md5(str(vpath).encode("utf-8")).hexdigest()[:12]
            stat = vpath.stat()
            if stat.st_size < 1024:
                continue
            duration_sec = 0.0
            width, height, fps = 0, 0, 0.0
            if HAS_CV2:
                cap = cv2.VideoCapture(str(vpath))
                if cap.isOpened():
                    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
                    frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                    if fps > 0 and frames > 0:
                        duration_sec = round(frames / fps, 1)
                cap.release()

            if width <= 0 or height <= 0 or duration_sec <= 0.1:
                continue

            short_dim = min(width, height)
            if short_dim >= 2000:
                res_label = "4K 2160p"
            elif short_dim >= 1400:
                res_label = "2K 1440p"
            elif short_dim >= 1000:
                res_label = "1080p FHD"
            elif short_dim >= 700:
                res_label = "720p HD"
            else:
                res_label = f"{short_dim}p"

            videos.append(
                {
                    "id": vid_id,
                    "name": vpath.name,
                    "folder": vpath.parent.name,
                    "path": str(vpath),
                    "size_mb": round(stat.st_size / (1024 * 1024), 1),
                    "duration_sec": duration_sec,
                    "width": width,
                    "height": height,
                    "fps": round(fps, 2),
                    "res_label": res_label,
                }
            )
        self._video_list_cache = (now, videos)
        return videos

    def _get_video_by_id(self, vid_id: str) -> Optional[Dict[str, Any]]:
        for v in self.list_videos():
            if v["id"] == vid_id:
                return v
        return None

    def preview_video_frame(self, vid_id: str, timestamp_sec: float) -> Optional[Path]:
        if not HAS_CV2:
            return None
        vinfo = self._get_video_by_id(vid_id)
        if not vinfo:
            return None

        ts = max(0.0, float(timestamp_sec))
        preview_path = VIDEO_PREVIEW_CACHE_DIR / f"{vid_id}_{ts:.2f}.jpg"
        if preview_path.exists():
            return preview_path

        cap = cv2.VideoCapture(vinfo["path"])
        if not cap.isOpened():
            return None
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                return None
            fh, fw = frame.shape[:2]
            if max(fh, fw) > 1280:
                scale_p = 1280.0 / max(fh, fw)
                frame = cv2.resize(
                    frame,
                    (max(1, int(round(fw * scale_p))), max(1, int(round(fh * scale_p)))),
                    interpolation=cv2.INTER_AREA,
                )
            cv2.imwrite(str(preview_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
            return preview_path
        finally:
            cap.release()

    def scan_video_best_frames(self, vid_id: str, sample_count: int = 18, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        AI Best-Frame Scanner: sample frames across the video and score them by
        Laplacian sharpness + YCrCb skin presence + balanced exposure.
        """
        if not HAS_CV2:
            return []
        vinfo = self._get_video_by_id(vid_id)
        if not vinfo:
            return []

        dur = max(10.0, float(vinfo.get("duration_sec") or 60.0))
        timestamps = np.linspace(dur * 0.06, dur * 0.94, sample_count)
        scored: List[Dict[str, Any]] = []

        cap = cv2.VideoCapture(vinfo["path"])
        if not cap.isOpened():
            return []
        try:
            for ts in timestamps:
                ts_f = round(float(ts), 1)
                cap.set(cv2.CAP_PROP_POS_MSEC, ts_f * 1000.0)
                ok, bgr = cap.read()
                if not ok or bgr is None:
                    continue

                # Cache preview thumbnail for instant UI display
                preview_path = VIDEO_PREVIEW_CACHE_DIR / f"{vid_id}_{ts_f:.2f}.jpg"
                if not preview_path.exists():
                    cv2.imwrite(str(preview_path), bgr, [cv2.IMWRITE_JPEG_QUALITY, 86])

                small = cv2.resize(bgr, (320, 180), interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                sharp = float(cv2.Laplacian(gray, cv2.CV_16S).var())

                rgb_s = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                _, skin_pct = self._detect_skin_mask(rgb_s)
                mean_luma = float(np.mean(gray))
                exposure_bonus = 1.0 if 45.0 <= mean_luma <= 215.0 else 0.3

                ai_score = round((sharp * 0.65 + skin_pct * 2.2) * exposure_bonus, 1)
                hh = int(ts_f // 3600)
                mm = int((ts_f % 3600) // 60)
                ss = int(ts_f % 60)
                scored.append(
                    {
                        "timestamp": ts_f,
                        "time_str": f"{hh:02d}:{mm:02d}:{ss:02d}",
                        "sharpness": round(sharp, 1),
                        "skin_pct": skin_pct,
                        "ai_score": ai_score,
                        "preview_url": f"/api/video/frame/{vid_id}?t={ts_f:.2f}",
                    }
                )
        finally:
            cap.release()

        scored.sort(key=lambda x: x["ai_score"], reverse=True)
        return scored[:top_k]

    def extract_video_frame_to_gallery(
        self, vid_id: str, timestamp_sec: float, preset: str = "ultra_hot_4k"
    ) -> Optional[Dict[str, Any]]:
        if not HAS_CV2:
            return None
        vinfo = self._get_video_by_id(vid_id)
        if not vinfo:
            return None

        ts = max(0.0, float(timestamp_sec))
        cap = cv2.VideoCapture(vinfo["path"])
        if not cap.isOpened():
            return None
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                return None

            hh = int(ts // 3600)
            mm = int((ts % 3600) // 60)
            ss = int(ts % 60)
            ts_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
            stem = Path(vinfo["name"]).stem
            out_name = f"{stem} {ts_str}.jpg"
            out_file = self.source_dir / out_name
            if out_file.exists():
                out_name = f"{stem} {ts_str}_{int((ts % 1) * 100):02d}.jpg"
                out_file = self.source_dir / out_name

            cv2.imwrite(str(out_file), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        finally:
            cap.release()

        self._meta_cache.clear()
        img_id = self._file_id(out_name)
        self.get_thumbnail(img_id)
        self.enhance_image(img_id, preset=preset)
        return self.get_image_by_id(img_id)

    def extract_video_loop_to_gallery(
        self,
        vid_id: str,
        timestamp_sec: float,
        duration_sec: float = 2.4,
        preset: str = "ultra_hot_4k",
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a smooth 2.4s animated WebP loop from the video at timestamp_sec,
        applying the AI optical enhancement pipeline frame-by-frame.
        """
        if not HAS_CV2:
            return None
        vinfo = self._get_video_by_id(vid_id)
        if not vinfo:
            return None

        cfg = dict(PRESET_CONFIGS.get(preset, PRESET_CONFIGS["ultra_hot_4k"]))
        ts = max(0.0, float(timestamp_sec))
        cap = cv2.VideoCapture(vinfo["path"])
        if not cap.isOpened():
            return None

        pil_frames: List[Image.Image] = []
        try:
            fps_out = 10
            total_frames = int(round(duration_sec * fps_out))
            for i in range(total_frames):
                cur_t = ts + (i / fps_out)
                cap.set(cv2.CAP_PROP_POS_MSEC, cur_t * 1000.0)
                ok, bgr = cap.read()
                if not ok or bgr is None:
                    break
                h, w = bgr.shape[:2]
                scale = min(1.0, 960.0 / max(w, h, 1))
                small_bgr = cv2.resize(
                    bgr, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA
                )
                rgb = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)
                enh_rgb, _ = self._enhance_cv2_pipeline(rgb, cfg)
                pil_frames.append(Image.fromarray(enh_rgb))
        finally:
            cap.release()

        if not pil_frames:
            return None

        hh = int(ts // 3600)
        mm = int((ts % 3600) // 60)
        ss = int(ts % 60)
        ts_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
        stem = Path(vinfo["name"]).stem
        out_name = f"{stem}_LOOP_{ts_str}.webp"
        out_file = self.source_dir / out_name

        pil_frames[0].save(
            out_file,
            "WEBP",
            save_all=True,
            append_images=pil_frames[1:],
            duration=100,
            loop=0,
            quality=88,
        )
        for pf in pil_frames:
            pf.close()

        self._meta_cache.clear()
        img_id = self._file_id(out_name)
        return self.get_image_by_id(img_id)

    def scan_video_scenes(self, vid_id: str, threshold: float = 0.35) -> List[Dict[str, Any]]:
        if not HAS_CV2:
            return []
        vinfo = self._get_video_by_id(vid_id)
        if not vinfo:
            return []

        cap = cv2.VideoCapture(vinfo["path"])
        if not cap.isOpened():
            return []

        dur = max(1.0, float(vinfo.get("duration_sec") or 60.0))
        sample_count = min(36, max(12, int(dur // 4)))
        timestamps = np.linspace(0.5, dur - 0.5, sample_count)

        scenes: List[Dict[str, Any]] = []
        prev_hist = None

        try:
            for ts in timestamps:
                ts_f = round(float(ts), 2)
                cap.set(cv2.CAP_PROP_POS_MSEC, ts_f * 1000.0)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
                hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [12, 8], [0, 180, 0, 256])
                cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                if prev_hist is None:
                    prev_hist = hist
                    scenes.append({"timestamp": ts_f, "diff": 1.0})
                    continue

                diff = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
                if diff >= threshold:
                    scenes.append({"timestamp": ts_f, "diff": round(diff, 3)})
                    prev_hist = hist

                if len(scenes) >= 20:
                    break
        finally:
            cap.release()

        for sc in scenes:
            ts = sc["timestamp"]
            hh = int(ts // 3600)
            mm = int((ts % 3600) // 60)
            ss = int(ts % 60)
            sc["time_str"] = f"{hh:02d}:{mm:02d}:{ss:02d}"
            sc["preview_url"] = f"/api/video/frame/{vid_id}?t={ts:.2f}"

        return scenes

    def create_comparison_loop(self, img_id: str, preset: str = "ultra_hot_4k") -> Optional[Path]:
        meta = self.get_image_by_id(img_id)
        if not meta:
            return None

        src_path = self.source_dir / meta["filename"]
        if not src_path.exists():
            return None

        out_path, _ = self.enhance_image(img_id, preset=preset, out_format="jpg")
        if not out_path or not out_path.exists():
            return None

        loop_path = VIDEO_PREVIEW_CACHE_DIR / f"compare_{img_id}_{preset}.webp"
        if loop_path.exists():
            return loop_path

        try:
            with Image.open(src_path) as im_orig_raw, Image.open(out_path) as im_enh_raw:
                im_orig = im_orig_raw.convert("RGB")
                im_enh = im_enh_raw.convert("RGB")

            max_side = 1440
            scale = min(1.0, max_side / max(im_orig.width, im_orig.height, 1))
            w = int(round(im_orig.width * scale))
            h = int(round(im_orig.height * scale))

            f1 = im_orig.resize((w, h), Image.Resampling.LANCZOS)
            f2 = im_enh.resize((w, h), Image.Resampling.LANCZOS)
            im_orig.close()
            im_enh.close()

            f1.save(
                loop_path,
                "WEBP",
                save_all=True,
                append_images=[f2],
                duration=1200,
                loop=0,
                quality=90,
            )
            f1.close()
            f2.close()
            return loop_path
        except Exception:
            return None

    # =========================================================================
    # 10s–60s VIDEO CLIP PRESET CONVERTER (STREAMING FFMPEG + TEMPORAL EMA)
    # =========================================================================
    def ingest_uploaded_video(
        self, tmp_path: Path, original_filename: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Validate and store a user-uploaded video clip for 10s–60s preset conversion."""
        if not tmp_path.exists() or tmp_path.stat().st_size <= 0:
            tmp_path.unlink(missing_ok=True)
            return False, None, "Uploaded video file is empty"

        raw_clean = Path(original_filename or f"clip_{int(time.time())}.mp4").name
        stem = re.sub(r"[^\w\-. ]+", "_", Path(raw_clean).stem).strip(" ._") or f"clip_{int(time.time())}"
        ext = Path(raw_clean).suffix.lower()
        if ext not in SUPPORTED_VIDEO_EXTENSIONS:
            ext = ".mp4"

        dest_path = UPLOADED_VIDEOS_DIR / f"{stem}{ext}"
        counter = 1
        while dest_path.exists():
            dest_path = UPLOADED_VIDEOS_DIR / f"{stem}_{counter}{ext}"
            counter += 1

        shutil.move(str(tmp_path), str(dest_path))

        if HAS_CV2:
            cap = cv2.VideoCapture(str(dest_path))
            ok = cap.isOpened()
            frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0) if ok else 0.0
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) if ok else 0
            cap.release()
            if not ok or w <= 0 or frames <= 0:
                dest_path.unlink(missing_ok=True)
                return False, None, "Invalid or unreadable video clip"

        self._video_list_cache = None
        vid_id = hashlib.md5(str(dest_path).encode("utf-8")).hexdigest()[:12]
        vinfo = self._get_video_by_id(vid_id)
        return True, vinfo, ""

    def start_video_clip_preset_job(
        self,
        vid_id: str,
        start_sec: float = 0.0,
        duration_sec: float = 15.0,
        preset: str = "ultra_hot_4k",
        resolution_p: int = 0,
        fps_out: int = 0,
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Launch a low-RAM streaming video clip preset conversion job (10s to 60s)
        supporting 4K (2160p), 1080p, 720p, and Auto/Original resolution with temporal EMA
        anti-flicker stabilization and original audio muxing.
        """
        if not HAS_CV2:
            return False, {}, "OpenCV is required for video clip conversion"
        vinfo = self._get_video_by_id(vid_id)
        if not vinfo:
            return False, {}, "Video ID not found"

        preset_key = preset if preset in PRESET_CONFIGS else "ultra_hot_4k"
        preset_name = PRESET_CONFIGS[preset_key].get("name", preset_key)
        start_t = max(0.0, float(start_sec))
        max_avail = max(1.0, float(vinfo.get("duration_sec") or 3600.0) - start_t)
        if duration_sec <= 0:
            # -1 or 0 means Full Length (Entire Video)
            dur_t = max_avail
        else:
            dur_t = float(np.clip(duration_sec, 3.0, max_avail))

        src_w = int(vinfo.get("width") or 1920)
        src_h = int(vinfo.get("height") or 1080)
        src_short = min(src_w, src_h) if (src_w > 0 and src_h > 0) else 1080
        if int(resolution_p) <= 0:
            res_p = int(np.clip(src_short, 480, 2160))
        else:
            res_p = int(np.clip(resolution_p, 480, 2160))

        src_fps = float(vinfo.get("fps") or 24.0)
        if src_fps <= 1.0 or src_fps > 120.0:
            src_fps = 24.0
        if int(fps_out) <= 0:
            target_fps = int(np.clip(round(src_fps), 15, 60))
        else:
            target_fps = int(np.clip(fps_out, 15, 60))

        job_sig = f"{vid_id}_{start_t:.1f}_{dur_t:.1f}_{preset_key}_{res_p}p_{target_fps}fps"
        job_id = hashlib.md5(job_sig.encode("utf-8")).hexdigest()[:12]
        out_mp4 = VIDEO_CLIPS_CACHE_DIR / f"clip_{job_id}_{preset_key}.mp4"

        with self._video_clip_lock:
            existing = self._video_clip_jobs.get(job_id)
            if existing and existing.get("status") == "running":
                return True, dict(existing), ""
            if out_mp4.exists() and out_mp4.stat().st_size > 4096:
                done_job = {
                    "job_id": job_id,
                    "video_id": vid_id,
                    "video_name": vinfo["name"],
                    "preset": preset_key,
                    "preset_name": preset_name,
                    "start_sec": round(start_t, 1),
                    "duration_sec": round(dur_t, 1),
                    "resolution_p": res_p,
                    "fps": target_fps,
                    "status": "completed",
                    "progress_pct": 100,
                    "done_frames": int(round(dur_t * target_fps)),
                    "total_frames": int(round(dur_t * target_fps)),
                    "fps_speed": 0.0,
                    "eta_sec": 0.0,
                    "size_mb": round(out_mp4.stat().st_size / (1024 * 1024), 2),
                    "video_url": f"/api/video/clip-file/{job_id}",
                    "download_url": f"/api/video/clip-file/{job_id}?download=1",
                    "out_path": str(out_mp4),
                }
                self._video_clip_jobs[job_id] = done_job
                return True, dict(done_job), ""

            total_frames = max(1, int(round(dur_t * target_fps)))
            job_state = {
                "job_id": job_id,
                "video_id": vid_id,
                "video_name": vinfo["name"],
                "preset": preset_key,
                "preset_name": preset_name,
                "start_sec": round(start_t, 1),
                "duration_sec": round(dur_t, 1),
                "resolution_p": res_p,
                "fps": target_fps,
                "status": "running",
                "progress_pct": 1,
                "done_frames": 0,
                "total_frames": total_frames,
                "fps_speed": 0.0,
                "eta_sec": round(total_frames / 12.0, 1),
                "size_mb": 0.0,
                "video_url": f"/api/video/clip-file/{job_id}",
                "download_url": f"/api/video/clip-file/{job_id}?download=1",
                "out_path": str(out_mp4),
            }
            self._video_clip_jobs[job_id] = job_state

        worker_thread = threading.Thread(
            target=self._run_video_clip_preset_worker,
            args=(job_id, vinfo["path"], start_t, dur_t, preset_key, res_p, target_fps, out_mp4),
            daemon=True,
        )
        worker_thread.start()
        return True, dict(job_state), ""

    def cancel_video_job(self, job_id: str) -> bool:
        """Cancel an ongoing video conversion job and free resources."""
        with self._video_clip_lock:
            if job_id in self._video_clip_jobs:
                self._video_clip_jobs[job_id]["cancel_requested"] = True
                return True
        return False

    def _run_video_clip_preset_worker(
        self,
        job_id: str,
        video_path: str,
        start_sec: float,
        duration_sec: float,
        preset_key: str,
        resolution_p: int,
        target_fps: int,
        out_mp4: Path,
    ):
        with self._video_clip_sem:
            t_start = time.perf_counter()
            tmp_mp4 = out_mp4.with_name(f"{out_mp4.stem}_tmp_{os.getpid()}.mp4")
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                with self._video_clip_lock:
                    if job_id in self._video_clip_jobs:
                        self._video_clip_jobs[job_id]["status"] = "error"
                        self._video_clip_jobs[job_id]["error"] = "Failed to open source video"
                return

            dec_proc = None
            ff_proc = None
            vw = None
            try:
                src_fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
                if src_fps <= 1.0 or src_fps > 240.0:
                    src_fps = 30.0
                src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
                src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)

                # Compute even dimensions for H.264 yuv420p encoding across 720p, 1080p, and 4K (2160p)
                short_side = max(1, min(src_w, src_h))
                scale = float(resolution_p) / float(short_side)
                # Do not upscale beyond 2160p; preserve exact aspect ratio (16:9, 9:16, 4:3)
                out_w = max(16, int(round(src_w * scale)) & ~1)
                out_h = max(16, int(round(src_h * scale)) & ~1)

                # Working resolution for the heavy bilateral/skin-mask pass (guided delta transfer preserves 100% 4K/1080p sharpness)
                is_sketch = bool(
                    PRESET_CONFIGS.get(preset_key, {}).get("pencil_sketch", False)
                    or PRESET_CONFIGS.get(preset_key, {}).get("pro_pencil_sketch", False)
                )
                proxy_limit = 960 if is_sketch else 720
                out_short = min(out_w, out_h)
                if out_short > proxy_limit:
                    p_scale = float(proxy_limit) / float(out_short)
                    work_w = max(16, int(round(out_w * p_scale)) & ~1)
                    work_h = max(16, int(round(out_h * p_scale)) & ~1)
                    use_guided_delta = not is_sketch and not bool(
                        PRESET_CONFIGS.get(preset_key, {}).get("is_monochrome", False)
                    )
                else:
                    work_w, work_h = out_w, out_h
                    use_guided_delta = False

                cfg = dict(PRESET_CONFIGS.get(preset_key, PRESET_CONFIGS["ultra_hot_4k"]))
                # Lock per-frame dynamic auto-WB to prevent temporal brightness/color flicker
                cfg["auto_exposure_wb"] = False

                total_frames = max(1, int(round(duration_sec * target_fps)))
                ffmpeg_bin = shutil.which("ffmpeg")

                if ffmpeg_bin:
                    cap.release()
                    # Fast keyframe-seeking input decoder pipe via ffmpeg (-ss before -i jumps instantly in 4K/1080p files)
                    dec_cmd = [
                        ffmpeg_bin,
                        "-loglevel",
                        "error",
                        "-ss",
                        f"{start_sec:.2f}",
                        "-t",
                        f"{duration_sec:.2f}",
                        "-i",
                        video_path,
                        "-vf",
                        f"fps={target_fps},scale={out_w}:{out_h}:flags=bicubic",
                        "-f",
                        "rawvideo",
                        "-pix_fmt",
                        "rgb24",
                        "-",
                    ]
                    dec_proc = subprocess.Popen(
                        dec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=out_w * out_h * 3 * 2
                    )

                    crf_val = "20" if out_short >= 2000 else "19"
                    enc_preset = "ultrafast" if out_short >= 2000 else "veryfast"
                    cmd = [
                        ffmpeg_bin,
                        "-y",
                        "-loglevel",
                        "error",
                        "-f",
                        "rawvideo",
                        "-vcodec",
                        "rawvideo",
                        "-pix_fmt",
                        "rgb24",
                        "-s",
                        f"{out_w}x{out_h}",
                        "-r",
                        str(target_fps),
                        "-i",
                        "-",
                        "-ss",
                        f"{start_sec:.2f}",
                        "-t",
                        f"{duration_sec:.2f}",
                        "-i",
                        video_path,
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0?",
                        "-c:v",
                        "libx264",
                        "-preset",
                        enc_preset,
                        "-crf",
                        crf_val,
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "160k",
                        "-shortest",
                        "-movflags",
                        "+faststart",
                        str(tmp_mp4),
                    ]
                    ff_proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000.0)
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    vw = cv2.VideoWriter(str(tmp_mp4), fourcc, float(target_fps), (out_w, out_h))

                frame_bytes_len = out_w * out_h * 3
                step_ratio = src_fps / float(target_fps)
                src_idx = 0
                out_idx = 0
                prev_raw_gray: Optional[np.ndarray] = None
                prev_enh_work: Optional[np.ndarray] = None
                wb_luts: Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]] = None
                want_initial_wb = bool(PRESET_CONFIGS.get(preset_key, {}).get("auto_exposure_wb", False))

                while out_idx < total_frames:
                    if self._video_clip_jobs.get(job_id, {}).get("cancel_requested"):
                        if dec_proc is not None:
                            try:
                                dec_proc.terminate()
                                dec_proc.wait(timeout=2)
                            except Exception:
                                pass
                        if ff_proc is not None:
                            try:
                                ff_proc.terminate()
                                ff_proc.wait(timeout=2)
                            except Exception:
                                pass
                        if tmp_mp4.exists():
                            try:
                                tmp_mp4.unlink(missing_ok=True)
                            except Exception:
                                pass
                        with self._video_clip_lock:
                            if job_id in self._video_clip_jobs:
                                self._video_clip_jobs[job_id]["status"] = "cancelled"
                                self._video_clip_jobs[job_id]["progress_pct"] = 0
                                self._video_clip_jobs[job_id]["error"] = "Cancelled by user"
                        return

                    if out_idx % 200 == 0:
                        import gc
                        gc.collect()

                    if dec_proc is not None and dec_proc.stdout is not None:
                        raw_buf = dec_proc.stdout.read(frame_bytes_len)
                        if not raw_buf or len(raw_buf) < frame_bytes_len:
                            break
                        rgb_full = np.frombuffer(raw_buf, dtype=np.uint8).reshape((out_h, out_w, 3)).copy()
                    else:
                        ok, bgr = cap.read()
                        if not ok or bgr is None:
                            break
                        target_src_idx = int(round(out_idx * step_ratio))
                        if src_idx < target_src_idx:
                            src_idx += 1
                            continue
                        src_idx += 1
                        if bgr.shape[1] != out_w or bgr.shape[0] != out_h:
                            bgr = cv2.resize(bgr, (out_w, out_h), interpolation=cv2.INTER_AREA)
                        rgb_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

                    if (work_w, work_h) != (out_w, out_h):
                        rgb_work = cv2.resize(rgb_full, (work_w, work_h), interpolation=cv2.INTER_AREA)
                    else:
                        rgb_work = rgb_full
                    cur_gray = cv2.cvtColor(rgb_work, cv2.COLOR_RGB2GRAY)

                    # Compute locked Auto-WB LUT once on frame 0 so exposure never flickers across frames
                    if want_initial_wb and wb_luts is None:
                        mean_l = float(np.mean(cur_gray))
                        exp_g = (
                            float(np.clip(128.0 / max(mean_l, 1.0), 0.85, 1.25))
                            if (mean_l < 95.0 or mean_l > 165.0)
                            else 1.0
                        )
                        m_r = max(1.0, float(np.mean(rgb_work[:, :, 0])))
                        m_g = max(1.0, float(np.mean(rgb_work[:, :, 1])))
                        m_b = max(1.0, float(np.mean(rgb_work[:, :, 2])))
                        avg_c = (m_r + m_g + m_b) / 3.0
                        r_g = float(np.clip(avg_c / m_r, 0.90, 1.12)) * 0.45 + 0.55
                        g_g = float(np.clip(avg_c / m_g, 0.92, 1.08)) * 0.45 + 0.55
                        b_g = float(np.clip(avg_c / m_b, 0.88, 1.12)) * 0.45 + 0.55
                        idx_a = np.arange(256, dtype=np.float32)
                        wb_luts = (
                            np.clip(idx_a * (exp_g * r_g), 0, 255).astype(np.uint8),
                            np.clip(idx_a * (exp_g * g_g), 0, 255).astype(np.uint8),
                            np.clip(idx_a * (exp_g * b_g), 0, 255).astype(np.uint8),
                        )

                    raw_work_before = rgb_work
                    if wb_luts is not None:
                        rc, gc, bc = cv2.split(rgb_work)
                        rgb_work = cv2.merge((cv2.LUT(rc, wb_luts[0]), cv2.LUT(gc, wb_luts[1]), cv2.LUT(bc, wb_luts[2])))

                    enh_work, _ = self._enhance_cv2_pipeline(rgb_work, cfg)

                    # Motion-aware Temporal EMA Stabilization (eliminates frame-to-frame flicker & sketch boiling)
                    if prev_enh_work is not None and prev_raw_gray is not None:
                        motion_diff = cv2.absdiff(cur_gray, prev_raw_gray)
                        static_mask = (motion_diff < 14).astype(np.uint8)
                        blend_alpha = 0.84 if cfg.get("pencil_sketch") else 0.90
                        blended = cv2.addWeighted(enh_work, blend_alpha, prev_enh_work, 1.0 - blend_alpha, 0)
                        enh_work = np.where(static_mask[:, :, None] > 0, blended, enh_work)

                    prev_raw_gray = cur_gray
                    prev_enh_work = enh_work

                    if (work_w, work_h) == (out_w, out_h):
                        enh_rgb = enh_work
                    elif use_guided_delta:
                        # Preserve 100% of native 1080p/4K detail by transferring signed uint8 color/tone delta
                        pos_d = cv2.resize(
                            cv2.subtract(enh_work, raw_work_before), (out_w, out_h), interpolation=cv2.INTER_LINEAR
                        )
                        neg_d = cv2.resize(
                            cv2.subtract(raw_work_before, enh_work), (out_w, out_h), interpolation=cv2.INTER_LINEAR
                        )
                        enh_rgb = cv2.subtract(cv2.add(rgb_full, pos_d), neg_d)
                        del pos_d, neg_d
                    else:
                        # For monochrome or sketch presets on 1080p/4K, combine upscaled tone with native high-frequency detail
                        up_enh = cv2.resize(enh_work, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
                        if not is_sketch:
                            up_base = cv2.resize(raw_work_before, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
                            hf_pos = cv2.subtract(rgb_full, up_base)
                            hf_neg = cv2.subtract(up_base, rgb_full)
                            enh_rgb = cv2.subtract(cv2.add(up_enh, hf_pos), hf_neg)
                            del up_base, hf_pos, hf_neg
                        else:
                            enh_rgb = up_enh

                    if ff_proc is not None and ff_proc.stdin is not None:
                        ff_proc.stdin.write(enh_rgb.tobytes())
                    elif vw is not None:
                        vw.write(cv2.cvtColor(enh_rgb, cv2.COLOR_RGB2BGR))

                    out_idx += 1
                    elapsed = max(0.001, time.perf_counter() - t_start)
                    fps_cur = round(out_idx / elapsed, 1)
                    rem_frames = max(0, total_frames - out_idx)
                    eta_s = round(rem_frames / max(fps_cur, 0.5), 1)
                    pct = min(99, max(1, int(round((out_idx / total_frames) * 100))))

                    with self._video_clip_lock:
                        if job_id in self._video_clip_jobs:
                            jb = self._video_clip_jobs[job_id]
                            jb["done_frames"] = out_idx
                            jb["progress_pct"] = pct
                            jb["fps_speed"] = fps_cur
                            jb["eta_sec"] = eta_s

                if dec_proc is not None:
                    if dec_proc.stdout:
                        dec_proc.stdout.close()
                    dec_proc.terminate()
                if ff_proc is not None:
                    if ff_proc.stdin:
                        ff_proc.stdin.close()
                    ff_proc.wait(timeout=300)
                if vw is not None:
                    vw.release()

                if tmp_mp4.exists() and tmp_mp4.stat().st_size > 1024:
                    tmp_mp4.replace(out_mp4)
                    sz_mb = round(out_mp4.stat().st_size / (1024 * 1024), 2)
                    with self._video_clip_lock:
                        if job_id in self._video_clip_jobs:
                            jb = self._video_clip_jobs[job_id]
                            jb["status"] = "completed"
                            jb["progress_pct"] = 100
                            jb["done_frames"] = out_idx
                            jb["eta_sec"] = 0.0
                            jb["size_mb"] = sz_mb
                else:
                    with self._video_clip_lock:
                        if job_id in self._video_clip_jobs:
                            self._video_clip_jobs[job_id]["status"] = "error"
                            self._video_clip_jobs[job_id]["error"] = "Video encoding produced empty output"
            except Exception as exc:
                with self._video_clip_lock:
                    if job_id in self._video_clip_jobs:
                        self._video_clip_jobs[job_id]["status"] = "error"
                        self._video_clip_jobs[job_id]["error"] = str(exc)
            finally:
                cap.release()
                if dec_proc is not None:
                    try:
                        dec_proc.kill()
                    except Exception:
                        pass
                tmp_mp4.unlink(missing_ok=True)

    def get_video_clip_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._video_clip_lock:
            jb = self._video_clip_jobs.get(job_id)
            return dict(jb) if jb else None

    def get_video_clip_file(self, job_id: str) -> Optional[Path]:
        with self._video_clip_lock:
            jb = self._video_clip_jobs.get(job_id)
            if jb and jb.get("out_path"):
                p = Path(jb["out_path"])
                if p.exists():
                    return p
        for p in VIDEO_CLIPS_CACHE_DIR.glob(f"clip_{job_id}_*.mp4"):
            if p.exists():
                return p
        return None


if __name__ == "__main__":
    engine = AIImageEnhancerEngine()
    found = engine.scan_folder()
    print(f"[AI Enhancer Engine] Scanned {len(found)} images in {engine.source_dir}")
