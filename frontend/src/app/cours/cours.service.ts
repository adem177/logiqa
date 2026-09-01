// src/app/services/course.service.ts
import { Injectable, signal, computed } from '@angular/core';

export interface CourseChapter {
  title: string;
  videos: string[]; // Noms de fichiers ou URLs
  pdfs: string[];
}

export interface CourseSection {
  title: string;
  chapters: CourseChapter[];
}

export interface Course {
  id: number;
  slug: string;           // ex: 'systemes-logiques', 'base-de-donnees'
  title: string;
  description: string;
  category: string;       // ex: 'Informatique', 'Mathématiques'
  thumbnail: string;      // URL de l'image
  teacherId: number;
  createdAt: string;
  sections: CourseSection[];
}

const STORAGE_KEY = 'logiqa_courses';

@Injectable({ providedIn: 'root' })
export class CourseService {
  private coursesSignal = signal<Course[]>(this.loadFromStorage());

  // Lecture publique (readonly)
  courses = this.coursesSignal.asReadonly();

  // Liste des catégories uniques
  categories = computed(() => {
    const set = new Set(this.coursesSignal().map(c => c.category));
    return Array.from(set);
  });

  private loadFromStorage(): Course[] {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  private saveToStorage(courses: Course[]): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(courses));
  }

  // --- MÉTHODES DE RECHERCHE ---

  getCourseBySlug(slug: string): Course | undefined {
    return this.coursesSignal().find(c => c.slug === slug);
  }

  getCoursesByTeacher(teacherId: number): Course[] {
    return this.coursesSignal().filter(c => c.teacherId === teacherId);
  }

  // --- CRÉATION DE COURS COMPLET ---

  addCourse(course: Omit<Course, 'id' | 'createdAt'>): Course {
    const newCourse: Course = {
      ...course,
      id: Date.now(),
      createdAt: new Date().toISOString(),
    };

    const updated = [...this.coursesSignal(), newCourse];
    this.coursesSignal.set(updated);
    this.saveToStorage(updated);
    return newCourse;
  }

  // --- PUBLICATION / AJOUT DE RESSOURCES DANS UN CHAPITRE ---

  addContentToCourse(payload: {
    subjectSlug: string;
    chapterTitle: string;
    videos: string[];
    pdfs: string[];
  }): void {
    const currentCourses = [...this.coursesSignal()];
    const courseIndex = currentCourses.findIndex(c => c.slug === payload.subjectSlug);

    if (courseIndex === -1) {
      console.warn(`Le cours avec le slug "${payload.subjectSlug}" n'a pas été trouvé.`);
      return;
    }

    const course = { ...currentCourses[courseIndex] };
    const sections = [...course.sections];

    // Recherche de la section principale (ou création d'une section par défaut)
    let mainSectionIndex = sections.findIndex(s => s.title === 'Contenu principal');
    if (mainSectionIndex === -1) {
      sections.push({ title: 'Contenu principal', chapters: [] });
      mainSectionIndex = sections.length - 1;
    }

    const targetSection = { ...sections[mainSectionIndex] };
    const chapters = [...targetSection.chapters];

    // Recherche si le chapitre existe déjà dans cette matière
    const chapterIndex = chapters.findIndex(ch => ch.title === payload.chapterTitle);

    if (chapterIndex !== -1) {
      // Chapitre existant : ajout des nouveaux fichiers aux tableaux
      const existingChapter = chapters[chapterIndex];
      chapters[chapterIndex] = {
        ...existingChapter,
        videos: [...existingChapter.videos, ...payload.videos],
        pdfs: [...existingChapter.pdfs, ...payload.pdfs]
      };
    } else {
      // Chapitre inexistant : création du nouveau chapitre avec ses fichiers
      chapters.push({
        title: payload.chapterTitle,
        videos: payload.videos,
        pdfs: payload.pdfs
      });
    }

    // Reconstruction de la structure et mise à jour de l'état
    targetSection.chapters = chapters;
    sections[mainSectionIndex] = targetSection;
    course.sections = sections;
    currentCourses[courseIndex] = course;

    this.coursesSignal.set(currentCourses);
    this.saveToStorage(currentCourses);
  }

  // --- SUPPRESSION ---

  deleteCourse(id: number): void {
    const updated = this.coursesSignal().filter(c => c.id !== id);
    this.coursesSignal.set(updated);
    this.saveToStorage(updated);
  }
}