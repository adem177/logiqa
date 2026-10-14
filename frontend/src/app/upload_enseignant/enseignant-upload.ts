import { Component, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { concatMap, last, from, tap } from 'rxjs';
import { COURSES_DETAILS } from '../data/course-data'; // ajuste le chemin selon ton arborescence
import { Auth } from '../core/auth';

type FileType = 'video' | 'pdf';

interface UploadTask {
  file: File;
  type: FileType;
}

@Component({
  selector: 'app-enseignant-upload',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './enseignant-upload.html'
})
export class EnseignantUploadComponent {
  private router = inject(Router);
  private http = inject(HttpClient);
  private auth = inject(Auth);

  private readonly API_URL = 'http://localhost:3000';

  // Limites alignées avec le backend (app.py)
  private static readonly VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'avi', 'mkv'];
  private static readonly PDF_EXTENSIONS = ['pdf'];
  private static readonly MAX_VIDEO_SIZE = 500 * 1024 * 1024; // 500 Mo
  private static readonly MAX_PDF_SIZE = 20 * 1024 * 1024;    // 20 Mo

  // Informations générales du cours
  courseTitle = signal<string>('');
  courseDescription = signal<string>('');
  courseSubject = signal<string>('');

  // Fichiers du cours
  videos = signal<File[]>([]);
  pdfs = signal<File[]>([]);

  // Suivi de l'envoi
  isSubmitting = signal<boolean>(false);
  uploadedCount = signal<number>(0);
  totalFiles = signal<number>(0);

  // Liste des matières disponibles (alignée avec les slugs de course-data.ts)
  subjects: { value: string; label: string }[] = [
    { value: 'langage-c', label: 'Langage C' },
    { value: 'algebre', label: 'Algèbre' },
    { value: 'analyse', label: 'Analyse' },
    { value: 'systeme-exploitation', label: 'Système d\'exploitation' },
    { value: 'base-de-donnees', label: 'Base de données' },
    { value: 'algorithmes', label: 'Algorithmes' },
    { value: 'systemes-logiques', label: 'Systèmes logiques et architecture' },
    { value: 'reseaux', label: 'Réseaux' }
  ];

  // Titres de chapitres disponibles selon la matière sélectionnée
  availableTitles = computed<string[]>(() => {
    const subjectSlug = this.courseSubject();
    if (!subjectSlug) return [];
    const course = COURSES_DETAILS.find(c => c.slug === subjectSlug);
    return course ? course.chapters.map(ch => ch.title) : [];
  });

  // --- GESTION DE LA MATIÈRE ---

  onSubjectChange(): void {
    // Réinitialiser le titre quand la matière change
    this.courseTitle.set('');
  }

  // --- GESTION DES FICHIERS ---

  onFileSelected(event: Event, type: 'video' | 'pdf'): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const filesArray = Array.from(input.files);
    const invalid = filesArray.filter(file => this.invalidReason(file, type) !== null);

    if (invalid.length > 0) {
      alert(
        'Fichier(s) refusé(s) :\n' +
        invalid.map(f => `• ${f.name} — ${this.invalidReason(f, type)}`).join('\n')
      );
    }

    const valid = filesArray.filter(file => this.invalidReason(file, type) === null);
    if (valid.length === 0) {
      input.value = '';
      return;
    }

    if (type === 'video') {
      this.videos.set([...this.videos(), ...valid]);
    } else {
      this.pdfs.set([...this.pdfs(), ...valid]);
    }

    // Permet de re-sélectionner le même fichier plus tard
    input.value = '';
  }

  removeFile(type: 'video' | 'pdf', index: number): void {
    if (type === 'video') {
      const updated = this.videos().filter((_, i) => i !== index);
      this.videos.set(updated);
    } else {
      const updated = this.pdfs().filter((_, i) => i !== index);
      this.pdfs.set(updated);
    }
  }

  /** Validation côté client (mêmes règles que le backend). */
  private invalidReason(file: File, type: FileType): string | null {
    const extension = (file.name.split('.').pop() ?? '').toLowerCase();
    const allowed = type === 'video'
      ? EnseignantUploadComponent.VIDEO_EXTENSIONS
      : EnseignantUploadComponent.PDF_EXTENSIONS;

    if (!allowed.includes(extension)) {
      return type === 'video'
        ? 'format vidéo non autorisé (MP4, WEBM, MOV, AVI, MKV)'
        : 'le fichier doit être un PDF';
    }

    const maxSize = type === 'video'
      ? EnseignantUploadComponent.MAX_VIDEO_SIZE
      : EnseignantUploadComponent.MAX_PDF_SIZE;

    if (file.size > maxSize) {
      return type === 'video' ? 'la vidéo dépasse 500 Mo' : 'le PDF dépasse 20 Mo';
    }

    return null;
  }

  // --- SOUMISSION DU FORMULAIRE ---

  submitCourse(): void {
    if (!this.courseSubject()) {
      alert('Veuillez sélectionner une matière.');
      return;
    }

    if (!this.courseTitle().trim()) {
      alert('Veuillez sélectionner un chapitre pour le cours.');
      return;
    }

    const chapitreId = this.resolveChapterId();
    if (chapitreId === null) {
      alert('Chapitre introuvable. Rechargez la page et réessayez.');
      return;
    }

    const tasks: UploadTask[] = [
      ...this.videos().map(file => ({ file, type: 'video' as FileType })),
      ...this.pdfs().map(file => ({ file, type: 'pdf' as FileType }))
    ];

    if (tasks.length === 0) {
      alert('Ajoutez au moins une vidéo ou un document PDF.');
      return;
    }

    this.isSubmitting.set(true);
    this.uploadedCount.set(0);
    this.totalFiles.set(tasks.length);

    // Envoi séquentiel : plus sûr pour les grosses vidéos et progression fiable
    from(tasks)
      .pipe(
        concatMap(task =>
          this.uploadFile(chapitreId, task.file, task.type).pipe(
            tap(() => this.uploadedCount.update(count => count + 1))
          )
        ),
        last()
      )
      .subscribe({
        next: () => {
          this.isSubmitting.set(false);
          alert(
            `Le cours a été publié avec succès !\n` +
            `${tasks.length} fichier(s) envoyé(s) dans « ${this.courseTitle()} ».`
          );
          this.router.navigate(['/cours']);
        },
        error: (err) => {
          this.isSubmitting.set(false);
          const sent = this.uploadedCount();
          const prefix = sent > 0
            ? `${sent} fichier(s) déjà envoyé(s).\n`
            : '';
          alert(prefix + this.errorMessage(err));
        }
      });
  }

  /** Retrouve l'id réel du chapitre dans la base (miroir course-data.ts). */
  private resolveChapterId(): number | null {
    const course = COURSES_DETAILS.find(c => c.slug === this.courseSubject());
    const chapter = course?.chapters.find(ch => ch.title === this.courseTitle());
    return chapter ? chapter.id : null;
  }

  /** POST multipart vers /api/chapitres/:id/upload */
  private uploadFile(chapitreId: number, file: File, type: FileType) {
    const formData = new FormData();
    formData.append('fichier', file, file.name);
    formData.append('type', type);

    return this.http.post<{ success: boolean; id: number; url: string }>(
      `${this.API_URL}/api/chapitres/${chapitreId}/upload`,
      formData
    );
  }

  /** Message lisible à partir de la réponse d'erreur HTTP. */
  private errorMessage(err: any): string {
    const backendMessage = err?.error?.error;
    if (backendMessage) return backendMessage;

    switch (err?.status) {
      case 0:
        return 'Impossible de joindre le serveur. Vérifiez que le backend est bien démarré.';
      case 401:
        return 'Votre session a expiré. Veuillez vous reconnecter.';
      case 403:
        return 'Vous n\'êtes pas autorisé à publier des cours.';
      case 413:
        return 'Le fichier est trop volumineux pour le serveur.';
      default:
        return 'L\'envoi a échoué. Vérifiez vos fichiers et réessayez.';
    }
  }

  /** Retour au tableau de bord correspondant au rôle (admin ou enseignant). */
  goBack(): void {
    if (this.auth.getRole() === 'admin') {
      this.router.navigate(['/dashboard-admin']);
    } else {
      this.router.navigate(['/dashboard-enseignant']);
    }
  }
}
