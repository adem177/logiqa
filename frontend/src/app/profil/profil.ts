import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Auth } from '../core/auth';

/**
 * Page « Mon profil » : nom, e-mail et quelques détails du compte
 * (rôle, statut, lien vers l'espace dédié).
 */
@Component({
  selector: 'app-profil',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './profil.html'
})
export class ProfilComponent implements OnInit {
  private auth = inject(Auth);

  prenom = signal('');
  nom = signal('');
  email = signal('');
  role = signal('');

  fullName = computed(() =>
    `${this.prenom()} ${this.nom()}`.trim() || this.email() || 'Utilisateur'
  );

  initials = computed(() => {
    const p = this.prenom().charAt(0);
    const n = this.nom().charAt(0);
    const initials = `${p}${n}`.toUpperCase();
    return initials || this.email().charAt(0).toUpperCase() || 'U';
  });

  roleLabel = computed(() => {
    switch (this.role()) {
      case 'enseignant':
        return 'Enseignant';
      case 'admin':
        return 'Administrateur';
      default:
        return 'Étudiant';
    }
  });

  espaceLink = computed(() => {
    switch (this.role()) {
      case 'enseignant':
        return '/dashboard-enseignant';
      case 'admin':
        return '/dashboard-admin';
      default:
        return '/cours';
    }
  });

  espaceLabel = computed(() => {
    switch (this.role()) {
      case 'enseignant':
        return 'Espace enseignant';
      case 'admin':
        return 'Espace administrateur';
      default:
        return 'Espace étudiant';
    }
  });

  ngOnInit(): void {
    const user = this.auth.getUser();
    this.prenom.set(user?.prenom || '');
    this.nom.set(user?.nom || '');
    this.email.set(user?.email || '');
    this.role.set(this.auth.getRole() || user?.role || '');
  }

  logout(): void {
    this.auth.logout();
  }
}
