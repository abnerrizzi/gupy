export const formatWorkplaceType = (type) => {
  if (!type) return 'N/A';
  switch (type.toLowerCase()) {
    case 'on-site':
    case 'presencial':
      return 'Presencial';
    case 'remote':
    case 'remoto':
    case 'home office':
      return 'Remoto';
    case 'hybrid':
    case 'híbrido':
      return 'Híbrido';
    default:
      return type;
  }
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
