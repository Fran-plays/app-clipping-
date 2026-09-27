const API_BASE = "http://localhost:8000";

let currentStyleId = null;

const refInput = document.getElementById("refInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const profileBox = document.getElementById("profileBox");

const targetInput = document.getElementById("targetInput");
const generateBtn = document.getElementById("generateBtn");
const durationInput = document.getElementById("durationInput");
const statusBox = document.getElementById("status");

const resultCard = document.getElementById("resultCard");
const resultVideo = document.getElementById("resultVideo");
const downloadLink = document.getElementById("downloadLink");

analyzeBtn.addEventListener("click", async () => {
  if (!refInput.files.length) {
    alert("Pilih video referensi dulu.");
    return;
  }
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Menganalisis...";

  const form = new FormData();
  form.append("reference", refInput.files[0]);

  try {
    const res = await fetch(`${API_BASE}/api/style/extract`, { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail || "Gagal analisis");
    const data = await res.json();
    currentStyleId = data.style_id;
    renderProfile(data.profile);
    generateBtn.disabled = false;
  } catch (err) {
    alert(err.message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analisis Gaya";
  }
});

generateBtn.addEventListener("click", async () => {
  if (!targetInput.files.length) {
    alert("Pilih video yang mau diklip dulu.");
    return;
  }
  if (!currentStyleId) {
    alert("Analisis video referensi dulu.");
    return;
  }

  generateBtn.disabled = true;
  statusBox.textContent = "Memproses video, mohon tunggu...";
  resultCard.classList.add("hidden");

  const form = new FormData();
  form.append("target", targetInput.files[0]);
  form.append("style_id", currentStyleId);
  form.append("target_duration", durationInput.value || 30);

  try {
    const res = await fetch(`${API_BASE}/api/clip/generate`, { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail || "Gagal membuat klip");
    const data = await res.json();
    const fullUrl = `${API_BASE}${data.download_url}`;
    resultVideo.src = fullUrl;
    downloadLink.href = fullUrl;
    resultCard.classList.remove("hidden");
    statusBox.textContent = "Selesai!";
  } catch (err) {
    statusBox.textContent = "";
    alert(err.message);
  } finally {
    generateBtn.disabled = false;
  }
});

function renderProfile(p) {
  profileBox.classList.remove("hidden");
  profileBox.innerHTML = `
    <div class="row"><span>Irama potongan</span><b>${p.cut_pace}</b></div>
    <div class="row"><span>Rata-rata durasi shot</span><b>${p.avg_shot_duration}s</b></div>
    <div class="row"><span>Jumlah shot terdeteksi</span><b>${p.shot_count}</b></div>
    <div class="row"><span>Orientasi</span><b>${p.orientation}</b></div>
    <div class="row"><span>Kecerahan rata-rata</span><b>${p.avg_brightness}</b></div>
    <div class="row"><span>Saturasi rata-rata</span><b>${p.avg_saturation}</b></div>
  `;
}
