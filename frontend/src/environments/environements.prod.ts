// Configuration de production : le backend Flask sert lui-même le bundle
// Angular, donc l'API est sur le MÊME origine → on appelle des URL relatives
// ("/api/..."). Aucune configuration CORS ni nom de domaine à maintenir.
export const environment = {
  production: true,
  apiUrl: ''
};
