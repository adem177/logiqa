import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Routes rendues côté serveur (SSR).
 *
 * Les routes avec paramètres (`cours/:id`, `quiz/:id`) ne peuvent pas être
 * pré-rendues à la construction sans `getPrerenderParams` : on les rend donc
 * à la demande. Idem pour les pages qui dépendent de l'API / de la session.
 */
export const serverRoutes: ServerRoute[] = [
  {
    path: 'cours/:id',
    renderMode: RenderMode.Server,
  },
  {
    path: 'quiz/:id',
    renderMode: RenderMode.Server,
  },
  {
    path: '**',
    renderMode: RenderMode.Server,
  },
];
