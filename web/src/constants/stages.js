export const STAGE_META = {
  salva:    { label: 'Salva',      cls: 'stage-salva',    dot: '#94a3b8' },
  aplicada: { label: 'Aplicada',   cls: 'stage-aplicada', dot: '#2563eb' },
  entrev:   { label: 'Entrevista', cls: 'stage-entrev',   dot: '#d97706' },
  prop:     { label: 'Proposta',   cls: 'stage-prop',     dot: '#10b981' },
  encer:    { label: 'Encerrada',  cls: 'stage-encer',    dot: '#ef4444' },
};

export const STAGE_ORDER = ['salva', 'aplicada', 'entrev', 'prop', 'encer'];

export const STAGE_NEXT = {
  salva: 'aplicada',
  aplicada: 'entrev',
  entrev: 'prop',
  prop: 'encer',
  encer: 'encer',
};
