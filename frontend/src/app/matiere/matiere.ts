import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { HttpClient, HttpEventType, HttpErrorResponse } from '@angular/common/http';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { COURSES_DETAILS, CourseDetail, Chapter } from '../data/course-data';
import { CourseService, Course as StoredCourse } from '../services/course.service';
import { QuizService, Quiz } from '../services/quiz.service';
import { Auth } from '../core/auth';
import { environment } from '../../environments/environements';

type TabKey = 'cours' | 'examen';
type ResourceType = 'video' | 'pdf';

interface UploadState {
  fileName: string;
  progress: number;
  error: string | null;
}

interface ResourceItem {
  name: string;
  url: string;
}

@Component({
  selector: 'app-cours-content',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './matiere.html'
})
export class CoursContentComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private courseService = inject(CourseService);
  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);
  private auth = inject(Auth);

  private readonly API_URL = environment.apiUrl;
  private readonly UPLOAD_ENDPOINT = `${this.API_URL}/api/chapitres`;

  // ⚠️ Extension utilisée pour les vidéos statiques (public/videos/chapitreN_index.EXT).
  // Change ici si tes fichiers sont en .webm, .mov, etc.
  private readonly STATIC_VIDEO_EXT = 'mp4';

  // Signaux
  course = signal<CourseDetail | null>(null);
  activeTab = signal<TabKey>('cours');
  expandedChapters = signal<Set<number>>(new Set());
  chapterResources = signal<Map<number, { videos: ResourceItem[]; pdfs: ResourceItem[] }>>(new Map());
  resourceViews = signal<Map<number, ResourceType>>(new Map());
  private uploadStates = signal<Map<number, UploadState>>(new Map());

  // Signaux Examen
  examenUrl = signal<string | null>(null);
  examenUrlSafe = signal<SafeResourceUrl | null>(null);
  examenTitle = signal<string>('');
  loadingExam = signal<boolean>(false); // ← renommé (avant : loadingExamen)
  loadingCourse = signal<boolean>(true);

  // Signaux Quiz
  quizList = signal<Quiz[]>([]);
  quizError = signal<string | null>(null);
  private quizService = inject(QuizService);

  // Rôle de l'utilisateur : seuls enseignants/admins voient les boutons d'édition
  isEnseignant = false;

  /** Nom complet de l'auteur d'un quiz */
  getAuthorName(q: Quiz): string {
    const prenom = q.createur_prenom || '';
    const nom = q.createur_nom || '';
    return `${prenom} ${nom}`.trim() || 'Inconnu';
  }

  /** Rôle lisible de l'auteur (admin ou enseignant) */
  getAuthorRole(q: Quiz): string {
    switch (q.createur_role) {
      case 'admin': return 'Administrateur';
      case 'enseignant': return 'Enseignant';
      default: return 'Membre';
    }
  }

  /** Initiales de l'auteur pour l'avatar */
  getAuthorInitials(q: Quiz): string {
    const p = (q.createur_prenom || '').charAt(0);
    const n = (q.createur_nom || '').charAt(0);
    return (p + n).toUpperCase() || '?';
  }

  ngOnInit(): void {
    this.isEnseignant = this.auth.hasRole(['enseignant', 'admin']);

    const paramId = this.route.snapshot.paramMap.get('id');

    if (paramId) {
      this.loadCourseData(paramId);
    } else {
      // Route /matiere sans :id → jamais de page vide : renvoyer au catalogue.
      this.loadingCourse.set(false);
      this.router.navigate(['/cours']);
    }
  }

  private loadCourseData(idOrSlug: string): void {
    this.loadingCourse.set(true);

    // 1. Chercher dans CourseService (localStorage)
    const storedCourse = this.courseService.courses().find(
      c => c.slug === idOrSlug || c.id === Number(idOrSlug)
    );

    if (storedCourse && storedCourse.sections && storedCourse.sections.length > 0) {
      const converted = this.convertStoredCourse(storedCourse);
      if (converted.detail.chapters.length > 0) {
        this.course.set(converted.detail);
        this.chapterResources.set(converted.resources);
        this.loadingCourse.set(false);
        return;
      }
    }

    // 2. Chercher dans les données statiques (COURSES_DETAILS)
    const staticCourse = COURSES_DETAILS.find(
      c => c.slug === idOrSlug || c.id === Number(idOrSlug)
    );

    if (staticCourse && staticCourse.chapters && staticCourse.chapters.length > 0) {
      this.course.set(staticCourse);
      this.loadingCourse.set(false);
      return;
    }

    // 3. Sinon, tenter la requête auprès du serveur backend
    this.http.get<any>(`${this.API_URL}/api/cours/${idOrSlug}`).subscribe({
      next: (data) => {
        if (data && data.chapitres && data.chapitres.length > 0) {
          const chapters: Chapter[] = data.chapitres.map((ch: any) => ({
            id: ch.id,
            number: ch.numero,
            title: ch.titre,
            videosCount: 0,
            pdfsCount: 0,
            progress: 0
          }));

          const detail: CourseDetail = {
            id: data.id,
            title: data.titre,
            slug: data.slug || this.slugify(data.titre),
            chapters: chapters
          };

          this.course.set(detail);
          chapters.forEach(ch => this.loadChapterResources(ch.id));
        } else {
          this.loadFallbackLocal(idOrSlug);
        }
        this.loadingCourse.set(false);
      },
      error: () => {
        this.loadFallbackLocal(idOrSlug);
        this.loadingCourse.set(false);
      }
    });
  }

  private loadChapterResources(chapterId: number): void {
    this.http.get<any[]>(`${this.UPLOAD_ENDPOINT}/${chapterId}/resources`).subscribe({
      next: (resources) => {
        const videos: ResourceItem[] = resources
          .filter(r => r.type === 'video')
          .map(r => ({ name: r.nom_original, url: `${this.API_URL}${r.url}` }));
        const pdfs: ResourceItem[] = resources
          .filter(r => r.type === 'pdf')
          .map(r => ({ name: r.nom_original, url: `${this.API_URL}${r.url}` }));

        const currentMap = new Map(this.chapterResources());
        currentMap.set(chapterId, { videos, pdfs });
        this.chapterResources.set(currentMap);

        const currentCourse = this.course();
        if (currentCourse) {
          const updatedChapters = currentCourse.chapters.map(ch => {
            if (ch.id === chapterId) {
              return { ...ch, videosCount: videos.length, pdfsCount: pdfs.length };
            }
            return ch;
          });
          this.course.set({ ...currentCourse, chapters: updatedChapters });
        }
      }
    });
  }

  private loadFallbackLocal(idOrSlug: string | number): void {
    const paramStr = String(idOrSlug);
    const paramNum = Number(idOrSlug);

    const found = COURSES_DETAILS.find(
      c => c.id === paramNum || c.slug === paramStr
    );

    if (found) {
      this.course.set(found);
    } else {
      this.router.navigate(['/cours']);
    }
  }

  // Navigation & Onglets
  setTab(tab: TabKey): void {
    this.activeTab.set(tab);
    if (tab === 'examen' && !this.examenUrl()) {
      this.loadExamen();
    }
  }

  loadExamen(): void {
    const currentCourse = this.course();
    if (!currentCourse || currentCourse.chapters.length === 0) return;

    this.loadingExam.set(true);
    this.quizError.set(null);
    this.quizList.set([]);

    // Charger les quiz de tous les chapitres du cours
    const allQuiz: Quiz[] = [];
    let completed = 0;
    const totalChapters = currentCourse.chapters.length;

    currentCourse.chapters.forEach(chapter => {
      this.quizService.listerQuiz(chapter.id).subscribe({
        next: (quiz) => {
          allQuiz.push(...quiz);
          completed++;
          if (completed === totalChapters) {
            this.quizList.set(allQuiz);
            this.loadingExam.set(false);
          }
        },
        error: () => {
          completed++;
          if (completed === totalChapters) {
            this.quizList.set(allQuiz);
            this.loadingExam.set(false);
          }
        }
      });
    });
  }

  startQuiz(quizId: number): void {
    this.router.navigate(['/quiz', quizId]);
  }

  private convertStoredCourse(course: StoredCourse): {
    detail: CourseDetail;
    resources: Map<number, { videos: ResourceItem[]; pdfs: ResourceItem[] }>;
  } {
    const resources = new Map<number, { videos: ResourceItem[]; pdfs: ResourceItem[] }>();
    let chapterAutoId = 1;
    let chapterNumber = 1;

    const staticCourse = COURSES_DETAILS.find(
      c => c.slug === course.slug || c.id === course.id
    );

    let chapters: Chapter[] = [];

    if (course.sections && course.sections.length > 0) {
      chapters = course.sections.flatMap(s =>
        s.chapters.map((ch): Chapter => {
          const id = chapterAutoId++;

          const videos: ResourceItem[] = (ch.videos || []).map(name => ({ name, url: '' }));
          const pdfs: ResourceItem[] = (ch.pdfs || []).map(name => ({ name, url: '' }));
          resources.set(id, { videos, pdfs });

          const cleanTitle = ch.title.replace(/^Chapitre\s+\d+\s*:\s*/i, '');

          return {
            id,
            number: chapterNumber++,
            title: cleanTitle,
            videosCount: ch.videos?.length || 0,
            pdfsCount: ch.pdfs?.length || 0,
            progress: 0
          };
        })
      );
    } else if (staticCourse) {
      chapters = staticCourse.chapters;
    }

    return {
      detail: {
        id: course.id || (staticCourse ? staticCourse.id : 1),
        title: course.title || (staticCourse ? staticCourse.title : 'Cours'),
        slug: course.slug || this.slugify(course.title || ''),
        chapters
      },
      resources
    };
  }

  private slugify(text: string): string {
    return text
      .toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
  }

  // Computed
  courseTitle = computed(() => this.course()?.title ?? 'Cours');
  chapters = computed(() => this.course()?.chapters ?? []);

  totalVideos = computed(() =>
    this.chapters().reduce((total, chapter) => total + chapter.videosCount, 0)
  );

  globalProgress = computed(() => {
    const allChapters = this.chapters();
    if (allChapters.length === 0) return 0;
    const sum = allChapters.reduce((acc, c) => acc + c.progress, 0);
    return Math.round(sum / allChapters.length);
  });

  goBack(): void {
    // L'enseignant (ou l'admin) qui consulte un cours revient directement sur
    // son tableau de bord ; l'étudiant retourne au catalogue.
    if (this.isEnseignant) {
      this.router.navigate(['/dashboard-enseignant']);
    } else {
      this.router.navigate(['/cours']);
    }
  }

  // Gestion des chapitres
  toggleChapter(chapterId: number): void {
    const current = new Set(this.expandedChapters());
    if (current.has(chapterId)) {
      current.delete(chapterId);
    } else {
      current.add(chapterId);
    }
    this.expandedChapters.set(current);
  }

  isExpanded(chapterId: number): boolean {
    return this.expandedChapters().has(chapterId);
  }

  // Gestion des ressources
  getResourceView(chapterId: number): ResourceType {
    return this.resourceViews().get(chapterId) ?? 'video';
  }

  setResourceView(chapterId: number, type: ResourceType): void {
    const next = new Map(this.resourceViews());
    next.set(chapterId, type);
    this.resourceViews.set(next);
  }

  buildRange(count: number): number[] {
    return Array.from({ length: count }, (_, i) => i);
  }

  getVideoName(chapterId: number, index: number): string {
    const res = this.chapterResources().get(chapterId);
    return res?.videos[index]?.name ?? `Vidéo ${index + 1}`;
  }

  getPdfName(chapterId: number, index: number): string {
    const res = this.chapterResources().get(chapterId);
    return res?.pdfs[index]?.name ?? `Support PDF ${index + 1}`;
  }

  /**
   * Renvoie l'URL du PDF pour un chapitre donné.
   * 1. Si une ressource a été uploadée via le backend (BDD), on utilise son URL réelle.
   * 2. Sinon, on retombe sur la convention de nommage statique des fichiers
   *    placés à la main dans public/pdfs/ : chapitreN_index.pdf (index à partir de 1).
   */
  getPdfUrl(chapter: Chapter, index: number): string {
    const stored = this.chapterResources().get(chapter.id)?.pdfs[index];
    if (stored?.url) {
      return stored.url;
    }
    const slug = this.course()?.slug ?? '';
    return `/pdfs/${slug}/chapitre${chapter.number}/chapitre${chapter.number}_${index + 1}.pdf`;
  }

  getVideoUrl(chapter: Chapter, index: number): string {
    const stored = this.chapterResources().get(chapter.id)?.videos[index];
    if (stored?.url) {
      return stored.url;
    }
    const slug = this.course()?.slug ?? '';
    return `/videos/${slug}/chapitre${chapter.number}/chapitre${chapter.number}_${index + 1}.${this.STATIC_VIDEO_EXT}`;
  }

  // Upload de fichiers
  uploadingFileName(chapterId: number): string | null {
    return this.uploadStates().get(chapterId)?.fileName ?? null;
  }

  uploadProgress(chapterId: number): number | null {
    const state = this.uploadStates().get(chapterId);
    if (!state) return null;
    return state.progress < 100 ? state.progress : null;
  }

  uploadError(chapterId: number): string | null {
    return this.uploadStates().get(chapterId)?.error ?? null;
  }

  private setUploadState(chapterId: number, patch: Partial<UploadState>): void {
    const next = new Map(this.uploadStates());
    const current = next.get(chapterId) ?? { fileName: '', progress: 0, error: null };
    next.set(chapterId, { ...current, ...patch });
    this.uploadStates.set(next);
  }

  private clearUploadState(chapterId: number): void {
    const next = new Map(this.uploadStates());
    next.delete(chapterId);
    this.uploadStates.set(next);
  }

  onFileSelected(event: Event, chapterId: number, type: ResourceType): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.validateAndUpload(chapterId, type, file);
  }

  private validateAndUpload(chapterId: number, type: ResourceType, file: File): void {
    if (type === 'pdf' && file.type !== 'application/pdf') {
      this.setUploadState(chapterId, { fileName: file.name, progress: 0, error: 'Le fichier doit être un PDF.' });
      return;
    }
    if (type === 'video' && !file.type.startsWith('video/')) {
      this.setUploadState(chapterId, { fileName: file.name, progress: 0, error: 'Le fichier doit être une vidéo.' });
      return;
    }

    const maxSize = type === 'video' ? 500 * 1024 * 1024 : 20 * 1024 * 1024;
    if (file.size > maxSize) {
      const maxLabel = type === 'video' ? '500 Mo' : '20 Mo';
      this.setUploadState(chapterId, { fileName: file.name, progress: 0, error: `Le fichier dépasse la limite de ${maxLabel}.` });
      return;
    }

    this.setUploadState(chapterId, { fileName: file.name, progress: 0, error: null });
    this.uploadFile(chapterId, type, file);
  }

  private uploadFile(chapterId: number, type: ResourceType, file: File): void {
    const formData = new FormData();
    formData.append('fichier', file);
    formData.append('type', type);
    formData.append('titre', file.name);

    this.http
      .post<any>(`${this.UPLOAD_ENDPOINT}/${chapterId}/upload`, formData, {
        reportProgress: true,
        observe: 'events'
      })
      .subscribe({
        next: (event) => {
          if (event.type === HttpEventType.UploadProgress && event.total) {
            const percent = Math.round((100 * event.loaded) / event.total);
            this.setUploadState(chapterId, { progress: percent });
          }
          if (event.type === HttpEventType.Response) {
            this.setUploadState(chapterId, { progress: 100, error: null });
            const body = event.body;
            this.addResourceLocally(chapterId, type, file.name, body?.url ?? '');
            setTimeout(() => this.clearUploadState(chapterId), 1200);
          }
        },
        error: (err: HttpErrorResponse) => {
          const message = err.status === 0
            ? 'Impossible de contacter le serveur.'
            : `Échec de l'envoi (${err.status}).`;
          this.setUploadState(chapterId, { progress: 0, error: message });
        }
      });
  }

  private addResourceLocally(chapterId: number, type: ResourceType, fileName: string, url: string): void {
    const resources = new Map(this.chapterResources());
    const current = resources.get(chapterId) ?? { videos: [], pdfs: [] };
    const item: ResourceItem = { name: fileName, url: url ? `${this.API_URL}${url}` : '' };

    if (type === 'video') {
      current.videos = [...current.videos, item];
    } else {
      current.pdfs = [...current.pdfs, item];
    }
    resources.set(chapterId, current);
    this.chapterResources.set(resources);

    const courseValue = this.course();
    if (!courseValue) return;

    const updatedChapters = courseValue.chapters.map(ch => {
      if (ch.id !== chapterId) return ch;
      return {
        ...ch,
        videosCount: type === 'video' ? ch.videosCount + 1 : ch.videosCount,
        pdfsCount: type === 'pdf' ? ch.pdfsCount + 1 : ch.pdfsCount
      };
    });

    this.course.set({ ...courseValue, chapters: updatedChapters });
  }

  deleteResource(chapterId: number, type: ResourceType, index: number): void {
    const confirmed = confirm('Supprimer ce fichier ?');
    if (!confirmed) return;

    this.http.delete(`${this.UPLOAD_ENDPOINT}/${chapterId}/resources/${type}/${index}`).subscribe({
      next: () => this.removeResourceLocally(chapterId, type, index),
      error: () => alert('La suppression a échoué.')
    });
  }

  private removeResourceLocally(chapterId: number, type: ResourceType, index: number): void {
    const resources = new Map(this.chapterResources());
    const current = resources.get(chapterId) ?? { videos: [], pdfs: [] };
    if (type === 'video') {
      current.videos = current.videos.filter((_, i) => i !== index);
    } else {
      current.pdfs = current.pdfs.filter((_, i) => i !== index);
    }
    resources.set(chapterId, current);
    this.chapterResources.set(resources);

    const courseValue = this.course();
    if (!courseValue) return;

    const updatedChapters = courseValue.chapters.map(ch => {
      if (ch.id !== chapterId) return ch;
      return {
        ...ch,
        videosCount: type === 'video' ? Math.max(0, ch.videosCount - 1) : ch.videosCount,
        pdfsCount: type === 'pdf' ? Math.max(0, ch.pdfsCount - 1) : ch.pdfsCount
      };
    });

    this.course.set({ ...courseValue, chapters: updatedChapters });
  }
}