import { Component, signal, computed, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';

interface Course {
  id: number;
  title: string;
  category: string;
  description: string;
  lessons: number;
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
  // 8 COURS : Langage C, Algèbre, Analyse, 
  // Systèmes logiques et architecture, Algorithmes, 
  // Base de données, Réseaux, Système d'exploitation
  // ═══════════════════════════════════════════
  allCourses: Course[] = [
    {
      id: 1,
      title: 'Langage C',
      category: 'Programmation',
      description: 'Apprenez les fondamentaux de la programmation en C. Syntaxe, pointeurs, structures et gestion de la mémoire.',
      lessons: 28,
      tags: ['Bases', 'Pointeurs', 'Mémoire'],
      image: 'c_language.png'
    },
    {
      id: 2,
      title: 'Algèbre',
      category: 'Mathématiques',
      description: 'De l\'arithmétique à l\'algèbre généralisée. Équations, polynômes et fonctions.',
      lessons: 32,
      tags: ['Équations', 'Polynômes', 'Fonctions'],
      image: 'algebra.jpg'
    },
    {
      id: 3,
      title: 'Analyse',
      category: 'Mathématiques',
      description: 'Suites numériques, limites, dérivation et intégration. Tout pour réussir vos examens.',
      lessons: 30,
      tags: ['Suites', 'Limites', 'Intégrales'],
      image: 'analyse.jpg'
    },
    {
      id: 4,
      title: 'Systèmes logiques et architecture',
      category: 'Informatique',
      description: 'Comprenez le fonctionnement interne des ordinateurs. Algèbre de Boole, circuits combinatoires/séquentiels et architecture matérielle.',
      lessons: 24,
      tags: ['Boole', 'Circuits', 'Architecture'],
      image: 'logique_archi.png'
    },
    {
      id: 5,
      title: 'Algorithmes',
      category: 'Informatique',
      description: 'Apprenez à concevoir et analyser des algorithmes efficaces. Complexité, tri, recherche et structures de données.',
      lessons: 26,
      tags: ['Complexité', 'Tri', 'Structures de données'],
      image: 'algo.jpg'
    },
    {
      id: 6,
      title: 'Base de données',
      category: 'Informatique',
      description: 'Concevez et gérez des bases de données relationnelles. Modélisation, SQL et normalisation.',
      lessons: 24,
      tags: ['SQL', 'Modélisation', 'Normalisation'],
      image: 'bdd.jpg'
    },
    {
      id: 7,
      title: 'Réseaux',
      category: 'Informatique',
      description: 'Comprenez le fonctionnement des réseaux informatiques. Modèle OSI, TCP/IP et protocoles courants.',
      lessons: 22,
      tags: ['OSI', 'TCP/IP', 'Protocoles'],
      image: 'reseaux.jpg'
    },
    {
      id: 8,
      title: 'Système d\'exploitation',
      category: 'Informatique',
      description: 'Découvrez les concepts fondamentaux des systèmes d\'exploitation. Processus, mémoire et gestion des fichiers.',
      lessons: 25,
      tags: ['Processus', 'Mémoire', 'Fichiers'],
      image: 'os.jpg'
    }
  ];

  categories = signal<string[]>([
    'Tous',
    'Programmation',
    'Mathématiques',
    'Informatique'
  ]);

  sortOptions = [
    { value: 'popular', label: 'Plus consultés' },
    { value: 'recent', label: 'Plus récents' },
    { value: 'lessons', label: 'Par nombre de leçons' }
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
      case 'lessons':
        result = [...result].sort((a, b) => b.lessons - a.lessons);
        break;
      case 'recent':
        result = [...result].sort((a, b) => b.id - a.id);
        break;
      default:
        result = [...result].sort((a, b) => b.id - a.id);
        break;
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

  onImageError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.src = 'assets/placeholder-course.jpg';
  }
}