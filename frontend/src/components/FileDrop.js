import React, { useCallback, useRef, useState } from "react";

export default function FileDrop({ onFile, file, busy }) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    (files) => {
      const f = files && files[0];
      if (!f) return;
      if (!/\.pdf$/i.test(f.name)) {
        alert("Please choose a PDF file.");
        return;
      }
      onFile(f);
    },
    [onFile]
  );

  return (
    <div className="row">
      <div
        className="dropzone col"
        style={{
          borderColor: dragOver ? "#3a72ff" : undefined,
          background: dragOver ? "#0e1630" : undefined,
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <div>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>
            {file ? file.name : "Drop PDF here or "}
            <button
              className="btn"
              onClick={() => inputRef.current?.click()}
              disabled={busy}
            >
              Choose file
            </button>
          </div>
          <div className="hint">
            The file is kept in memory; nothing is stored.
          </div>
          <input
            type="file"
            accept="application/pdf"
            ref={inputRef}
            style={{ display: "none" }}
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>
      </div>
    </div>
  );
}