import React from "react";

const options = [
  { value: "text", label: "Text" },
  { value: "text+layout", label: "Text + layout" },
  { value: "page_images", label: "Page images" },
];

export default function ModeSelector({ value, onChange }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}