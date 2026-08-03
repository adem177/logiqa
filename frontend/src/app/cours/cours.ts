import { Component, OnInit, OnDestroy, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { CoursService, Course } from '../cours/cours.service';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-cours',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './cours.html',
  styleUrls: ['./cours.css']
})
export class CoursesComponent implements OnInit, OnDestroy {
  // ============================================
  // SIGNALS (Reactive State)
  // ============================================
  private destroy$ = new Subject<void>();

  // Recherche et filtres
  searchTerm = signal<string>('');
  selectedCategory = signal<string>('Tous');
  isSearchFocused = false;

  // Données
  courses = signal<Course[]>([]);
  isLoading = signal<boolean>(false);
  error = signal<string | null>(null);

  // Pagination
  readonly coursesPerPage = 6;
  currentPage = signal<number>(1);

  // Options de tri
  sortOptions = [
    { label: 'Les plus populaires', value: 'popular' },
    { label: 'Les mieux notés', value: 'rating' },
    { label: 'Prix croissant', value: 'price-asc' },
    { label: 'Prix décroissant', value: 'price-desc' }
  ];
  selectedSort = signal<string>('popular');

  // Computed: Catégories uniques
  categories = computed(() => {
    const all = this.courses().map(c => c.category);
    return ['Tous', ...new Set(all)];
  });

  // Computed: Cours filtrés et triés
  filteredCourses = computed(() => {
    const courses = this.courses();
    const search = this.searchTerm().toLowerCase().trim();
    const category = this.selectedCategory();
    const sort = this.selectedSort();

    // Filtrer
    let filtered = courses.filter(course => {
      const matchSearch = course.title.toLowerCase().includes(search) ||
                          course.description.toLowerCase().includes(search);
      const matchCategory = category === 'Tous' || course.category === category;
      return matchSearch && matchCategory;
    });

    // Trier
    switch (sort) {
      case 'popular':
        filtered.sort((a, b) => b.enrolledCount - a.enrolledCount);
        break;
      case 'rating':
        filtered.sort((a, b) => b.rating - a.rating);
        break;
      case 'price-asc':
        filtered.sort((a, b) => a.price - b.price);
        break;
      case 'price-desc':
        filtered.sort((a, b) => b.price - a.price);
        break;
      default:
        break;
    }

    return filtered;
  });

  // Computed: Nombre total de pages
  totalPages = computed(() => {
    return Math.max(1, Math.ceil(this.filteredCourses().length / this.coursesPerPage));
  });

  // Computed: Cours affichés sur la page courante (max 6)
  paginatedCourses = computed(() => {
    const page = this.currentPage();
    const start = (page - 1) * this.coursesPerPage;
    return this.filteredCourses().slice(start, start + this.coursesPerPage);
  });

  // Computed: Numéros de page à afficher (ex: [1,2,3,4,5])
  pageNumbers = computed(() => {
    const total = this.totalPages();
    return Array.from({ length: total }, (_, i) => i + 1);
  });

  // Computed: Statistiques
  stats = computed(() => ({
    total: this.courses().length,
    filtered: this.filteredCourses().length,
    categories: this.categories().length - 1 // Exclure "Tous"
  }));

  constructor(private coursService: CoursService) {}

  // ============================================
  // LIFECYCLE HOOKS
  // ============================================
  ngOnInit(): void {
    this.loadCourses();
    this.setupEffects();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ============================================
  // MÉTHODES PUBLIQUES
  // ============================================

  /**
   * Charge les cours (accessible depuis le template, ex: bouton "Réessayer")
   */
  loadCourses(): void {
    this.isLoading.set(true);
    this.error.set(null);

    try {
      const data = this.coursService.getCourses();
      this.courses.set(data);
    } catch (err) {
      this.error.set('Impossible de charger les cours. Veuillez réessayer.');
      console.error('Erreur de chargement:', err);
    } finally {
      this.isLoading.set(false);
    }
  }

  /**
   * Sélectionne une catégorie
   */
  selectCategory(category: string): void {
    this.selectedCategory.set(category);
  }

  /**
   * Change le tri
   */
  changeSort(sortValue: string): void {
    this.selectedSort.set(sortValue);
  }

  /**
   * Efface la recherche
   */
  clearSearch(): void {
    this.searchTerm.set('');
  }

  /**
   * Voir les détails d'un cours
   */
  viewCourse(courseId: number | string): void {
    // Navigation avec Router
    // this.router.navigate(['/cours', courseId]);
    console.log('Voir le cours:', courseId);
  }

  /**
   * S'abonner à un cours
   */
  enrollCourse(courseId: number | string, event: Event): void {
    event.stopPropagation(); // Empêche la propagation au parent
    console.log('S\'abonner au cours:', courseId);
    // this.enrollmentService.enroll(courseId);
  }

  /**
   * Aller à une page précise
   */
  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.currentPage.set(page);
  }

  /**
   * Page précédente
   */
  previousPage(): void {
    this.goToPage(this.currentPage() - 1);
  }

  /**
   * Page suivante
   */
  nextPage(): void {
    this.goToPage(this.currentPage() + 1);
  }

  /**
   * Gérer le chargement d'image
   */
  onImageError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.src = 'assets/images/placeholder-course.jpg';
  }

  /**
   * Retourne la classe CSS pour le prix
   */
  getPriceClass(price: number): string {
    if (price === 0) return 'price-free';
    if (price < 30) return 'price-low';
    if (price < 50) return 'price-medium';
    return 'price-high';
  }

  /**
   * Retourne la note en étoiles
   */
  getStars(rating: number): string {
    return '★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating));
  }

  // ============================================
  // MÉTHODES PRIVÉES
  // ============================================
  private setupEffects(): void {
    // Log des changements de filtre (utile pour analytics)
    effect(() => {
      const search = this.searchTerm();
      const category = this.selectedCategory();
      const sort = this.selectedSort();
      const count = this.filteredCourses().length;

      console.log(`[Courses] Filtres: search="${search}", category="${category}", sort="${sort}", results=${count}`);

      // Ici vous pourriez envoyer des événements à Google Analytics
      // this.analytics.trackFilter(search, category, sort);
    });

    // Revenir à la page 1 dès que la recherche, la catégorie ou le tri change
    effect(() => {
      this.searchTerm();
      this.selectedCategory();
      this.selectedSort();
      this.currentPage.set(1);
    });
  }
}