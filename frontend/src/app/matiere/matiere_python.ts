import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, ActivatedRoute } from '@angular/router';
import { COURSES_DETAILS, CourseDetail, Section } from '../data/course-data';

type TabKey = 'cours' | 'examen';
type ResourceType = 'video' | 'pdf';

@Component({
  selector: 'app-cours-content',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './matiere_python.html',
  styleUrls: ['./matiere_python.css']
})
export class CoursContentComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  course = signal<CourseDetail | null>(null);
  activeTab = signal<TabKey>('cours');
  expandedChapters = signal<Set<number>>(new Set());

  // Signal pour gérer l'onglet actif (Vidéo ou PDF) par chapitre
  resourceViews = signal<Map<number, ResourceType>>(new Map());

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    const found = COURSES_DETAILS.find(c => c.id === id);

    if (found) {
      this.course.set(found);
    } else {
      this.router.navigate(['/cours']);
    }
  }

  courseTitle = computed(() => this.course()?.title ?? 'Cours');
  sections = computed(() => this.course()?.sections ?? []);

  totalVideos = computed(() =>
    this.sections().reduce(
      (total, section) =>
        total + section.chapters.reduce((s, c) => s + c.videosCount, 0),
      0
    )
  );

  globalProgress = computed(() => {
    const allChapters = this.sections().flatMap(s => s.chapters);
    if (allChapters.length === 0) return 0;
    const sum = allChapters.reduce((acc, c) => acc + c.progress, 0);
    return Math.round(sum / allChapters.length);
  });

  setTab(tab: TabKey): void {
    this.activeTab.set(tab);
  }

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

  chaptersCount(section: Section): number {
    return section.chapters.length;
  }

  // --- NOUVELLES MÉTHODES REQUISES PAR LE TEMPLATE ---

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

  goBack(): void {
    this.router.navigate(['/cours']);
  }
}