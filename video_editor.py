"""
Membuat klip otomatis dari video target dengan meniru profil gaya
(irama potongan, orientasi, color grading) dari video referensi.

Alur:
1. Deteksi scene/shot alami pada video target (PySceneDetect).
2. Beri skor tiap shot berdasarkan intensitas gerakan (motion score)
   -> shot dengan gerakan/aksi lebih tinggi dianggap "highlight".
3. Pilih & susun shot sampai mendekati target_duration, dengan panjang
   tiap shot mengikuti avg_shot_duration dari gaya referensi.
4. Render tiap segmen (crop rasio aspek + brightness/saturation match)
   lalu digabung jadi satu file output.
"""
import os
import uuid
import subprocess
import cv2
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector


def _detect_scenes(video_path: str):
    video = open_video(video_path)
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=27.0))
    sm.detect_scenes(video)
    scenes = sm.get_scene_list()
    return [(s.get_seconds(), e.get_seconds()) for s, e in scenes]


def _scene_motion_score(video_path: str, start_sec: float, end_sec: float, samples: int = 5) -> float:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    start_frame = int(start_sec * fps)
    end_frame = int(end_sec * fps)
    if end_frame <= start_frame:
        cap.release()
        return 0.0
    step = max(1, (end_frame - start_frame) // samples)
    prev, diffs = None, []
    frame_idx = start_frame
    while frame_idx < end_frame:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY)
        if prev is not None:
            diffs.append(float(cv2.absdiff(gray, prev).mean()))
        prev = gray
        frame_idx += step
    cap.release()
    return sum(diffs) / len(diffs) if diffs else 0.0


def _extract_segment(input_path: str, start: float, duration: float, output_path: str, style_profile: dict):
    orientation = style_profile.get("orientation", "horizontal")
    target_w, target_h = (1080, 1920) if orientation == "vertical" else (1920, 1080)

    brightness_target = style_profile.get("avg_brightness", 128)
    saturation_target = style_profile.get("avg_saturation", 128)
    brightness_adj = (brightness_target - 128) / 255
    saturation_adj = max(0.5, min(2.0, saturation_target / 128))

    vf = (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},"
        f"eq=brightness={brightness_adj:.3f}:saturation={saturation_adj:.3f}"
    )

    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-i", input_path, "-t", str(duration),
        "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-c:a", "aac",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def generate_clip(target_path: str, style_profile: dict, output_path: str,
                   target_duration: int = 30, work_dir: str = "/tmp") -> str:
    scenes = _detect_scenes(target_path)
    if not scenes:
        cap = cv2.VideoCapture(target_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        cap.release()
        scenes = [(0, dur)]

    scored = [
        {"start": s, "end": e, "score": _scene_motion_score(target_path, s, e)}
        for s, e in scenes
    ]
    scored.sort(key=lambda s: s["score"], reverse=True)

    avg_shot = max(0.6, style_profile.get("avg_shot_duration", 2.0))
    picked, total = [], 0.0
    for scene in scored:
        if total >= target_duration:
            break
        available = scene["end"] - scene["start"]
        s_len = min(available, avg_shot)
        picked.append({"start": scene["start"], "end": scene["start"] + s_len})
        total += s_len
    picked.sort(key=lambda p: p["start"])

    if not picked:
        raise RuntimeError("Tidak ada segmen yang bisa dipilih dari video target.")

    tmp_id = uuid.uuid4().hex
    segment_paths = []
    for i, seg in enumerate(picked):
        seg_path = os.path.join(work_dir, f"{tmp_id}_seg{i}.mp4")
        _extract_segment(target_path, seg["start"], seg["end"] - seg["start"], seg_path, style_profile)
        segment_paths.append(seg_path)

    concat_list = os.path.join(work_dir, f"{tmp_id}_list.txt")
    with open(concat_list, "w") as f:
        for p in segment_paths:
            f.write(f"file '{p}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", output_path]
    subprocess.run(cmd, check=True, capture_output=True)

    for p in segment_paths:
        os.remove(p)
    os.remove(concat_list)

    return output_path
