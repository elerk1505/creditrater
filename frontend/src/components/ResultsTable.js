import React from "react";

export default function ResultsTable({ result }) {
  const rows = result?.table || [];
  return (
    <>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Factor</th>
            <th className="right">Value</th>
            <th>Band</th>
            <th className="right">Weight</th>
            <th className="right">Weighted score</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={7} className="muted">
                No rows returned.
              </td>
            </tr>
          ) : (
            rows.map((r, idx) => (
              <tr key={idx}>
                <td className="right">{idx + 1}</td>
                <td>{r.factor || r.label}</td>
                <td className="right">{r.value ?? ""}</td>
                <td>{r.band ?? ""}</td>
                <td className="right">{r.weight ?? ""}</td>
                <td className="right">{r.weighted_score ?? ""}</td>
                <td>{r.notes ?? ""}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <div className="spacer"></div>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <div className="muted">
          Composite score: <span className="kbd">{result?.composite_score ?? "—"}</span>
        </div>
        <div>
          Final rating:&nbsp;
          <span className="rating">{result?.final_rating ?? "—"}</span>
        </div>
      </div>
    </>
  );
}