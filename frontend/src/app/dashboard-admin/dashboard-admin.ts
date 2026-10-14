import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AdminService, AdminStats, AdminUser, AdminQuiz, AdminRessource, AdminCours } from '../services/admin.service';

type AdminTab = 'dashboard' | 'utilisateurs' | 'matieres' | 'quiz' | 'ressources';

@Component({
  selector: 'app-dashboard-admin',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './dashboard-admin.html'
})
export class AdminDashboardComponent implements OnInit {
  activeTab = signal<AdminTab>('dashboard');
  stats = signal<AdminStats | null>(null);
  users = signal<AdminUser[]>([]);
  coursList = signal<AdminCours[]>([]);
  quizList = signal<AdminQuiz[]>([]);
  ressources = signal<AdminRessource[]>([]);
  loading = signal<boolean>(true);
  actionLoading = signal<number | null>(null);
  message = signal<string>('');
  messageType = signal<'success' | 'error'>('success');

  // Formulaire création de matière
  showCreateForm = signal<boolean>(false);
  creating = signal<boolean>(false);
  newCours = { titre: '', description: '', categorie: '' };

  adminName = '';
  adminInitials = '';

  constructor(private adminService: AdminService) {}

  ngOnInit(): void {
    try {
      const userStr = typeof localStorage !== 'undefined' ? localStorage.getItem('user') : null;
      if (userStr) {
        const user = JSON.parse(userStr);
        this.adminName = `${user.prenom} ${user.nom}`;
        this.adminInitials = `${user.prenom?.[0] || ''}${user.nom?.[0] || ''}`.toUpperCase();
      }
    } catch { /* SSR ou localStorage indisponible */ }
    this.loadStats();
  }

  // ===== Navigation =====
  setTab(tab: AdminTab): void {
    this.activeTab.set(tab);
    this.message.set('');
    switch (tab) {
      case 'dashboard': this.loadStats(); break;
      case 'utilisateurs': this.loadUsers(); break;
      case 'matieres': this.loadCours(); break;
      case 'quiz': this.loadQuiz(); break;
      case 'ressources': this.loadRessources(); break;
    }
  }

  // ===== Chargement =====
  loadStats(): void {
    this.loading.set(true);
    this.adminService.getStats().subscribe({
      next: (stats) => { this.stats.set(stats); this.loading.set(false); },
      error: () => { this.loading.set(false); this.showToast('Erreur lors du chargement des stats.', 'error'); }
    });
  }

  loadUsers(): void {
    this.loading.set(true);
    this.adminService.getUsers().subscribe({
      next: (res) => { this.users.set(res.users); this.loading.set(false); },
      error: () => { this.loading.set(false); this.showToast('Erreur lors du chargement des utilisateurs.', 'error'); }
    });
  }

  loadCours(): void {
    this.loading.set(true);
    this.adminService.getCours().subscribe({
      next: (res) => { this.coursList.set(res.cours); this.loading.set(false); },
      error: () => { this.loading.set(false); this.showToast('Erreur lors du chargement des matières.', 'error'); }
    });
  }

  loadQuiz(): void {
    this.loading.set(true);
    this.adminService.getQuiz().subscribe({
      next: (res) => { this.quizList.set(res.quiz); this.loading.set(false); },
      error: () => { this.loading.set(false); this.showToast('Erreur lors du chargement des quiz.', 'error'); }
    });
  }

  loadRessources(): void {
    this.loading.set(true);
    this.adminService.getRessources().subscribe({
      next: (res) => { this.ressources.set(res.ressources); this.loading.set(false); },
      error: () => { this.loading.set(false); this.showToast('Erreur lors du chargement des ressources.', 'error'); }
    });
  }

  // ===== Actions utilisateurs =====
  toggleStatus(user: AdminUser): void {
    this.actionLoading.set(user.id);
    this.adminService.toggleUserStatus(user.id).subscribe({
      next: () => {
        this.users.update(list => list.map(u =>
          u.id === user.id ? { ...u, status: u.status ? 0 : 1 } : u
        ));
        this.showToast(user.status ? 'Compte désactivé.' : 'Compte activé.', 'success');
        this.actionLoading.set(null);
      },
      error: (err) => {
        this.showToast(err.error?.error || 'Erreur lors de la modification.', 'error');
        this.actionLoading.set(null);
      }
    });
  }

