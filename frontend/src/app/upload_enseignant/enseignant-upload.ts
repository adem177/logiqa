import { Component, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { COURSES_DETAILS } from '../data/course-data'; // ajuste le chemin selon ton arborescence

@Component({
  selector: 'app-enseignant-upload',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './enseignant-upload.html',
  styleUrls: ['./enseignant-upload.css']
})
export class EnseignantUploadComponent {
  private router = inject(Router);

  // Informations générales du cours
  courseTitle = signal<string>('');
  courseDescription = signal<string>('');
  courseSubject = signal<string>('');

  // Fichiers du cours
  videos = signal<File[]>([]);
  pdfs = signal<File[]>([]);

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

  isSubmitting = signal<boolean>(false);

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

    if (type === 'video') {
      this.videos.set([...this.videos(), ...filesArray]);
    } else {
      this.pdfs.set([...this.pdfs(), ...filesArray]);
    }
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

    this.isSubmitting.set(true);

    const formData = new FormData();
    formData.append('subject', this.courseSubject());
    formData.append('title', this.courseTitle());
    formData.append('description', this.courseDescription());

    this.videos().forEach(video => {
      formData.append('videos', video);
    });

    this.pdfs().forEach(pdf => {
      formData.append('pdfs', pdf);
    });

    console.log('Matière :', this.courseSubject());
    console.log('Titre :', this.courseTitle());
    console.log('Description :', this.courseDescription());
    console.log('Vidéos :', this.videos());
    console.log('PDFs :', this.pdfs());

    setTimeout(() => {
      this.isSubmitting.set(false);
      alert('Le cours a été publié avec succès !');
      this.router.navigate(['/cours']);
    }, 1500);
  }
}