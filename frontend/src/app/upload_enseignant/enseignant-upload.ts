import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { SectionUpload, ChapterUpload } from '../data/course-upload.model';

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
  
  // Structure dynamique du cours
  sections = signal<SectionUpload[]>([
    {
      id: Date.now(),
      title: 'Section 1 : Introduction',
      chapters: [
        { id: Date.now() + 1, title: 'Chapitre 1 : Présentation', videos: [], pdfs: [] }
      ]
    }
  ]);

  isSubmitting = signal<boolean>(false);

  // --- GESTION DES SECTIONS ET CHAPITRES ---

  addSection(): void {
    const newSection: SectionUpload = {
      id: Date.now(),
      title: `Section ${this.sections().length + 1}`,
      chapters: [
        { id: Date.now() + 1, title: 'Chapitre 1', videos: [], pdfs: [] }
      ]
    };
    this.sections.set([...this.sections(), newSection]);
  }

  removeSection(sectionId: number): void {
    this.sections.set(this.sections().filter(s => s.id !== sectionId));
  }

  addChapter(sectionId: number): void {
    const updated = this.sections().map(section => {
      if (section.id === sectionId) {
        const newChapter: ChapterUpload = {
          id: Date.now(),
          title: `Chapitre ${section.chapters.length + 1}`,
          videos: [],
          pdfs: []
        };
        return { ...section, chapters: [...section.chapters, newChapter] };
      }
      return section;
    });
    this.sections.set(updated);
  }

  removeChapter(sectionId: number, chapterId: number): void {
    const updated = this.sections().map(section => {
      if (section.id === sectionId) {
        return {
          ...section,
          chapters: section.chapters.filter(c => c.id !== chapterId)
        };
      }
      return section;
    });
    this.sections.set(updated);
  }

  // --- GESTION DES FICHIERS ---

  onFileSelected(event: Event, chapter: ChapterUpload, type: 'video' | 'pdf'): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const filesArray = Array.from(input.files);
    if (type === 'video') {
      chapter.videos.push(...filesArray);
    } else {
      chapter.pdfs.push(...filesArray);
    }
  }

  removeFile(chapter: ChapterUpload, type: 'video' | 'pdf', index: number): void {
    if (type === 'video') {
      chapter.videos.splice(index, 1);
    } else {
      chapter.pdfs.splice(index, 1);
    }
  }

  // --- SOUMISSION DU FORMULAIRE ---

  submitCourse(): void {
    if (!this.courseTitle().trim()) {
      alert('Veuillez saisir un titre pour le cours.');
      return;
    }

    this.isSubmitting.set(true);

    const formData = new FormData();
    formData.append('title', this.courseTitle());
    formData.append('description', this.courseDescription());

    // Construction du payload / transmission des fichiers au backend
    console.log('Titre :', this.courseTitle());
    console.log('Sections & Fichiers :', this.sections());

    // Simulation de requête API
    setTimeout(() => {
      this.isSubmitting.set(false);
      alert('Le cours a été publié avec succès !');
      this.router.navigate(['/cours']);
    }, 1500);
  }
}