import { Component, inject, OnInit, OnDestroy, ElementRef, HostListener, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { EnseignantService, EnseignantCours } from '../services/enseignant.service';
import { Auth } from '../core/auth';
import { LogoutConfirmComponent } from '../shared/components/logout-confirm/logout-confirm';

interface StatCard {
  icon: string;
  iconClass: string;
  value: string;
  title: string;
  sub: string;
  subMuted?: boolean;
}

interface ActivityItem {
  id: number;
  text: string;
  date: string;
}

@Component({
  selector: 'app-teacher-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule, LogoutConfirmComponent],
  templateUrl: './enseignant.html'
})
export class TeacherDashboardComponent implements OnInit, OnDestroy {
  private router = inject(Router);
  private enseignantService = inject(EnseignantService);
  private auth = inject(Auth);
  private elementRef = inject(ElementRef);
  private destroy$ = new Subject<void>();

  teacherName = '';
  teacherLastName = '';
  teacherEmail = '';
  teacherInitials = 'EN';

  isProfileOpen = false;

  // Cours de l'enseignant (chargés depuis l'API)
  // Signaux : en mode zoneless, seuls les signaux (ou les événements)
  // déclenchent la détection de changement — une simple affectation dans
  // subscribe() laisserait la vue bloquée jusqu'au prochain clic.
  coursList = signal<EnseignantCours[]>([]);
  loading = signal(false);

  // État du formulaire d'édition
  showEditForm = false;
  editingCours: EnseignantCours | null = null;
  editData = { titre: '', description: '', categorie: '', niveau: 'Débutant' };
  saving = signal(false);

  // Confirmation de suppression
  coursToDelete: EnseignantCours | null = null;
  deleting = signal(false);

  // Message toast
  toastMessage = signal('');
  toastType = signal<'success' | 'error'>('success');
  private toastTimer: any = null;

  ngOnInit(): void {
    this.loadUserInfo();
    this.loadCours();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.toastTimer) clearTimeout(this.toastTimer);
  }

  private loadUserInfo(): void {
    const user = this.auth.getUser();
    if (user) {
      this.teacherName = user.prenom || '';
      this.teacherLastName = user.nom || '';
      this.teacherEmail = user.email || '';
      const first = this.teacherName ? this.teacherName[0] : '';
      const last = this.teacherLastName ? this.teacherLastName[0] : '';
      this.teacherInitials = (first + last).toUpperCase() || 'EN';
    }
  }

  private loadCours(): void {
    this.loading.set(true);
    this.enseignantService.getMesCours()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data) => {
          this.coursList.set(data || []);
          this.loading.set(false);
        },
        error: () => {
          this.coursList.set([]);
          this.loading.set(false);
        }
      });
  }

  // ===== Actions =====

  /** Consulter : ouvre la page de lecture du cours */
  viewCours(coursId: number): void {
    this.router.navigate(['/cours', coursId]);
  }

  /** Modifier : ouvre le formulaire d'édition pré-rempli */
  editCours(cours: EnseignantCours): void {
    this.editingCours = cours;
    this.editData = {
      titre: cours.titre,
      description: cours.description,
      categorie: cours.categorie,
      niveau: cours.niveau || 'Débutant'
    };
    this.showEditForm = true;
  }

  cancelEdit(): void {
    this.showEditForm = false;
    this.editingCours = null;
  }

  saveEdit(): void {
    if (!this.editingCours) return;
    if (!this.editData.titre.trim() || !this.editData.description.trim()) {
      this.showToast('Le titre et la description sont obligatoires.', 'error');
      return;
    }
    const coursId = this.editingCours.id;
    this.saving.set(true);
    this.enseignantService.updateCours(coursId, this.editData)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.coursList.update(list =>
            list.map(c => c.id === coursId
              ? {
                  ...c,
                  titre: this.editData.titre,
                  description: this.editData.description,
                  categorie: this.editData.categorie,
                  niveau: this.editData.niveau
                }
              : c)
          );
          this.saving.set(false);
          this.showEditForm = false;
          this.editingCours = null;
          this.showToast('Cours modifié avec succès !', 'success');
        },
        error: (err) => {
          this.saving.set(false);
          this.showToast(err?.error?.error || 'Erreur lors de la modification.', 'error');
        }
      });
  }

  /** Supprimer : demande confirmation puis supprime */
  confirmDelete(cours: EnseignantCours): void {
    this.coursToDelete = cours;
  }

  cancelDelete(): void {
    this.coursToDelete = null;
  }

  deleteCours(): void {
    if (!this.coursToDelete) return;
    this.deleting.set(true);
    const id = this.coursToDelete.id;
    this.enseignantService.deleteCours(id)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.coursList.update(list => list.filter(c => c.id !== id));
          this.deleting.set(false);
          this.coursToDelete = null;
          this.showToast('Cours supprimé.', 'success');
        },
        error: (err) => {
          this.deleting.set(false);
          this.showToast(err?.error?.error || 'Erreur lors de la suppression.', 'error');
        }
      });
  }

  private showToast(message: string, type: 'success' | 'error'): void {
    this.toastMessage.set(message);
    this.toastType.set(type);
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => this.toastMessage.set(''), 3500);
  }

  // ===== Utilitaires =====
  toggleProfile(event?: MouseEvent): void {
    if (event) event.stopPropagation();
    this.isProfileOpen = !this.isProfileOpen;
  }

  closeProfile(): void {
    this.isProfileOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isProfileOpen = false;
    }
  }

  get stats(): StatCard[] {
    return [
      {
        icon: '📘',
        iconClass: 'icon-blue',
        value: String(this.coursList().length),
        title: 'Cours publiés',
        sub: this.coursList().length === 0 ? 'Aucun pour le moment' : `${this.coursList().length} cours actif(s)`
      },
      {
        icon: '📄',
        iconClass: 'icon-purple',
        value: String(this.totalChapitres),
        title: 'Chapitres',
        sub: `${this.totalChapitres} chapitre(s) au total`
      }
    ];
  }

  get totalChapitres(): number {
    return this.coursList().reduce((sum, c) => sum + (c.nb_chapitres || 0), 0);
  }

  activities: ActivityItem[] = [];

  onCreateCourse(): void {
    this.router.navigate(['/enseignant/upload-cours']);
  }

  onGenererQuiz(): void {
    this.router.navigate(['/generer-quiz']);
  }

  goHome(): void {
    this.router.navigate(['/']);
  }

  /** Clic sur le logo du bandeau : demande de confirmation, puis déconnexion. */
  showLogoutConfirm = false;

  askLogout(): void {
    this.showLogoutConfirm = true;
  }

  /** Confirmation « Oui » : ferme la fenêtre et déconnecte. */
  confirmLogout(): void {
    this.showLogoutConfirm = false;
    this.logout();
  }

  logout(): void {
    this.auth.logout();
  }
}
