import React, { useEffect, useMemo, useRef, useState } from "react";
import FileDrop from "./components/FileDrop.jsx";
import ModeSelector from "./components/ModeSelector.jsx";
import PageControls from "./components/PageControls.jsx";
import IndustrySection from "./components/IndustrySection.jsx";
import ResultsTable from "./components/ResultsTable.jsx";

const API_BASE = "http://127.0.0.1:5051";

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function postForm(url, formData) {
  const r = await fetch(url, { method: "POST", body: formData });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export default function App() {
  const [file, setFile] = useState(null);        // original file Blob
  const [fileId, setFileId] = useState(null);    // backend tmp id
  const [costMode, setCostMode] = useState("text"); // text | text+layout | page_images
  const [preMode, setPreMode] = useState("text");
  const [cutForce, setCutForce] = useState("");    // "1-5, 8, 13"
  const [keepForce, setKeepForce] = useState("");
  const [aggressive, setAggressive] = useState(true);
  const [pagesToRemoveRaw, setPagesToRemoveRaw] = useState(""); // for raw cost estimate
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  // Industry data
  const [industries, setIndustries] = useState([]);
  const [factorScales, setFactorScales] = useState({});
  const [manualIndustry, setManualIndustry] = useState(false);
  const [selectedIndustry, setSelectedIndustry] = useState(null);
  const [manualFactors, setManualFactors] = useState({}); // { factor_key: {value: number|string} }

  // Results
  const [result, setResult] = useState(null); // { table:[...], final_rating, composite_score }

  // Load industries + scales at start
  useEffect(() => {
    getJSON(`${API_BASE}/industries`)
      .then((res) => {
        setIndustries(res.industries || []);
        setFactorScales(res.factor_scales || {});
      })
      .catch((e) => {
        console.error(e);
        setToast(`Failed to load industries: ${String(e).slice(0, 160)}`);
      });
  }, []);

  // Helpers
  const uploadFile = async (blob) => {
    const fd = new FormData();
    fd.append("file", blob);
    const data = await postForm(`${API_BASE}/upload`, fd);
    if (!data.file_id) throw new Error("Upload failed: no file_id");
    setFileId(data.file_id);
    return data.file_id;
  };

  const ensureUploaded = async () => {
    if (fileId) return fileId;
    if (!file) throw new Error("Please upload a PDF first.");
    return uploadFile(file);
  };

  const parsePages = (s) =>
    s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean)
      .join(","); // backend will parse

  // UI actions
  const onEstimateRaw = async () => {
    try {
      setBusy(true);
      const fid = await ensureUploaded();
      const data = await postJSON(`${API_BASE}/estimate_tokens_cost`, {
        file_id: fid,
        mode: costMode,
        pages_to_remove: parsePages(pagesToRemoveRaw),
      });
      setToast(`Estimated LLM cost (raw): $${Number(data.cost_usd).toFixed(4)}`);
    } catch (e) {
      setToast(`Estimator error: ${String(e).slice(0, 200)}`);
    } finally {
      setBusy(false);
    }
  };

  const onPreprocess = async () => {
    try {
      setBusy(true);
      const fid = await ensureUploaded();
      const data = await postJSON(`${API_BASE}/preprocess-pdf`, {
        file_id: fid,
        mode: preMode,
        aggressive,
        force_cut: cutForce,
        force_keep: keepForce,
      });
      if (data.file_id) setFileId(data.file_id); // might return same id or a new derived id
      setToast(
        `Preprocess OK. Removed: ${data.pages_removed || "auto"}. Kept: ${
          data.kept_pages || "(auto)"
        }.`
      );
    } catch (e) {
      setToast(`Preprocess error: ${String(e).slice(0, 200)}`);
    } finally {
      setBusy(false);
    }
  };

  const onEstimateFiltered = async () => {
    try {
      setBusy(true);
      const fid = await ensureUploaded();
      const data = await postJSON(`${API_BASE}/estimate_tokens_cost`, {
        file_id: fid,
        mode: preMode,
        // after preprocess we usually don't need explicit pages_to_remove;
        // passing none so server uses the active filtered doc
      });
      setToast(
        `Estimated LLM cost (filtered): $${Number(data.cost_usd).toFixed(4)}`
      );
    } catch (e) {
      setToast(`Estimator error: ${String(e).slice(0, 200)}`);
    } finally {
      setBusy(false);
    }
  };

  const onReset = async () => {
    if (!file) {
      setToast("Nothing to reset (upload a PDF first).");
      return;
    }
    try {
      setBusy(true);
      // The simplest reliable reset is to re-upload the original file.
      const fid = await uploadFile(file);
      setFileId(fid);
      setCutForce("");
      setKeepForce("");
      setPagesToRemoveRaw("");
      setResult(null);
      setToast("PDF reset to full document.");
    } catch (e) {
      setToast(`Reset failed: ${String(e).slice(0, 200)}`);
    } finally {
      setBusy(false);
    }
  };

  const onAnalyze = async () => {
    try {
      if (!file && !fileId) throw new Error("Upload a PDF first.");
      const fid = await ensureUploaded();

      const body = {
        file_id: fid,
      };

      if (manualIndustry && selectedIndustry) {
        body.industry_key = selectedIndustry.key || selectedIndustry.id || selectedIndustry.name;
      }
      if (manualIndustry && Object.keys(manualFactors).length > 0) {
        body.manual_factors = manualFactors; // { factor_key: value or band }
      }

      setBusy(true);
      const data = await postJSON(`${API_BASE}/score`, body);
      setResult(data);
      setToast(`Analyze complete. Final rating: ${data.final_rating}`);
    } catch (e) {
      setToast(`Analyze error: ${String(e).slice(0, 200)}`);
    } finally {
      setBusy(false);
    }
  };

  const onUpload = async (blob) => {
    setFile(blob);
    setResult(null);
    setPagesToRemoveRaw("");
    setCutForce("");
    setKeepForce("");
    try {
      setBusy(true);
      const fid = await uploadFile(blob);
      setToast("File uploaded.");
      setFileId(fid);
    } catch (e) {
      setToast(`Upload failed: ${String(e).slice(0, 200)}`);
    } finally {
      setBusy(false);
    }
  };

  // UI render
  return (
    <div className="container">
      <div className="card">
        <h1>CreditRater</h1>
        <div className="muted">Upload, cut irrelevant pages, select (optional) industry factors, estimate cost, and analyze.</div>
      </div>

      {/* 1) Upload + cost/analysis */}
      <div className="card">
        <h2>1) Upload or drag a company PDF</h2>
        <FileDrop onFile={onUpload} file={file} busy={busy} />

        <div className="spacer"></div>
        <div className="row">
          <div className="col">
            <label className="muted">Mode (for cost)</label>
            <ModeSelector value={costMode} onChange={setCostMode} />
          </div>
          <div className="col">
            <label className="muted">Pages to remove (comma list)</label>
            <input
              placeholder="e.g. 1-5, 8, 3 (simple commas only here)"
              value={pagesToRemoveRaw}
              onChange={(e) => setPagesToRemoveRaw(e.target.value)}
            />
          </div>
        </div>

        <div className="spacer"></div>
        <div className="row">
          <button className="btn" onClick={onEstimateRaw} disabled={busy}>
            Estimate LLM Cost (raw)
          </button>
          <button className="btn primary" onClick={onAnalyze} disabled={busy}>
            Analyze (LLM)
          </button>
          <button className="btn warn" onClick={onReset} disabled={busy}>
            Reset PDF
          </button>
        </div>
      </div>

      {/* 2) Preprocess */}
      <div className="card">
        <h2>2) Preprocess PDF (cut irrelevant pages) <span className="badge">Removes boilerplate (CSR/ESG etc.), glossary, disclaimers, etc.</span></h2>

        <PageControls
          mode={preMode}
          setMode={setPreMode}
          aggressive={aggressive}
          setAggressive={setAggressive}
          cutForce={cutForce}
          setCutForce={setCutForce}
          keepForce={keepForce}
          setKeepForce={setKeepForce}
        />

        <div className="spacer"></div>
        <div className="row">
          <button className="btn" onClick={onEstimateFiltered} disabled={busy}>
            Estimate LLM Cost (filtered)
          </button>
          <button className="btn green" onClick={onPreprocess} disabled={busy}>
            Run Cut (filtered)
          </button>
        </div>
      </div>

      {/* 3) Industry factors */}
      <div className="card">
        <h2>3) Industry factors <span className="badge">Optional</span></h2>

        <IndustrySection
          industries={industries}
          factorScales={factorScales}
          manualIndustry={manualIndustry}
          setManualIndustry={setManualIndustry}
          selectedIndustry={selectedIndustry}
          setSelectedIndustry={setSelectedIndustry}
          manualFactors={manualFactors}
          setManualFactors={setManualFactors}
        />

        <div className="spacer"></div>
        <div className="row">
          <button className="btn primary" onClick={onAnalyze} disabled={busy}>
            Analyze (LLM)
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="card">
        <h2>Result</h2>
        {!result ? (
          <div className="muted">No result yet. Upload a PDF and click Analyze.</div>
        ) : (
          <ResultsTable result={result} />
        )}
      </div>

      {toast && (
        <div className="card">
          <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
            <div>{toast}</div>
            <button className="btn" onClick={() => setToast(null)}>Dismiss</button>
          </div>
        </div>
      )}
    </div>
  );
}