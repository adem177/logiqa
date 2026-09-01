import { Injectable, signal, computed } from '@angular/core';
import { COURSES_DETAILS } from '../data/course-data';

export interface CourseChapter {
  title: string;
  videos: string[];
  pdfs: string[];
}

export interface CourseSection {
  title: string;
  chapters: CourseChapter[];
}

export interface Course {
  id: number;
  slug: string;
  title: string;
  description: string;
  category: string;
  thumbnail: string;
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

  /**
   * Normalise un texte pour générer ou comparer un slug (insensible à la casse et aux accents)
   */
  private slugify(text: string): string {
    return text
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  }

  // --- MÉTHODES DE RECHERCHE ---

  getCourseBySlug(slug: string): Course | undefined {
    const targetSlug = this.slugify(slug);
    return this.coursesSignal().find(c => this.slugify(c.slug) === targetSlug);
  }

  getCoursesByTeacher(teacherId: number): Course[] {
    return this.coursesSignal().filter(c => c.teacherId === teacherId);
  }

  // --- CRÉATION DE COURS COMPLET ---

  addCourse(course: Omit<Course, 'id' | 'createdAt'>): Course {
    const newCourse: Course = {
      ...course,
      slug: this.slugify(course.slug || course.title),
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
    const targetSlug = this.slugify(payload.subjectSlug);

    let courseIndex = currentCourses.findIndex(c => this.slugify(c.slug) === targetSlug);

    // Si le cours n'existe pas en Storage, initialisation depuis COURSES_DETAILS
    if (courseIndex === -1) {
      const staticCourse = COURSES_DETAILS.find(c => this.slugify(c.slug) === targetSlug);

      const newCourse: Course = {
        id: staticCourse ? staticCourse.id : Date.now(),
        slug: staticCourse ? staticCourse.slug : targetSlug,
        title: staticCourse ? staticCourse.title : payload.subjectSlug,
        description: '',
        category: 'Général',
        thumbnail: '',
        teacherId: 1,
        createdAt: new Date().toISOString(),
        sections: [{
          title: 'Contenu principal',
          chapters: staticCourse ? staticCourse.chapters.map(ch => ({
            title: ch.title,
            videos: [],
            pdfs: []
          })) : []
        }]
      };

      currentCourses.push(newCourse);
      courseIndex = currentCourses.length - 1;
    }

    const course = { ...currentCourses[courseIndex] };
    const sections = [...(course.sections || [])];

    // Recherche ou création de la section principale
    let mainSectionIndex = sections.findIndex(s => s.title === 'Contenu principal');
    if (mainSectionIndex === -1) {
      sections.push({ title: 'Contenu principal', chapters: [] });
      mainSectionIndex = sections.length - 1;
    }

    const targetSection = { ...sections[mainSectionIndex] };
    const chapters = [...targetSection.chapters];

    // Nettoyage et comparaison du titre de chapitre
    const cleanPayloadTitle = payload.chapterTitle.replace(/^Chapitre\s+\d+\s*:\s*/i, '').trim();

    const chapterIndex = chapters.findIndex(ch => {
      const cleanChTitle = ch.title.replace(/^Chapitre\s+\d+\s*:\s*/i, '').trim();
      return cleanChTitle === cleanPayloadTitle || 
             cleanChTitle.includes(cleanPayloadTitle) || 
             cleanPayloadTitle.includes(cleanChTitle);
    });

    if (chapterIndex !== -1) {
      // Chapitre existant : fusion sans doublons
      const existingChapter = chapters[chapterIndex];
      chapters[chapterIndex] = {
        ...existingChapter,
        videos: Array.from(new Set([...(existingChapter.videos || []), ...payload.videos])),
        pdfs: Array.from(new Set([...(existingChapter.pdfs || []), ...payload.pdfs]))
      };
    } else {
      // Chapitre inexistant : création
      chapters.push({
        title: cleanPayloadTitle,
        videos: payload.videos,
        pdfs: payload.pdfs
      });
    }

    // Sauvegarde et mise à jour des signaux
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