import React, { useCallback, useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

/**
 * Place words on a canvas using a spiral layout.
 * Each word is sized proportionally to its frequency value.
 */
function layoutWords(words, width, height, scaleFactor) {
  if (!words.length) return [];

  // Logarithmic scale for smoother size distribution
  const maxVal = Math.log(words[0].value || 1);
  const minVal = Math.log(words[words.length - 1].value || 1);
  const range = Math.max(maxVal - minVal, 0.1);

  // Match the reference image: huge fonts, very dense
  const minFont = 14 * scaleFactor;
  const maxFont = 100 * scaleFactor;

  const placed = [];
  const occupied = [];

  // Offscreen canvas for text measurement
  const measureCanvas = document.createElement('canvas');
  const mCtx = measureCanvas.getContext('2d');

  const cx = width / 2;
  const cy = height / 2;
  const aspect = width / height;

  for (let idx = 0; idx < words.length; idx++) {
    const word = words[idx];
    const t = (Math.log(word.value || 1) - minVal) / range;
    const fontSize = minFont + t * (maxFont - minFont);
    
    // Impact or Arial Black gives that dense, heavy look from the image
    mCtx.font = `900 ${Math.round(fontSize)}px Impact, "Arial Black", sans-serif`;
    const metrics = mCtx.measureText(word.text);
    
    // Tighter bounding box for dense packing
    const textWidth = metrics.width + 2;
    const textHeight = fontSize * 0.85;

    // 25% chance to be vertical (rotated -90deg)
    // Keep the top 2 biggest words horizontal for readability
    const isVertical = idx > 1 && Math.random() < 0.25;

    const w = isVertical ? textHeight : textWidth;
    const h = isVertical ? textWidth : textHeight;

    let foundSpot = false;
    let angle = (idx * 0.3) % (Math.PI * 2);
    let radius = 0;

    // Expand search radius heavily to ensure we find a spot
    while (radius < Math.max(width, height) * 1.5) {
      const x = cx + radius * Math.cos(angle) * aspect - w / 2;
      const y = cy + radius * Math.sin(angle) - h / 2;

      // Bounds check
      if (x >= 4 && y >= 4 && x + w <= width - 4 && y + h <= height - 4) {
        // Collision check against already placed words
        let collides = false;
        for (let i = 0; i < occupied.length; i++) {
          const o = occupied[i];
          if (x < o.x + o.w && x + w > o.x && y < o.y + o.h && y + h > o.y) {
            collides = true;
            break;
          }
        }
        
        if (!collides) {
          placed.push({ ...word, x, y, w, h, fontSize, isVertical });
          occupied.push({ x, y, w, h });
          foundSpot = true;
          break;
        }
      }

      angle += 0.25;
      radius += 0.4;
    }
  }

  return placed;
}

function drawCloud(canvas, placedWords, hoveredWord) {
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width / dpr;
  const h = canvas.height / dpr;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Color palette matching the classic word cloud style
  const palette = [
    '#102a43', // very dark blue
    '#820000', // dark red
    '#9a3412', // rust orange
    '#243b53', // dark blue-grey
    '#b91c1c', // red
    '#0f172a', // almost black
    '#ea580c', // orange
    '#451a03', // dark brown
  ];

  for (let i = 0; i < placedWords.length; i++) {
    const pw = placedWords[i];
    const isHovered = hoveredWord && hoveredWord.text === pw.text;

    ctx.save();
    ctx.font = `900 ${Math.round(pw.fontSize)}px Impact, "Arial Black", sans-serif`;
    ctx.fillStyle = isHovered ? '#3b82f6' : palette[i % palette.length];
    ctx.globalAlpha = isHovered ? 1 : 0.95;
    ctx.textBaseline = 'top';

    if (isHovered) {
      ctx.shadowColor = 'rgba(59, 130, 246, 0.4)';
      ctx.shadowBlur = 8;
    }

    if (pw.isVertical) {
      // For vertical text, rotate -90 degrees around the bottom-left corner of the bounding box
      ctx.translate(pw.x * dpr, (pw.y + pw.h) * dpr);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(pw.text, 0, 0);
    } else {
      ctx.translate(pw.x * dpr, pw.y * dpr);
      ctx.fillText(pw.text, 0, 0);
    }
    ctx.restore();
  }

  // Draw tooltip
  if (hoveredWord) {
    const pw = placedWords.find((p) => p.text === hoveredWord.text);
    if (pw) {
      const label = `${pw.text}: ${pw.value}`;
      ctx.save();
      ctx.font = `600 13px "Inter", system-ui, sans-serif`;
      const tm = ctx.measureText(label);
      const tipW = tm.width + 16;
      const tipH = 28;
      let tipX = (pw.x + pw.w / 2) * dpr - tipW / 2;
      let tipY = pw.y * dpr - tipH - 6;
      if (tipY < 4) tipY = (pw.y + pw.h) * dpr + 4;
      if (tipX < 4) tipX = 4;
      if (tipX + tipW > w * dpr) tipX = w * dpr - tipW - 4;

      ctx.fillStyle = 'rgba(15,23,42,0.92)';
      ctx.beginPath();
      const r = 6;
      ctx.moveTo(tipX + r, tipY);
      ctx.lineTo(tipX + tipW - r, tipY);
      ctx.quadraticCurveTo(tipX + tipW, tipY, tipX + tipW, tipY + r);
      ctx.lineTo(tipX + tipW, tipY + tipH - r);
      ctx.quadraticCurveTo(tipX + tipW, tipY + tipH, tipX + tipW - r, tipY + tipH);
      ctx.lineTo(tipX + r, tipY + tipH);
      ctx.quadraticCurveTo(tipX, tipY + tipH, tipX, tipY + tipH - r);
      ctx.lineTo(tipX, tipY + r);
      ctx.quadraticCurveTo(tipX, tipY, tipX + r, tipY);
      ctx.closePath();
      ctx.fill();

      ctx.fillStyle = '#fff';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, tipX + 8, tipY + tipH / 2);
      ctx.restore();
    }
  }
}

