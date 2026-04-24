import React, { useState } from 'react';
import PropTypes from 'prop-types';

function isObject(v) {
  return v && typeof v === 'object' && !Array.isArray(v);
}

function summary(value) {
  if (Array.isArray(value)) return `Array(${value.length})`;
  if (isObject(value)) return `{${Object.keys(value).length} keys}`;
  return '';
}

function Leaf({ value }) {
  if (value === null) return <span className="json-null">null</span>;
  if (typeof value === 'boolean') return <span className="json-bool">{String(value)}</span>;
  if (typeof value === 'number') return <span className="json-number">{value}</span>;
  if (typeof value === 'string') return <span className="json-string">"{value}"</span>;
  return <span>{String(value)}</span>;
}

Leaf.propTypes = { value: PropTypes.any };

function Node({ label, value, depth, defaultOpen }) {
  const [open, setOpen] = useState(Boolean(defaultOpen));
  const branch = Array.isArray(value) || isObject(value);

  if (!branch) {
    return (
      <div className="json-row" style={{ paddingLeft: `${depth * 12}px` }}>
        {label !== undefined && <span className="json-key">{label}:</span>}
        <Leaf value={value} />
      </div>
    );
  }

  const entries = Array.isArray(value)
    ? value.map((v, i) => [i, v])
    : Object.entries(value);

  return (
    <div className="json-branch">
      <div
        className="json-row json-toggle"
        style={{ paddingLeft: `${depth * 12}px` }}
        onClick={() => setOpen(!open)}
      >
        <span className="json-caret">{open ? '▾' : '▸'}</span>
        {label !== undefined && <span className="json-key">{label}:</span>}
        <span className="json-summary">{summary(value)}</span>
      </div>
      {open && (
        <div className="json-children">
          {entries.map(([k, v]) => (
            <Node key={k} label={k} value={v} depth={depth + 1} defaultOpen={false} />
          ))}
        </div>
      )}
    </div>
  );
}

Node.propTypes = {
  label: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  value: PropTypes.any,
  depth: PropTypes.number.isRequired,
  defaultOpen: PropTypes.bool,
};

function JsonTree({ raw }) {
  if (!raw) return null;
  let parsed;
  try {
    parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
  } catch (e) {
    return <pre className="json-parse-error">JSON parse error: {e.message}</pre>;
  }
  return (
    <div className="json-tree">
      <Node value={parsed} depth={0} defaultOpen />
    </div>
  );
}

JsonTree.propTypes = {
  raw: PropTypes.oneOfType([PropTypes.string, PropTypes.object, PropTypes.array]),
};

export default JsonTree;