  changeRole(user: AdminUser, event: Event): void {
    const select = event.target as HTMLSelectElement;
    const newRole = select.value;
    this.actionLoading.set(user.id);
    this.adminService.changeUserRole(user.id, newRole).subscribe({
      next: () => {
        this.users.update(list => list.map(u =>
          u.id === user.id ? { ...u, role: newRole as AdminUser['role'] } : u
        ));
        this.showToast(`Rôle modifié en « ${newRole} ».`, 'success');
        this.actionLoading.set(null);
      },
      error: (err) => {
        this.showToast(err.error?.error || 'Erreur lors du changement de rôle.', 'error');
        select.value = user.role;
        this.actionLoading.set(null);
      }
    });
  }

  deleteUser(user: AdminUser): void {
    if (!confirm(`Supprimer définitivement le compte de ${user.prenom} ${user.nom} ?`)) return;
    this.actionLoading.set(user.id);
    this.adminService.deleteUser(user.id).subscribe({
      next: () => {
        this.users.update(list => list.filter(u => u.id !== user.id));
        this.showToast('Utilisateur supprimé.', 'success');
        this.actionLoading.set(null);
      },
      error: (err) => {
        this.showToast(err.error?.error || 'Erreur lors de la suppression.', 'error');
        this.actionLoading.set(null);
      }
    });
  }

  // ===== Actions matières =====
  toggleCreateForm(): void {
    this.showCreateForm.update(v => !v);
    if (!this.showCreateForm()) {
      this.resetCoursForm();
    }
  }

  createCours(): void {
    if (!this.newCours.titre.trim() || !this.newCours.description.trim()) {
      this.showToast('Le titre et la description sont obligatoires.', 'error');
      return;
    }
    this.creating.set(true);
    this.adminService.createCours(this.newCours).subscribe({
      next: (res) => {
        this.coursList.update(list => [{
          id: res.id,
          titre: res.titre,
          description: res.description,
          categorie: res.categorie,
          niveau: res.niveau,
          created_at: new Date().toISOString(),
          enseignant_id: null,
          enseignant_nom: null,
          enseignant_prenom: null,
          nb_chapitres: 0
        }, ...list]);
        this.showToast('Matière créée avec succès !', 'success');
        this.resetCoursForm();
        this.showCreateForm.set(false);
        this.creating.set(false);
      },
      error: (err) => {
        this.showToast(err.error?.error || 'Erreur lors de la création.', 'error');
        this.creating.set(false);
      }
    });
  }

  deleteCours(cours: AdminCours): void {
    if (!confirm(`Supprimer la matière « ${cours.titre} » ? Tout son contenu sera supprimé.`)) return;
    this.actionLoading.set(cours.id);
    this.adminService.deleteCours(cours.id).subscribe({
      next: () => {
        this.coursList.update(list => list.filter(c => c.id !== cours.id));
        this.showToast('Matière supprimée.', 'success');
        this.actionLoading.set(null);
      },
      error: (err) => {
        this.showToast(err.error?.error || 'Erreur lors de la suppression.', 'error');
        this.actionLoading.set(null);
      }
    });
  }

  private resetCoursForm(): void {
    this.newCours = { titre: '', description: '', categorie: '' };
  }

  // ===== Actions quiz =====
  deleteQuiz(quiz: AdminQuiz): void {
    if (!confirm(`Supprimer le quiz « ${quiz.titre} » ?`)) return;
    this.actionLoading.set(quiz.id);
    this.adminService.deleteQuiz(quiz.id).subscribe({
      next: () => {
        this.quizList.update(list => list.filter(q => q.id !== quiz.id));
        this.showToast('Quiz supprimé.', 'success');
        this.actionLoading.set(null);
      },
      error: (err) => {
        this.showToast(err.error?.error || 'Erreur lors de la suppression.', 'error');
        this.actionLoading.set(null);
      }
    });
  }

  // ===== Actions ressources =====
  deleteRessource(ressource: AdminRessource): void {
    if (!confirm(`Supprimer la ressource « ${ressource.nom_original} » ?`)) return;
    this.actionLoading.set(ressource.id);
    this.adminService.deleteRessource(ressource.id).subscribe({
      next: () => {
        this.ressources.update(list => list.filter(r => r.id !== ressource.id));
        this.showToast('Ressource supprimée.', 'success');
        this.actionLoading.set(null);
      },
      error: (err) => {
        this.showToast(err.error?.error || 'Erreur lors de la suppression.', 'error');
        this.actionLoading.set(null);
      }
    });
  }

  // ===== Utilitaires =====
  formatSize(bytes: number | null): string {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  }

  private showToast(msg: string, type: 'success' | 'error'): void {
    this.message.set(msg);
    this.messageType.set(type);
    setTimeout(() => this.message.set(''), 4000);
  }
}
