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
  if (!type) return 'N/A';
  switch (type.toLowerCase()) {
    case 'vacancy_type_effective':
    case 'efetivo':
    case 'full-time':
      return 'Efetiva';
    case 'vacancy_type_talent_pool':
    case 'banco de talentos':
      return 'Banco de Talentos';
    case 'estágio':
    case 'internship':
      return 'Estágio';
    default:
      return type;
  }
};
