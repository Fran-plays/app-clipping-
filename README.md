# Auto Klip Video — Editing Otomatis Meniru Gaya Referensi

Aplikasi full-stack: upload **video contoh/referensi** untuk dianalisis gayanya,
lalu upload **video yang mau diklip** — sistem otomatis memotong & menyusun
ulang video tersebut agar polanya mirip dengan referensi.

## Cara kerja (penting dibaca)

Ini bukan AI generatif yang "belajar" gaya editor secara mendalam (itu butuh
model machine learning terlatih, dataset besar, dan komputasi berat).
Yang dibangun di sini adalah **pipeline heuristik berbasis analisis video**
yang meniru aspek-aspek gaya yang bisa diukur secara otomatis:

| Aspek gaya yang ditiru | Cara deteksi |
|---|---|
| Irama/kecepatan potongan (cepat/sedang/lambat) | Scene detection (PySceneDetect) → rata-rata durasi shot |
| Orientasi & rasio aspek (vertikal/horizontal) | Dimensi video referensi |
| Warna & mood (brightness/saturation) | Sampling HSV dari frame referensi, diterapkan lewat filter `eq` FFmpeg |
| Pemilihan momen "highlight" di video target | Motion score (perbedaan antar-frame) — shot dengan gerakan tinggi diprioritaskan |

**Belum termasuk** (bisa dikembangkan lebih lanjut): auto-caption dari suara
(perlu speech-to-text, mis. faster-whisper), deteksi musik/beat untuk sinkronisasi
potongan ke irama lagu, transisi custom, atau text overlay otomatis yang meniru
posisi/font teks di video referensi (perlu OCR + deteksi layout).

## Struktur proyek

```
klip-app/
  backend/
    main.py            # FastAPI: endpoint upload, analisis, generate
    style_extractor.py # Ekstraksi profil gaya dari video referensi
    video_editor.py     # Pemotongan & render ulang video target
    requirements.txt
  frontend/
    index.html
    app.js
    style.css
```

## Menjalankan backend

Butuh **FFmpeg** terpasang di sistem (`ffmpeg -version` untuk cek).

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend jalan di `http://localhost:8000`. Cek `GET /api/health`.

## Menjalankan frontend

Cukup buka `frontend/index.html` di browser (atau serve dengan `python -m http.server`
dari folder `frontend`). Pastikan `API_BASE` di `app.js` sesuai alamat backend.

## Alur pemakaian

1. Upload video referensi di bagian 1 → klik **Analisis Gaya** → sistem menampilkan
   profil gaya (irama potongan, orientasi, warna, dll).
2. Upload video yang mau diklip di bagian 2, atur target durasi klip.
3. Klik **Buat Klip Otomatis** → backend memilih & memotong shot paling "aktif"
   dari video target, menyusunnya dengan irama & warna mirip referensi.
4. Preview & download hasil klip.

## Pengembangan lanjutan yang disarankan

- Proses video bisa lama untuk file besar — untuk produksi, pindahkan
  `generate_clip` ke background job (Celery/RQ) + polling status, jangan sinkron.
- Tambahkan auto-caption (faster-whisper) & burn-in subtitle bila referensi
  punya teks.
- Tambahkan deteksi tempo musik (librosa) agar potongan bisa disinkronkan ke beat.
- Validasi ukuran/format file upload & batasi durasi maksimum di production.