function WordCloud({ onWordClick }) {
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('titles');
  const [hovered, setHovered] = useState(null);
  const [placedWords, setPlacedWords] = useState([]);

  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Fetch word data
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setWords([]);
    setPlacedWords([]);
    setHovered(null);

    (async () => {
      try {
        const res = await fetch(
          `${API_URL}/wordcloud?type=${tab}&limit=150`,
          { signal: controller.signal }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setWords(data.words || []);
      } catch (err) {
        if (err.name === 'AbortError') return;
        setError('Falha ao carregar dados. Verifique se a API está online.');
      } finally {
        setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [tab]);

  // Layout words when data or container size changes
  useEffect(() => {
    if (!words.length || !containerRef.current) {
      setPlacedWords([]);
      return;
    }
    const rect = containerRef.current.getBoundingClientRect();
    const w = rect.width || 800;
    const h = Math.max(rect.height, 420);
    const dpr = window.devicePixelRatio || 1;

    const scaleFactor = Math.min(w / 800, 1.2);
    const placed = layoutWords(words, w, h, scaleFactor);
    setPlacedWords(placed);

    const canvas = canvasRef.current;
    if (canvas) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
    }
  }, [words]);

  // Draw
  useEffect(() => {
    if (!canvasRef.current || !placedWords.length) return;
    drawCloud(canvasRef.current, placedWords, hovered);
  }, [placedWords, hovered]);

  // Hit-test on mouse move
  const handleMouseMove = useCallback(
    (e) => {
      if (!placedWords.length || !canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const hit = placedWords.find(
        (pw) => mx >= pw.x && mx <= pw.x + pw.w && my >= pw.y && my <= pw.y + pw.h
      );
      setHovered(hit || null);
      canvasRef.current.style.cursor = hit ? 'pointer' : 'default';
    },
    [placedWords]
  );

  const handleClick = useCallback(
    (e) => {
      if (!placedWords.length || !canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const hit = placedWords.find(
        (pw) => mx >= pw.x && mx <= pw.x + pw.w && my >= pw.y && my <= pw.y + pw.h
      );
      if (hit && onWordClick) {
        onWordClick(hit.text);
      }
    },
    [placedWords, onWordClick]
  );

  const handleMouseLeave = useCallback(() => setHovered(null), []);

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Word Cloud</h2>
          <p>Visualize as palavras mais frequentes nas vagas.</p>
        </div>
      </div>

      <div className="wc-tabs">
        <button
          type="button"
          className={'wc-tab' + (tab === 'titles' ? ' wc-tab-active' : '')}
          onClick={() => setTab('titles')}
        >
          Títulos
        </button>
        <button
          type="button"
          className={'wc-tab' + (tab === 'descriptions' ? ' wc-tab-active' : '')}
          onClick={() => setTab('descriptions')}
        >
          Descrições
        </button>
      </div>

      <div className="wc-container" ref={containerRef}>
        {loading && (
          <div className="wc-loading">
            <div className="wc-spinner" />
            <span>Carregando…</span>
          </div>
        )}
        {error && <div className="wc-error">{error}</div>}
        {!loading && !error && !words.length && (
          <div className="wc-empty">
            <div className="wc-empty-icon">☁</div>
            <p>Nenhuma palavra encontrada.</p>
            <p className="wc-empty-hint">
              {tab === 'descriptions'
                ? 'Sincronize detalhes de algumas vagas em "Buscar vagas" para gerar a nuvem de descrições.'
                : 'Aguarde a primeira execução do scraper.'}
            </p>
          </div>
        )}
        {!loading && !error && words.length > 0 && (
          <canvas
            ref={canvasRef}
            className="wc-canvas"
            onMouseMove={handleMouseMove}
            onClick={handleClick}
            onMouseLeave={handleMouseLeave}
          />
        )}
      </div>

      {!loading && words.length > 0 && (
        <p className="wc-hint">
          Clique em uma palavra para buscá-la em &quot;Buscar vagas&quot;.
        </p>
      )}
    </>
  );
}

WordCloud.propTypes = {
  onWordClick: PropTypes.func,
};

WordCloud.defaultProps = {
  onWordClick: null,
};

export default WordCloud;
