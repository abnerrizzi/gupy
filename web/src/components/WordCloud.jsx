import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const PREMIUM_PALETTE = [
  '#0f172a', // slate 900
  '#1e293b', // slate 800
  '#1d4ed8', // blue 700
  '#2563eb', // blue 600
  '#4338ca', // indigo 700
  '#4f46e5', // indigo 600
  '#334155', // slate 700
  '#0f766e', // teal 700
  '#0369a1', // sky 700
];

function layoutWords(words, width, height, scaleFactor) {
  if (!words.length) return [];

  const maxVal = Math.log(words[0].value || 1);
  const minVal = Math.log(words[words.length - 1].value || 1);
  const range = Math.max(maxVal - minVal, 0.1);

  // Modern, cleaner size range (not overly chaotic)
  const minFont = 14 * scaleFactor;
  const maxFont = 68 * scaleFactor;

  const placed = [];
  const occupied = [];

  const measureCanvas = document.createElement('canvas');
  const mCtx = measureCanvas.getContext('2d');

  const cx = width / 2;
  const cy = height / 2;
  const aspect = width / height;

  for (let idx = 0; idx < words.length; idx++) {
    const word = words[idx];
    const t = (Math.log(word.value || 1) - minVal) / range;
    const fontSize = minFont + t * (maxFont - minFont);
    
    // Weight scales with size for a premium typographic hierarchy
    const weight = fontSize > 44 ? 800 : fontSize > 24 ? 700 : 600;
    
    mCtx.font = `${weight} ${Math.round(fontSize)}px "Inter", system-ui, sans-serif`;
    const metrics = mCtx.measureText(word.text);
    
    // Tighter width bounds, line-height 1.1 equivalent
    const w = metrics.width + 4;
    const h = fontSize * 1.1;

    let foundSpot = false;
    // Golden angle approximation for organic spiral distribution
    let angle = idx * 2.39996; 
    let radius = 0;

    while (radius < Math.max(width, height) * 1.2) {
      const x = cx + radius * Math.cos(angle) * aspect - w / 2;
      const y = cy + radius * Math.sin(angle) - h / 2;

      // Ensure words stay comfortably inside the container
      if (x >= 10 && y >= 10 && x + w <= width - 10 && y + h <= height - 10) {
        let collides = false;
        for (let i = 0; i < occupied.length; i++) {
          const o = occupied[i];
          if (x < o.x + o.w && x + w > o.x && y < o.y + o.h && y + h > o.y) {
            collides = true;
            break;
          }
        }
        
        if (!collides) {
          placed.push({ 
            ...word, 
            x, 
            y, 
            fontSize, 
            weight,
            color: PREMIUM_PALETTE[idx % PREMIUM_PALETTE.length] 
          });
          occupied.push({ x, y, w, h });
          foundSpot = true;
          break;
        }
      }

      angle += 0.35;
      radius += 0.5;
    }
  }

  return placed;
}

function WordCloud({ onWordClick }) {
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('titles');
  const [placedWords, setPlacedWords] = useState([]);

  const containerRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setWords([]);
    setPlacedWords([]);

    (async () => {
      try {
        const res = await fetch(
          `${API_URL}/wordcloud?type=${tab}&limit=120`,
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

  useEffect(() => {
    if (!words.length || !containerRef.current) {
      setPlacedWords([]);
      return;
    }
    const rect = containerRef.current.getBoundingClientRect();
    const w = rect.width || 800;
    const h = Math.max(rect.height, 460);

    const scaleFactor = Math.min(w / 800, 1.2);
    const placed = layoutWords(words, w, h, scaleFactor);
    setPlacedWords(placed);
  }, [words]);

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
            <span>Processando dados...</span>
          </div>
        )}
        {error && <div className="wc-error">{error}</div>}
        {!loading && !error && !words.length && (
          <div className="wc-empty">
            <div className="wc-empty-icon">✨</div>
            <p>Nenhuma palavra encontrada.</p>
            <p className="wc-empty-hint">
              {tab === 'descriptions'
                ? 'Sincronize detalhes de algumas vagas em "Buscar vagas" para gerar a nuvem de descrições.'
                : 'Aguarde a primeira execução do scraper.'}
            </p>
          </div>
        )}
        {!loading && !error && placedWords.length > 0 && (
          <div className="wc-dom-cloud">
            {placedWords.map((pw) => (
              <button
                key={pw.text}
                className="wc-dom-word"
                onClick={() => onWordClick && onWordClick(pw.text)}
                style={{
                  left: pw.x,
                  top: pw.y,
                  fontSize: pw.fontSize,
                  fontWeight: pw.weight,
                  color: pw.color,
                }}
                title={`Frequência: ${pw.value}`}
              >
                {pw.text}
              </button>
            ))}
          </div>
        )}
      </div>
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
