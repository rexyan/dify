const translation = {
  title: 'Paramètres de connaissance',
  desc: 'Ici, vous pouvez modifier les propriétés et les méthodes de fonctionnement de la Connaissance.',
  form: {
    name: 'Nom de la Connaissance',
    namePlaceholder: 'Veuillez entrer le nom de la Connaissance',
    nameError: 'Le nom ne peut pas être vide',
    desc: 'Description des connaissances',
    descInfo: 'Veuillez rédiger une description textuelle claire pour décrire le contenu de la Connaissance. Cette description sera utilisée comme base pour la correspondance lors de la sélection parmi plusieurs Connaissances pour l\'inférence.',
    descPlaceholder: 'Décrivez ce qui se trouve dans cette Connaissance. Une description détaillée permet à l\'IA d\'accéder au contenu de la Connaissance en temps opportun. Si vide, Dify utilisera la stratégie de hit par défaut.',
    descWrite: 'Apprenez comment rédiger une bonne description de connaissance.',
    permissions: 'Autorisations',
    permissionsOnlyMe: 'Seulement moi',
    permissionsAllMember: 'Tous les membres de l\'équipe',
    indexMethod: 'Méthode d\'Indexation',
    indexMethodHighQuality: 'Haute Qualité',
    indexMethodHighQualityTip: 'Appelez l\'interface d\'embedding d\'OpenAI pour le traitement afin de fournir une précision plus élevée lorsque les utilisateurs font une requête.',
    indexMethodEconomy: 'Économique',
    indexMethodEconomyTip: 'Utilisez des moteurs vectoriels hors ligne, des index de mots-clés, etc. pour réduire la précision sans dépenser de jetons',
    embeddingModel: 'Modèle d\'Embedding',
    embeddingModelTip: 'Changez le modèle intégré, veuillez aller à',
    embeddingModelTipLink: 'Paramètres',
    retrievalSetting: {
      title: 'Paramètre de récupération',
      learnMore: 'En savoir plus',
      description: 'à propos de la méthode de récupération.',
      longDescription: 'À propos de la méthode de récupération, vous pouvez la modifier à tout moment dans les paramètres de Connaissance.',
    },
    save: 'Enregistrer',
  },
}

export default translation
