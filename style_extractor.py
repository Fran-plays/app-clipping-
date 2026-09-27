"""
Menganalisis video referensi untuk mengambil "profil gaya" editan:
- kecepatan potongan (cut pace) dari rata-rata durasi shot
- orientasi & rasio aspek
- kecerahan & saturasi rata-rata (untuk meniru color grading)
"""
import cv2
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector


def extract_style(video_path: str) -> dict:
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=27.0))
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps else 0

    shot_durations = [
        (end.get_seconds() - start.get_seconds()) for start, end in scene_list
    ]
    if not shot_durations:
        shot_durations = [duration if duration else 3.0]

    avg_shot_duration = sum(shot_durations) / len(shot_durations)
    if avg_shot_duration < 1.5:
        cut_pace = "fast"
    elif avg_shot_duration < 4:
        cut_pace = "medium"
    else:
        cut_pace = "slow"

    # Sampling frame untuk kecerahan & saturasi rata-rata
    brightness_vals, saturation_vals = [], []
    sample_count = min(20, total_frames) if total_frames else 0
    step = max(1, total_frames // sample_count) if sample_count else 1
    idx = 0
    while idx < total_frames and len(brightness_vals) < sample_count:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        brightness_vals.append(float(hsv[:, :, 2].mean()))
        saturation_vals.append(float(hsv[:, :, 1].mean()))
        idx += step
    cap.release()

    avg_brightness = sum(brightness_vals) / len(brightness_vals) if brightness_vals else 128.0
    avg_saturation = sum(saturation_vals) / len(saturation_vals) if saturation_vals else 128.0

    aspect_ratio = round(width / height, 3) if height else 16 / 9
    orientation = "vertical" if aspect_ratio < 1 else "horizontal"

    return {
        "source_duration": round(duration, 2),
        "shot_count": len(shot_durations),
        "avg_shot_duration": round(avg_shot_duration, 2),
        "cut_pace": cut_pace,
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "orientation": orientation,
        "avg_brightness": round(avg_brightness, 1),
        "avg_saturation": round(avg_saturation, 1),
        "fps": round(fps, 2),
    }
