import React from "react";
import ModeSelector from "./ModeSelector.jsx";

export default function PageControls({
  mode, setMode,
  aggressive, setAggressive,
  cutForce, setCutForce,
  keepForce, setKeepForce
}) {
  return (
    <>
      <div className="row">
        <div className="col" style={{ maxWidth: 220 }}>
          <label className="muted">Aggressive</label>
          <div>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={aggressive}
                onChange={(e) => setAggressive(e.target.checked)}
              />
              Aggressive cut
            </label>
          </div>
        </div>
        <div className="col" style={{ maxWidth: 260 }}>
          <label className="muted">Mode (applies to preprocess)</label>
          <ModeSelector value={mode} onChange={setMode} />
        </div>
        <div className="col">
          <label className="muted">Force cut (comma list)</label>
          <input
            placeholder="e.g. 11, 59-128 (ranges allowed)"
            value={cutForce}
            onChange={(e) => setCutForce(e.target.value)}
          />
        </div>
        <div className="col">
          <label className="muted">Force keep (comma list)</label>
          <input
            placeholder="e.g. 1-3, 8"
            value={keepForce}
            onChange={(e) => setKeepForce(e.target.value)}
          />
        </div>
      </div>
      <div className="hint">
        <b>Tip:</b> “Aggressive” removes ESG/CSR sections, glossaries, disclaimers, appendices, etc.
      </div>
    </>
  );
}