import React, { useEffect, useMemo } from "react";

export default function IndustrySection({
  industries,
  factorScales,
  manualIndustry, setManualIndustry,
  selectedIndustry, setSelectedIndustry,
  manualFactors, setManualFactors
}) {
  const onPickIndustry = (e) => {
    const key = e.target.value || "";
    const ind = industries.find(
      (x) => x.key === key || x.id === key || x.name === key
    );
    setSelectedIndustry(ind || null);
    setManualFactors({});
  };

  const factors = useMemo(() => {
    if (!selectedIndustry) return [];
    // Expect each industry item to expose something like: { key, name, factors: [{key,label,type,units,weight,...}] }
    return selectedIndustry.factors || [];
  }, [selectedIndustry]);

  const onChangeManualFactor = (fkey, raw) => {
    setManualFactors((m) => ({
      ...m,
      [fkey]: raw,
    }));
  };

  return (
    <>
      <div className="row" style={{ alignItems: "center" }}>
        <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={manualIndustry}
            onChange={(e) => setManualIndustry(e.target.checked)}
          />
          (Optional) I’ll select the industry
        </label>
      </div>

      <div className="spacer"></div>

      <div className="row">
        <div className="col" style={{ maxWidth: 380 }}>
          <label className="muted">(Optional) Select industry</label>
          <select
            disabled={!manualIndustry}
            value={
              selectedIndustry
                ? selectedIndustry.key || selectedIndustry.id || selectedIndustry.name
                : ""
            }
            onChange={onPickIndustry}
          >
            <option value="">— None —</option>
            {industries.map((ind) => {
              const val = ind.key || ind.id || ind.name;
              const label = ind.name || ind.title || val;
              return (
                <option key={val} value={val}>
                  {label}
                </option>
              );
            })}
          </select>
        </div>
      </div>

      <div className="spacer"></div>

      {manualIndustry && selectedIndustry ? (
        <>
          <div className="muted" style={{ marginBottom: 10 }}>
            Factor weights (enter a <b>number</b> or band; numbers are auto-converted to bands using the industry’s thresholds).
          </div>
          <table>
            <thead>
              <tr>
                <th style={{ width: 28 }}>#</th>
                <th>Factor</th>
                <th>Type</th>
                <th>Units</th>
                <th>Weight (number)</th>
                <th className="center">→ Band</th>
              </tr>
            </thead>
            <tbody>
              {factors.length === 0 && (
                <tr><td colSpan={6} className="muted">This industry has no exposed factors.</td></tr>
              )}
              {factors.map((f, idx) => {
                const fkey = f.key || f.id || f.name;
                const placeholder = f.type === "numeric" ? "enter a number" : "enter a band (e.g., Baa2)";
                const val = manualFactors[fkey] ?? "";
                return (
                  <tr key={fkey}>
                    <td className="right">{idx + 1}</td>
                    <td>{f.label || f.name || fkey}</td>
                    <td>{f.type || "numeric"}</td>
                    <td>{f.units || ""}</td>
                    <td>
                      <input
                        value={val}
                        onChange={(e) => onChangeManualFactor(fkey, e.target.value)}
                        placeholder={placeholder}
                      />
                    </td>
                    <td className="center">—</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      ) : (
        <div className="muted">
          If you don’t select an industry, the LLM will infer industry and factors automatically.
        </div>
      )}
    </>
  );
}