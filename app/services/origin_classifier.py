# app/services/origin_classifier.py

from typing import Dict, Any


def classify_origin(clean_md: Dict[str, Any]) -> str:
    """
    Returns one of:
    "camera", "edited_desktop", "edited_mobile",
    "forwarded", "ai_or_synthetic", "uncertain"
    """
    make = (clean_md.get("make") or "").lower()
    model = (clean_md.get("model") or "").lower()
    software = (clean_md.get("software") or "").lower()
    ai_tool = (clean_md.get("ai_tool") or "").lower()

    has_camera = bool(make or model)

    camera_keywords = [
        "iphone", "ipad", "ipod",
        "samsung", "oneplus", "oppo", "vivo", "xiaomi", "redmi", "mi ",
        "pixel", "google",
        "canon", "nikon", "sony", "fuji", "fujifilm", "leica", "panasonic",
    ]
    is_camera_model = (
        any(k in model for k in camera_keywords)
        or any(k in make for k in camera_keywords)
    )

    desktop_editors = ["photoshop", "gimp", "affinity", "lightroom"]
    is_desktop_editor = any(d in software for d in desktop_editors)

    mobile_editors = [
        "snapseed", "picsart", "canva", "lightroom mobile",
        "pixlr", "capcut", "vsco", "remini"
    ]
    is_mobile_editor = any(m in software for m in mobile_editors)

    forwarding_apps = ["whatsapp", "instagram", "telegram", "facebook", "messenger"]
    is_forwarded_app = any(a in software for a in forwarding_apps)

    # Explicit AI signals
    ai_strings = [
        "midjourney", "dall-e", "stable diffusion", "sdxl",
        "flux", "leonardo", "firefly", "gemini", "chatgpt", "gpt-4o",
        "trainedalgorithmicmedia", "generativeai", "ai generated",
    ]
    has_ai_signal = bool(ai_tool) or any(s in software for s in ai_strings)

    # camera original
    if is_camera_model and not is_desktop_editor and not is_mobile_editor and not is_forwarded_app:
        return "camera"

    # edited desktop
    if is_desktop_editor:
        return "edited_desktop"

    # edited mobile / online
    if is_mobile_editor:
        return "edited_mobile"

    # forwarded/shared
    if is_forwarded_app:
        return "forwarded"

    # explicit AI indicator
    if has_ai_signal and not is_camera_model:
        return "ai_or_synthetic"

    # likely AI / synthetic: no camera, no obvious software
    if not has_camera and not software:
        return "ai_or_synthetic"

    return "uncertain"
