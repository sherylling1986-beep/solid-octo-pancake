#!/usr/bin/env python3
"""Google Colab friendly 30-second exhibition video generator.

The script scans a Google Drive material folder, analyzes whatever media exists,
and builds a stable 1920x1080/30fps MP4 without assuming fixed filenames.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from moviepy.audio.fx.all import audio_loop
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

VIDEO_SIZE = (1920, 1080)
FPS = 30
DURATION = 30.0
ROOT_FOLDER_NAME = "30秒快剪-JFEX展会速览"
SEGMENTS = [
    ("开场", 0.0, 3.0, ["entrance", "crowd", "scene", "booth", "product"]),
    ("展位展示", 3.0, 10.0, ["booth", "scene", "entrance", "crowd", "product"]),
    ("产品展示", 10.0, 20.0, ["product", "booth", "scene", "crowd", "entrance"]),
    ("商务交流", 20.0, 27.0, ["business", "crowd", "scene", "booth", "product"]),
    ("品牌结束页", 27.0, 30.0, ["logo", "booth", "product", "scene", "entrance"]),
]
CAPTIONS = {
    "开场": "JFEX Exhibition Highlights",
    "展位展示": "Booth Showcase",
    "产品展示": "Featured Products",
    "商务交流": "Business Networking",
    "品牌结束页": "Thank You",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
REQUIRED_DIRS = ["video", "photo", "logo", "music", "output"]
KEYWORDS = {
    "entrance": ["入口", "门口", "展馆", "会场", "entrance", "gate", "hall"],
    "booth": ["展位", "展台", "摊位", "booth", "stand", "pavilion"],
    "product": ["产品", "商品", "样品", "食品", "product", "sample", "food"],
    "business": ["交流", "洽谈", "客户", "签约", "活动", "business", "meeting", "client", "talk"],
    "crowd": ["人流", "观众", "现场", "crowd", "people", "visitor"],
    "scene": ["现场", "环境", "展会", "scene", "expo", "event", "jfex"],
    "logo": ["logo", "标志", "品牌", "brand"],
}


@dataclass
class Asset:
    path: Path
    media_type: str
    duration: float = 0.0
    width: int = 0
    height: int = 0
    quality: float = 0.0
    purpose: str = "备用素材"
    tags: List[str] = field(default_factory=list)
    keyframe: Optional[Path] = None


def ensure_directories(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)


def iter_files(folder: Path, extensions: Iterable[str]) -> List[Path]:
    allowed = {e.lower() for e in extensions}
    if not folder.exists():
        return []
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in allowed)


def print_materials(root: Path) -> None:
    labels = [("视频", "video", VIDEO_EXTENSIONS), ("照片", "photo", IMAGE_EXTENSIONS), ("logo", "logo", IMAGE_EXTENSIONS), ("音乐", "music", AUDIO_EXTENSIONS)]
    print("当前发现的素材：")
    for label, dirname, exts in labels:
        files = iter_files(root / dirname, exts)
        print(f"\n{label}：")
        if files:
            for file in files:
                print(file.relative_to(root))
        else:
            print("（未发现，将自动跳过或使用其他素材替代）")


def tags_for(path: Path, media_type: str) -> List[str]:
    text = f"{path.stem} {path.parent.name}".lower()
    found = [tag for tag, words in KEYWORDS.items() if any(word.lower() in text for word in words)]
    if media_type == "logo" and "logo" not in found:
        found.append("logo")
    if not found and media_type in {"video", "photo"}:
        found.append("scene")
    return found


def sharpness_score(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def analyze_image(path: Path, media_type: str) -> Asset:
    with Image.open(path) as img:
        width, height = img.size
        arr = cv2.cvtColor(np.array(ImageOps.exif_transpose(img).convert("RGB")), cv2.COLOR_RGB2BGR)
    sharp = sharpness_score(arr)
    megapixels = (width * height) / 1_000_000
    aspect_bonus = 15 if 1.45 <= width / max(height, 1) <= 2.05 else 0
    quality = min(100.0, megapixels * 14 + min(sharp / 20, 45) + aspect_bonus)
    asset = Asset(path=path, media_type=media_type, width=width, height=height, quality=round(quality, 2))
    asset.tags = tags_for(path, media_type)
    asset.purpose = "/".join(asset.tags) if asset.tags else "备用素材"
    return asset


def analyze_video(path: Path, keyframe_dir: Path) -> Asset:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return Asset(path=path, media_type="video", quality=0.0, tags=tags_for(path, "video"), purpose="无法读取")
    fps = cap.get(cv2.CAP_PROP_FPS) or FPS
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = float(frames / fps) if fps else 0.0
    sample_positions = [0.15, 0.35, 0.55, 0.75]
    best_frame = None
    best_score = -1.0
    for pos in sample_positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(max(frames - 1, 0) * pos))
        ok, frame = cap.read()
        if ok:
            score = sharpness_score(frame)
            if score > best_score:
                best_score = score
                best_frame = frame
    cap.release()
    keyframe = None
    if best_frame is not None:
        keyframe_dir.mkdir(parents=True, exist_ok=True)
        keyframe = keyframe_dir / f"{path.stem}_keyframe.jpg"
        cv2.imwrite(str(keyframe), best_frame)
    megapixels = (width * height) / 1_000_000
    duration_bonus = min(duration, 12) * 1.5
    quality = min(100.0, megapixels * 12 + min(max(best_score, 0) / 22, 45) + duration_bonus)
    asset = Asset(path=path, media_type="video", duration=round(duration, 2), width=width, height=height, quality=round(quality, 2), keyframe=keyframe)
    asset.tags = tags_for(path, "video")
    asset.purpose = "/".join(asset.tags) if asset.tags else "备用素材"
    return asset


def analyze_materials(root: Path) -> List[Asset]:
    keyframe_dir = root / "output" / "keyframes"
    assets: List[Asset] = []
    for path in iter_files(root / "video", VIDEO_EXTENSIONS):
        assets.append(analyze_video(path, keyframe_dir))
    for path in iter_files(root / "photo", IMAGE_EXTENSIONS):
        assets.append(analyze_image(path, "photo"))
    for path in iter_files(root / "logo", IMAGE_EXTENSIONS):
        assets.append(analyze_image(path, "logo"))
    return sorted(assets, key=lambda a: a.quality, reverse=True)


def write_csv(root: Path, assets: Sequence[Asset]) -> Path:
    csv_path = root / "output" / "material_analysis.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["文件名", "类型", "时长", "分辨率", "质量评分", "用途", "关键帧"])
        for a in assets:
            writer.writerow([str(a.path.relative_to(root)), a.media_type, a.duration or "", f"{a.width}x{a.height}" if a.width else "", a.quality, a.purpose, str(a.keyframe.relative_to(root)) if a.keyframe else ""])
    return csv_path


def cover_image(path: Path) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    tw, th = VIDEO_SIZE
    scale = max(tw / image.width, th / image.height)
    resized = image.resize((math.ceil(image.width * scale), math.ceil(image.height * scale)), Image.LANCZOS)
    left = (resized.width - tw) // 2
    top = (resized.height - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def image_clip(path: Path, duration: float) -> ImageClip:
    clip = ImageClip(np.asarray(cover_image(path))).set_duration(duration)
    return clip.resize(lambda t: 1 + 0.06 * (t / max(duration, 0.1))).set_position("center")


def video_clip(path: Path, duration: float) -> VideoFileClip:
    clip = VideoFileClip(str(path))
    source_audio = clip.audio
    if clip.duration < duration:
        repeats = int(math.ceil(duration / max(clip.duration, 0.1)))
        clip = concatenate_videoclips([clip] * repeats, method="compose")
    clip = clip.subclip(0, duration)
    resized = clip.resize(height=VIDEO_SIZE[1]) if clip.w / clip.h >= VIDEO_SIZE[0] / VIDEO_SIZE[1] else clip.resize(width=VIDEO_SIZE[0])
    cropped = resized.crop(x_center=resized.w / 2, y_center=resized.h / 2, width=VIDEO_SIZE[0], height=VIDEO_SIZE[1])
    return cropped.set_audio(source_audio.subclip(0, min(duration, source_audio.duration)) if source_audio else None)


def load_font(size: int):
    for candidate in ["/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def text_overlay(text: str) -> np.ndarray:
    canvas = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = load_font(62)
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (VIDEO_SIZE[0] - w) // 2, VIDEO_SIZE[1] - 170
    box = Image.new("RGBA", VIDEO_SIZE, (0, 0, 0, 0))
    bd = ImageDraw.Draw(box)
    bd.rounded_rectangle((x - 42, y - 22, x + w + 42, y + h + 22), radius=22, fill=(0, 0, 0, 145))
    canvas.alpha_composite(box.filter(ImageFilter.GaussianBlur(0.4)))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 180))
    return np.asarray(canvas)


def make_caption(text: str, start: float, duration: float) -> ImageClip:
    return ImageClip(text_overlay(text)).set_start(start).set_duration(duration).fadein(0.25).fadeout(0.25)


def make_logo_end(asset: Optional[Asset], fallback: Optional[Asset], duration: float) -> CompositeVideoClip:
    bg = ColorClip(VIDEO_SIZE, color=(12, 18, 32)).set_duration(duration)
    layers = [bg]
    if asset:
        logo = ImageClip(str(asset.path)).set_duration(duration).resize(width=720).set_position("center").fadein(0.4)
        layers.append(logo)
    elif fallback:
        layers.append(image_clip(fallback.path, duration).fadein(0.3))
    return CompositeVideoClip(layers, size=VIDEO_SIZE).set_duration(duration)


def choose_asset(assets: Sequence[Asset], preferred_tags: Sequence[str], used: set[Path], allow_logo: bool = False) -> Optional[Asset]:
    candidates = [a for a in assets if (allow_logo or a.media_type != "logo")]
    for tag in preferred_tags:
        tagged = [a for a in candidates if tag in a.tags and a.path not in used]
        if tagged:
            return max(tagged, key=lambda a: a.quality)
    unused = [a for a in candidates if a.path not in used]
    return max(unused or candidates, key=lambda a: a.quality, default=None)


def segment_clip(asset: Optional[Asset], name: str, duration: float, fallback: Optional[Asset]) -> CompositeVideoClip:
    if name == "品牌结束页":
        return make_logo_end(asset if asset and asset.media_type == "logo" else None, fallback, duration)
    if asset is None:
        return ColorClip(VIDEO_SIZE, color=(20, 25, 35)).set_duration(duration)
    if asset.media_type == "video":
        clip = video_clip(asset.path, duration)
    else:
        clip = image_clip(asset.path, duration)
    return CompositeVideoClip([clip], size=VIDEO_SIZE).set_duration(duration).fadein(0.2).fadeout(0.2)


def add_audio(final: CompositeVideoClip, root: Path) -> CompositeVideoClip:
    music_files = iter_files(root / "music", AUDIO_EXTENSIONS)
    if music_files:
        audio = AudioFileClip(str(music_files[0]))
        audio = audio.fx(audio_loop, duration=DURATION) if audio.duration < DURATION else audio.subclip(0, DURATION)
        return final.set_audio(audio.volumex(0.22).audio_fadeout(1.2))
    # No music: keep any original video audio already present in the composed timeline.
    return final


def build_video(root: Path, output: Optional[Path] = None) -> Tuple[Path, Path]:
    ensure_directories(root)
    print_materials(root)
    assets = analyze_materials(root)
    csv_path = write_csv(root, assets)
    print(f"\n素材分析表已生成：{csv_path}")
    usable = [a for a in assets if a.media_type in {"video", "photo"} and a.quality > 0]
    fallback = max(usable, key=lambda a: a.quality, default=None)
    if not assets or fallback is None:
        raise RuntimeError("未发现可用的视频或照片素材。请至少在 video/ 或 photo/ 放入一个素材文件。")
    used: set[Path] = set()
    clips = []
    captions = []
    for name, start, end, tags in SEGMENTS:
        duration = end - start
        asset = choose_asset(assets, tags, used, allow_logo=(name == "品牌结束页"))
        if asset:
            used.add(asset.path)
            print(f"{name}: 使用 {asset.path.name}（{asset.purpose}, 评分 {asset.quality}）")
        clips.append(segment_clip(asset, name, duration, fallback))
        captions.append(make_caption(CAPTIONS[name], start, min(duration, 3.2)))
    timeline = concatenate_videoclips(clips, method="compose").set_duration(DURATION)
    final = CompositeVideoClip([timeline, *captions], size=VIDEO_SIZE).set_duration(DURATION)
    final = add_audio(final, root)
    output_path = output or (root / "output" / "final_30s_exhibition_video.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac", preset="medium", threads=max(2, os.cpu_count() or 2), ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"])
    final.close()
    return output_path, csv_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="自动扫描素材并生成 30 秒展会宣传视频。")
    parser.add_argument("--input-dir", type=Path, default=Path("/content/drive/MyDrive") / ROOT_FOLDER_NAME, help="素材根目录。")
    parser.add_argument("--output", type=Path, default=None, help="输出 MP4 路径，默认写入素材目录 output/final_30s_exhibition_video.mp4。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output, csv_path = build_video(args.input_dir, args.output)
    print("\n生成完成：")
    print(f"视频：{output}")
    print(f"分析表：{csv_path}")


if __name__ == "__main__":
    main()
