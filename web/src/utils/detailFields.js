import { formatJobType, formatWorkplaceType } from './formatters';

const DATE_FMT = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: 'long',
  year: 'numeric',
});

const DATETIME_FMT = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

const RELATIVE_FMT = typeof Intl.RelativeTimeFormat === 'function'
  ? new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' })
  : null;

export function formatDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return DATE_FMT.format(d);
}

export function formatDateTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return DATETIME_FMT.format(d);
}

export function formatRelative(iso) {
  if (!iso || !RELATIVE_FMT) return formatDateTime(iso);
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  const diffMs = d.getTime() - Date.now();
  const diffSec = Math.round(diffMs / 1000);
  const abs = Math.abs(diffSec);
  const units = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ];
  for (const [unit, secs] of units) {
    if (abs >= secs) return RELATIVE_FMT.format(Math.round(diffSec / secs), unit);
  }
  return RELATIVE_FMT.format(diffSec, 'second');
}

export function formatCountry(code) {
  if (!code) return null;
  const v = code.trim().toUpperCase();
  if (v === 'BRA' || v === 'BR' || v === 'BRAZIL') return 'Brasil';
  return code;
}

export function formatSeniority(value) {
  if (!value) return null;
  const key = value.trim().toLowerCase();
  const map = {
    'internship': 'Estágio',
    'entry level': 'Júnior',
    'associate': 'Pleno',
    'mid-senior level': 'Sênior',
    'director': 'Diretoria',
    'executive': 'Executivo',
    'not applicable': null,
  };
  if (key in map) return map[key];
  return value;
}

// Unifies the three source schemas into a single list of {label, value}
// pairs so the UI can render a consistent "facts" grid. Each caller decides
// which labels (if any) duplicate the outer modal header and filters them.
export function extractCommonFacts(detail) {
  if (!detail) return [];
  const facts = [];
  const push = (label, value) => {
    if (value === null || value === undefined || value === '') return;
    facts.push({ label, value });
  };

  if (detail.source === 'gupy') {
    push('Publicado em', formatDate(detail.published_at));
    push('Tipo de contratação', formatJobType(detail.job_type));
    push('Modalidade', formatWorkplaceType(detail.workplace_type));
    push('País', formatCountry(detail.country));
  } else if (detail.source === 'inhire') {
    push('Publicado em', formatDate(detail.published_at));
    push('Tipo de contratação', formatJobType(detail.contract_type));
    push('Modalidade', formatWorkplaceType(detail.workplace_type));
    push('Localização', detail.location);
    push('Complemento', detail.location_complement);
  } else if (detail.source === 'linkedin') {
    push('Publicado em', formatDate(detail.posted_at));
    push('Nível', formatSeniority(detail.seniority));
    push('Tipo de contratação', formatJobType(detail.employment_type));
    push('Função', detail.job_function);
    push('Indústrias', detail.industries);
    if (typeof detail.num_applicants === 'number') {
      push('Candidatos', detail.num_applicants.toLocaleString('pt-BR'));
    }
  }

  return facts;
}
