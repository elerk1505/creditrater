// ----- API KEY (localStorage + Remember) -----
const LS_KEY = "creditrater_openai_key";

const apiKeyInput = document.getElementById("apiKeyInput");
const rememberKey = document.getElementById("rememberKey");
const toggleKeyVis = document.getElementById("toggleKeyVis");
const saveKeyBtn = document.getElementById("saveKeyBtn");

// Load remembered key
(function initKey() {
  const saved = localStorage.getItem(LS_KEY);
  if (saved) {
    apiKeyInput.value = saved;
    rememberKey.checked = true;
  }
})();

toggleKeyVis.addEventListener("change", () => {
  apiKeyInput.type = toggleKeyVis.checked ? "text" : "password";
});

saveKeyBtn.addEventListener("click", () => {
  const key = apiKeyInput.value.trim();
  if (!key) { alert("Please paste your OpenAI API key"); return; }
  if (rememberKey.checked) localStorage.setItem(LS_KEY, key);
  else localStorage.removeItem(LS_KEY);
  alert("Key ready for this session.");
});

function getApiKey() {
  return apiKeyInput.value.trim();
}

// ----- Minimal helpers -----
const modeRadios = [...document.querySelectorAll('input[name="mode"]')];
const fileInput = document.getElementById("fileInput");
const cutPages = document.getElementById("cutPages");
const autocutBtn = document.getElementById("autocutBtn");
const resetCutBtn = document.getElementById("resetCutBtn");
const estimateBtn = document.getElementById("estimateBtn");
const estimateOut = document.getElementById("estimateOut");
const industrySelect = document.getElementById("industrySelect");
const manualValues = document.getElementById("manualValues");
const analyzeBtn = document.getElementById("analyzeBtn");
const analyzeStatus = document.getElementById("analyzeStatus");
const resultsTable = document.querySelector("#resultsTable tbody");
const finalScore = document.getElementById("finalScore");

let uploadedId = null;
let factorsForIndustry = [];

// ----- Load industries -----
async function loadIndustries() {
  const res = await fetch("/api/industries");
  const data = await res.json();
  industrySelect.innerHTML = `<option value="">(Auto-detect)</option>` +
    data.map(x => `<option value="${x.id}">${x.name}</option>`).join("");
}
loadIndustries().catch(console.error);

// When an industry is chosen, fetch its factors for manual entry
industrySelect.addEventListener("change", async () => {
  const id = industrySelect.value;
  manualValues.innerHTML = "Loading factors…";
  if (!id) { manualValues.textContent = "Will auto-detect."; factorsForIndustry = []; return; }
  const res = await fetch(`/api/industry-factors?id=${encodeURIComponent(id)}`);
  const data = await res.json();
  factorsForIndustry = data.factors || [];
  if (!factorsForIndustry.length) { manualValues.textContent = "No factors found."; return; }

  manualValues.innerHTML = factorsForIndustry.map(f => {
    const input = f.kind === "quant" ? `<input data-factor="${f.code}" placeholder="${f.name}" style="width: 220px" />`
                                     : `<textarea data-factor="${f.code}" rows="2" style="width: 320px" placeholder="${f.name}"></textarea>`;
    return `<div style="margin:6px 0">${input} <span class="muted">${f.weight ? `(${f.weight}%)` : ""}</span></div>`;
  }).join("");
});

// ----- Upload PDF -----
fileInput.addEventListener("change", async () => {
  if (!fileInput.files?.length) return;
  const key = getApiKey();
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  if (key) fd.append("api_key", key);

  analyzeStatus.textContent = "Uploading…";
  const res = await fetch("/upload", { method: "POST", body: fd });
  if (!res.ok) { analyzeStatus.textContent = "Upload failed."; return; }
  const data = await res.json();
  uploadedId = data.file_id;
  analyzeStatus.textContent = "PDF uploaded.";
});

// ----- Autocut / Reset -----
autocutBtn.addEventListener("click", async () => {
  if (!uploadedId) { alert("Please upload a PDF first."); return; }
  analyzeStatus.textContent = "Finding irrelevant pages…";
  const res = await fetch("/autocut", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: uploadedId })
  });
  const data = await res.json();
  cutPages.value = data.cut_suggestion || "";
  analyzeStatus.textContent = "Autocut suggestion filled.";
});

resetCutBtn.addEventListener("click", () => {
  cutPages.value = "";
});

// ----- Estimate cost -----
estimateBtn.addEventListener("click", async () => {
  if (!uploadedId) { alert("Upload a PDF first."); return; }
  const pages = cutPages.value.trim();
  const mode = modeRadios.find(x => x.checked)?.value ?? "text";
  const key = getApiKey();

  estimateOut.textContent = "Estimating…";
  const res = await fetch("/estimate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_id: uploadedId, pages, mode, api_key: key || null })
  });
  const data = await res.json();
  if (res.ok) {
    estimateOut.innerHTML = `Input tokens ≈ <b>${data.input_tokens}</b>, Output tokens ≈ <b>${data.output_tokens}</b>, Estimated cost ≈ <b>${data.estimated_cost}</b>`;
  } else {
    estimateOut.textContent = data.detail || "Failed to estimate.";
  }
});

// ----- Analyse -----
analyzeBtn.addEventListener("click", async () => {
  if (!uploadedId) { alert("Upload a PDF first."); return; }

  const pages = cutPages.value.trim();
  const mode = modeRadios.find(x => x.checked)?.value ?? "text";
  const industryId = industrySelect.value || null;
  const key = getApiKey();

  // Collect manual values
  const manual = {};
  [...manualValues.querySelectorAll("[data-factor]")].forEach(el => {
    const code = el.getAttribute("data-factor");
    const val = el.value?.trim();
    if (val) manual[code] = val;
  });

  analyzeStatus.textContent = "Analysing… this can take a bit.";
  resultsTable.innerHTML = "";
  finalScore.textContent = "";

  const res = await fetch("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_id: uploadedId, pages, mode, industry_id: industryId,
      manual_values: manual, api_key: key || null
    })
  });

  const data = await res.json();
  if (!res.ok) {
    analyzeStatus.textContent = data.detail || "Analysis failed.";
    return;
  }

  analyzeStatus.textContent = "Done.";
  // Render results
  const rows = data.breakdown || [];
  resultsTable.innerHTML = rows.map(r => `
    <tr>
      <td>${r.factor}</td>
      <td>${r.weight ?? ""}</td>
      <td>${r.description ?? r.value ?? ""}</td>
      <td>${r.score ?? ""}</td>
    </tr>
  `).join("");
  finalScore.textContent = `Final rating: ${data.final_rating ?? "—"} | Composite score: ${data.composite_score ?? "—"}`;
});
