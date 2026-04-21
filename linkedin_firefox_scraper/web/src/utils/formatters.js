export function formatWorkplaceType(type) {
  if (!type || type === 'N/A') return 'N/A';
  const t = type.toLowerCase();
  if (t.includes('remote') || t.includes('remoto')) return 'Remoto';
  if (t.includes('hybrid') || t.includes('híbrido')) return 'Híbrido';
  if (t.includes('on-site') || t.includes('presencial')) return 'Presencial';
  return type;
}

export function formatJobType(type) {
  if (!type || type === 'N/A') return 'N/A';
  const t = type.toLowerCase();
  if (t.includes('internship') || t.includes('estágio')) return 'Estágio';
  if (t.includes('effective') || t.includes('efetivo')) return 'Efetiva';
  if (t.includes('talent') || t.includes('banco')) return 'Banco de Talentos';
  if (t.includes('pj') || t.includes('legal')) return 'PJ';
  if (t.includes('apprentice') || t.includes('aprendiz')) return 'Jovem Aprendiz';
  if (t.includes('temporary') || t.includes('temporário')) return 'Temporário';
  if (t.includes('associate') || t.includes('associado')) return 'Associado';
  if (t.includes('autonomous') || t.includes('autônomo')) return 'Autônomo';
  if (t.includes('lecturer') || t.includes('docente')) return 'Docente';
  return type;
}