export const formatWorkplaceType = (type) => {
  if (!type) return 'N/A';
  const t = type.toLowerCase();
  if (t === 'on-site' || t === 'presencial') return 'Presencial';
  if (t === 'remote' || t === 'remoto' || t === 'home office') return 'Remoto';
  if (t === 'hybrid' || t === 'híbrido') return 'Híbrido';
  return type;
};

export const formatJobType = (type) => {
  if (!type || type === 'N/A') return 'Outros';
  switch (type.toLowerCase()) {
    case 'vacancy_type_effective':
    case 'efetivo':
    case 'full-time':
      return 'Efetiva';
    case 'vacancy_type_talent_pool':
    case 'banco de talentos':
      return 'Banco de Talentos';
    case 'vacancy_type_internship':
    case 'estágio':
    case 'internship':
      return 'Estágio';
    case 'vacancy_type_apprentice':
    case 'aprendiz':
      return 'Jovem Aprendiz';
    case 'vacancy_type_temporary':
    case 'temporário':
      return 'Temporário';
    case 'vacancy_type_lecturer':
    case 'palestrante':
    case 'docente':
      return 'Docente';
    case 'vacancy_legal_entity':
    case 'pj':
      return 'PJ';
    case 'vacancy_type_associate':
    case 'associado':
      return 'Associado';
    case 'vacancy_type_autonomous':
    case 'autônomo':
      return 'Autônomo';
    default:
      return type;
  }
};
