import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Auth } from './auth';

/**
 * Garde générique : protège une route nécessitant un utilisateur connecté.
 * - Si non connecté OU token expiré → redirection vers /login avec returnUrl
 *   (après connexion, l'utilisateur revient à la page voulue).
 */
export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(Auth);
  const router = inject(Router);

  if (auth.isLoggedIn()) return true;

  // Token absent ou expiré → login avec retour automatique
  return router.createUrlTree(['/login'], {
    queryParams: { returnUrl: state.url }
  });
};

/**
 * Garde par rôle : protège une route nécessitant un rôle précis.
 * - Non connecté / token expiré → /login avec returnUrl
 * - Mauvais rôle → redirection vers son propre espace
 */
export const roleGuard = (roles: string[]): CanActivateFn => (route, state) => {
  const auth = inject(Auth);
  const router = inject(Router);

  if (!auth.isLoggedIn()) {
    return router.createUrlTree(['/login'], {
      queryParams: { returnUrl: state.url }
    });
  }

  if (auth.hasRole(roles)) return true;

  const role = auth.getRole();
  const home = role === 'admin' ? '/dashboard-admin'
             : role === 'enseignant' ? '/dashboard-enseignant'
             : '/cours';
  return router.createUrlTree([home]);
};
