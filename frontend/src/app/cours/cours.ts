import { Component, signal, computed, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';

interface Course {
  id: number;
  title: string;
  category: string;
  description: string;
  instructor: string;
  lessons: number;
  duration: number;
  rating: number;
  reviewsCount: number;
  price: number;
  isPremium: boolean;
  level: string;
  enrolledCount: number;
  tags: string[];
  image: string;
}

@Component({
  selector: 'app-courses',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './cours.html',
  styleUrls: ['./cours.css']
})
export class CoursesComponent implements OnInit {
  private router = inject(Router);

  courses = signal<Course[]>([]);
  searchTerm = signal<string>('');
  selectedCategory = signal<string>('Tous');
  selectedSort = signal<string>('popular');
  isSearchFocused = false;
  isLoading = signal<boolean>(false);
  error = signal<string | null>(null);
  currentPage = signal<number>(1);
  itemsPerPage = 6;

  // ═══════════════════════════════════════════
  // 7 COURS : Python, Algèbre, Analyse, HTML/CSS, Java, React, Angular
  // ═══════════════════════════════════════════
  allCourses: Course[] = [
    {
      id: 1,
      title: 'Python',
      category: 'Programmation',
      description: 'Maîtrisez Python de zéro à héros. Variables, boucles, fonctions, POO et projets concrets.',
      instructor: 'Prof. Karim Ben Salah',
      lessons: 28,
      duration: 14,
      rating: 4.7,
      reviewsCount: 245,
      price: 45,
      isPremium: true,
      level: 'Débutant',
      enrolledCount: 890,
      tags: ['Bases', 'POO', 'Fichiers'],
      image: 'python.png'
    },
    {
      id: 2,
      title: 'Algèbre',
      category: 'Mathématiques',
      description: 'De l\'arithmétique à l\'algèbre généralisée. Équations, polynômes et fonctions.',
      instructor: 'Prof. Amine Benali',
      lessons: 32,
      duration: 16,
      rating: 4.8,
      reviewsCount: 198,
      price: 55,
      isPremium: true,
      level: 'Débutant',
      enrolledCount: 650,
      tags: ['Équations', 'Polynômes', 'Fonctions'],
      image: 'algebra.jpg'
    },
    {
      id: 3,
      title: 'Analyse',
      category: 'Mathématiques',
      description: 'Suites numériques, limites, dérivation et intégration. Tout pour réussir vos examens.',
      instructor: 'Prof. Sami Trabelsi',
      lessons: 30,
      duration: 18,
      rating: 4.6,
      reviewsCount: 156,
      price: 60,
      isPremium: true,
      level: 'Intermédiaire',
      enrolledCount: 420,
      tags: ['Suites', 'Limites', 'Intégrales'],
      image: 'analyse.jpg'
    },
    {
      id: 4,
      title: 'HTML & CSS',
      category: 'Développement Web',
      description: 'Créez des sites web modernes et responsives. Flexbox, Grid, animations et bonnes pratiques.',
      instructor: 'Prof. Nadia Khemiri',
      lessons: 24,
      duration: 12,
      rating: 4.9,
      reviewsCount: 312,
      price: 35,
      isPremium: false,
      level: 'Débutant',
      enrolledCount: 1200,
      tags: ['HTML5', 'CSS3', 'Responsive'],
      image: 'html_css.png'
    },
    {
      id: 5,
      title: 'Java',
      category: 'Programmation',
      description: 'Programmation orientée objet avec Java. Classes, héritage, collections et applications.',
      instructor: 'Prof. Youssef Gharbi',
      lessons: 35,
      duration: 20,
      rating: 4.5,
      reviewsCount: 178,
      price: 50,
      isPremium: true,
      level: 'Débutant',
      enrolledCount: 560,
      tags: ['POO', 'Collections', 'JVM'],
      image: 'java.png'
    },
    {
      id: 6,
      title: 'React',
      category: 'Développement Web',
      description: 'Construisez des interfaces dynamiques avec React. Hooks, Context API, Redux et Next.js.',
      instructor: 'Prof. Rami Ben Ammar',
      lessons: 26,
      duration: 14,
      rating: 4.8,
      reviewsCount: 289,
      price: 55,
      isPremium: true,
      level: 'Intermédiaire',
      enrolledCount: 780,
      tags: ['Hooks', 'Redux', 'Next.js'],
      image: 'react.png'
    },
    {
      id: 7,
      title: 'Angular',
      category: 'Développement Web',
      description: 'Framework Angular complet. Components, services, routing, RxJS et signals.',
      instructor: 'Prof. Lina Ben Youssef',
      lessons: 28,
      duration: 16,
      rating: 4.7,
      reviewsCount: 210,
      price: 55,
      isPremium: true,
      level: 'Intermédiaire',
      enrolledCount: 640,
      tags: ['Components', 'RxJS', 'Signals'],
      image: 'ang.png'
    }
  ];

  categories = signal<string[]>([
    'Tous',
    'Programmation',
    'Mathématiques',
    'Développement Web'
  ]);

  sortOptions = [
    { value: 'popular', label: 'Plus populaires' },
    { value: 'recent', label: 'Plus récents' },
    { value: 'price-asc', label: 'Prix croissant' },
    { value: 'price-desc', label: 'Prix décroissant' },
    { value: 'rating', label: 'Mieux notés' }
  ];

  ngOnInit(): void {
    this.loadCourses();
  }

  loadCourses(): void {
    this.isLoading.set(true);
    this.error.set(null);
    setTimeout(() => {
      this.courses.set(this.allCourses);
      this.isLoading.set(false);
    }, 500);
  }

  filteredCourses = computed(() => {
    let result = this.courses();
    if (this.selectedCategory() !== 'Tous') {
      result = result.filter(c => c.category === this.selectedCategory());
    }
    const term = this.searchTerm().toLowerCase().trim();
    if (term) {
      result = result.filter(c =>
        c.title.toLowerCase().includes(term) ||
        c.description.toLowerCase().includes(term) ||
        c.category.toLowerCase().includes(term) ||
        c.tags.some(t => t.toLowerCase().includes(term))
      );
    }
    switch (this.selectedSort()) {
      case 'price-asc': result = [...result].sort((a, b) => a.price - b.price); break;
      case 'price-desc': result = [...result].sort((a, b) => b.price - a.price); break;
      case 'rating': result = [...result].sort((a, b) => b.rating - a.rating); break;
      case 'recent': result = [...result].sort((a, b) => b.id - a.id); break;
      default: result = [...result].sort((a, b) => b.enrolledCount - a.enrolledCount); break;
    }
    return result;
  });

  paginatedCourses = computed(() => {
    const start = (this.currentPage() - 1) * this.itemsPerPage;
    return this.filteredCourses().slice(start, start + this.itemsPerPage);
  });

  totalPages = computed(() => Math.ceil(this.filteredCourses().length / this.itemsPerPage));

  pageNumbers = computed(() => {
    const pages: number[] = [];
    for (let i = 1; i <= this.totalPages(); i++) pages.push(i);
    return pages;
  });

  stats = computed(() => ({
    categories: this.categories().length - 1
  }));

  selectCategory(cat: string): void {
    this.selectedCategory.set(cat);
    this.currentPage.set(1);
  }

  changeSort(value: string): void {
    this.selectedSort.set(value);
  }

  clearSearch(): void {
    this.searchTerm.set('');
  }

  previousPage(): void {
    if (this.currentPage() > 1) this.currentPage.update(p => p - 1);
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages()) this.currentPage.update(p => p + 1);
  }

  goToPage(page: number): void {
    this.currentPage.set(page);
  }

  viewCourse(courseId: number): void {
    this.router.navigate(['/cours', courseId]);
  }

  getStars(rating: number): string {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5 ? 1 : 0;
    return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(5 - full - half);
  }

  getPriceClass(price: number): string {
    return price === 0 ? 'free' : '';
  }

  onImageError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.src = 'assets/placeholder-course.jpg';
  }
}