#!/usr/bin/env python3
"""Generate a 30-second exhibition promo video from categorized Google Drive assets.

The script is designed for Google Colab and GitHub Actions. It uses MoviePy for
composition and FFmpeg (bundled through imageio-ffmpeg) for MP4 export.
"""
from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from moviepy.audio.fx.all import audio_loop
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VIDEO_SIZE: Tuple[int, int] = (1920, 1080)
FPS = 30
DURATION = 30

DEFAULT_CAPTIONS = [
    (0.4, 3.0, "Exhibition Highlights"),
    (3.2, 8.0, "Hunan Pavilion"),
    (8.4, 13.5, "Featured Products"),
    (13.8, 20.0, "Connecting with Global Buyers"),
    (20.3, 27.0, "Business Opportunities"),
    (27.2, 30.0, "JYX EXPO"),
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def list_media(folder: Path, extensions: Iterable[str]) -> List[Path]:
    if not folder.exists():
        return []
    allowed = {ext.lower() for ext in extensions}
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in allowed)


def first_media(folder: Path, extensions: Iterable[str], label: str) -> Path:
    files = list_media(folder, extensions)
    if not files:
        raise FileNotFoundError(f"未在 {folder} 找到{label}。请检查素材文件夹和文件格式。")
    return files[0]


def choose_media(folder: Path, extensions: Iterable[str], label: str, rng: random.Random) -> Path:
    files = list_media(folder, extensions)
    if not files:
        raise FileNotFoundError(f"未在 {folder} 找到{label}。请检查素材文件夹和文件格式。")
    return rng.choice(files)


def cover_resize(image: Image.Image, size: Tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize((math.ceil(src_w * scale), math.ceil(src_h * scale)), Image.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def image_segment(path: Path, duration: float, zoom: float = 1.08) -> ImageClip:
    base = cover_resize(Image.open(path), VIDEO_SIZE)
    clip = ImageClip(np.asarray(base)).set_duration(duration)
    # Gentle Ken Burns zoom. The oversized frame is center-cropped by CompositeVideoClip.
    return clip.resize(lambda t: 1 + (zoom - 1) * (t / duration)).set_position("center")


def fit_video_clip(path: Path, duration: float) -> VideoFileClip:
    clip = VideoFileClip(str(path), audio=False)
    if clip.duration < duration:
        repeats = int(math.ceil(duration / max(clip.duration, 0.1)))
        clip = concatenate_videoclips([clip] * repeats)
    clip = clip.subclip(0, duration)
    resized = clip.resize(height=VIDEO_SIZE[1])
    return resized.crop(
        x_center=resized.w / 2,
        y_center=resized.h / 2,
        width=VIDEO_SIZE[0],
        height=VIDEO_SIZE[1],
    )


def transparent_text_image(text: str, size: Tuple[int, int] = VIDEO_SIZE) -> np.ndarray:
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = load_font(74 if len(text) < 18 else 62)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size[0] - text_w) // 2
    y = size[1] - 185

    pad_x, pad_y = 48, 24
    box = Image.new("RGBA", size, (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(box)
    box_draw.rounded_rectangle(
        (x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y),
        radius=28,
        fill=(0, 0, 0, 135),
    )
    box = box.filter(ImageFilter.GaussianBlur(0.2))
    canvas.alpha_composite(box)

    # Stroke improves readability over busy exhibition footage.
    draw = ImageDraw.Draw(canvas)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 190))
    return np.asarray(canvas)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for font_path in candidates:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def caption_clips(captions: Sequence[Tuple[float, float, str]]) -> List[ImageClip]:
    clips: List[ImageClip] = []
    for start, end, text in captions:
        clips.append(ImageClip(transparent_text_image(text)).set_start(start).set_duration(end - start))
    return clips


def logo_end_clip(logo_path: Path, duration: float) -> CompositeVideoClip:
    background = ColorClip(VIDEO_SIZE, color=(12, 18, 32)).set_duration(duration)
    logo = ImageClip(str(logo_path)).set_duration(duration)
    logo = logo.resize(width=min(logo.w, 760)).set_position("center")
    return CompositeVideoClip([background, logo], size=VIDEO_SIZE).set_duration(duration)


def add_music(video: CompositeVideoClip, music_path: Optional[Path]) -> CompositeVideoClip:
    if music_path is None:
        return video
    audio = AudioFileClip(str(music_path))
    if audio.duration < DURATION:
        audio = audio.fx(audio_loop, duration=DURATION)
    else:
        audio = audio.subclip(0, DURATION)
    audio = audio.volumex(0.22).audio_fadeout(1.2)
    return video.set_audio(audio)


def build_video(input_dir: Path, output_path: Path, seed: int = 2026) -> None:
    rng = random.Random(seed)
    entrance = choose_media(input_dir / "展馆入口照片", IMAGE_EXTENSIONS, "展馆入口照片", rng)
    booth = choose_media(input_dir / "展位照片", IMAGE_EXTENSIONS, "展位照片", rng)
    hall_video = first_media(input_dir / "展馆内视频", VIDEO_EXTENSIONS, "展馆内视频",)
    logo = choose_media(input_dir / "展会logo", IMAGE_EXTENSIONS, "展会logo", rng)
    music_files = list_media(input_dir / "music", AUDIO_EXTENSIONS)
    music = music_files[0] if music_files else None

    print("已选择素材：")
    print(f"- 展馆入口照片: {entrance}")
    print(f"- 展位照片: {booth}")
    print(f"- 展馆内视频: {hall_video}")
    print(f"- 展会logo: {logo}")
    print(f"- 背景音乐: {music if music else '未找到，将生成无音乐视频'}")

    timeline = concatenate_videoclips(
        [
            CompositeVideoClip([image_segment(entrance, 3)], size=VIDEO_SIZE).set_duration(3),
            CompositeVideoClip([image_segment(booth, 5)], size=VIDEO_SIZE).set_duration(5),
            fit_video_clip(hall_video, 19),
            logo_end_clip(logo, 3),
        ],
        method="compose",
    ).set_duration(DURATION)

    final = CompositeVideoClip([timeline, *caption_clips(DEFAULT_CAPTIONS)], size=VIDEO_SIZE).set_duration(DURATION)
    final = add_music(final, music)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=2,
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="自动生成 30 秒展会宣传视频。")
    parser.add_argument("--input-dir", type=Path, required=True, help="Google Drive 中的素材根目录。")
    parser.add_argument("--output", type=Path, required=True, help="输出 MP4 文件路径。")
    parser.add_argument("--seed", type=int, default=2026, help="随机选素材种子，固定后可复现。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_video(args.input_dir, args.output, args.seed)


if __name__ == "__main__":
    main()
