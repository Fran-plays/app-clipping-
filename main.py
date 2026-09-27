import os
import json
import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from style_extractor import extract_style
from video_editor import generate_clip

STORAGE = os.path.join(os.path.dirname(__file__), "storage")
STYLES_DIR = os.path.join(STORAGE, "styles")
OUTPUT_DIR = os.path.join(STORAGE, "outputs")
UPLOAD_DIR = os.path.join(STORAGE, "uploads")
for d in (STYLES_DIR, OUTPUT_DIR, UPLOAD_DIR):
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="Auto Klip Video API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_upload(upload: UploadFile, dest_dir: str) -> str:
    ext = os.path.splitext(upload.filename or "")[1] or ".mp4"
    path = os.path.join(dest_dir, f"{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path


@app.post("/api/style/extract")
async def api_extract_style(reference: UploadFile = File(...)):
    """Upload video referensi/contoh gaya editan -> hasilkan style_id + profil gaya."""
    ref_path = _save_upload(reference, UPLOAD_DIR)
    try:
        profile = extract_style(ref_path)
    except Exception as e:
        raise HTTPException(500, f"Gagal menganalisis video referensi: {e}")
    finally:
        if os.path.exists(ref_path):
            os.remove(ref_path)

    style_id = uuid.uuid4().hex
    with open(os.path.join(STYLES_DIR, f"{style_id}.json"), "w") as f:
        json.dump(profile, f)

    return {"style_id": style_id, "profile": profile}


@app.post("/api/clip/generate")
async def api_generate_clip(
    target: UploadFile = File(...),
    style_id: str = Form(...),
    target_duration: int = Form(30),
):
    """Upload video yang akan diklip + style_id -> hasilkan video hasil klip otomatis."""
    style_path = os.path.join(STYLES_DIR, f"{style_id}.json")
    if not os.path.exists(style_path):
        raise HTTPException(404, "Style profile tidak ditemukan. Analisis ulang video referensi.")
    with open(style_path) as f:
        profile = json.load(f)

    target_path = _save_upload(target, UPLOAD_DIR)
    output_name = f"{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    try:
        generate_clip(
            target_path, profile, output_path,
            target_duration=target_duration, work_dir=UPLOAD_DIR,
        )
    except Exception as e:
        raise HTTPException(500, f"Gagal membuat klip: {e}")
    finally:
        if os.path.exists(target_path):
            os.remove(target_path)

    return {"download_url": f"/api/download/{output_name}"}


@app.get("/api/download/{filename}")
async def download(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "File tidak ditemukan")
    return FileResponse(path, filename=filename, media_type="video/mp4")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
