import { Injectable } from '@angular/core';
import { Observable, of, delay } from 'rxjs';

// ============================================
// INTERFACES
// ============================================
export interface Course {
  id: number;
  title: string;
  description: string;
  category: string;
  subCategory?: string;
  image: string;
  rating: number;
  reviewsCount: number;
  lessons: number;
  duration: number; // en heures
  price: number;
  enrolledCount: number;
  instructor: string;
  level: 'Débutant' | 'Intermédiaire' | 'Avancé' | 'Tous niveaux';
  tags: string[];
  publishedDate: Date;
  isPremium: boolean;
}

export interface CourseFilters {
  search?: string;
  category?: string;
  level?: string;
  minPrice?: number;
  maxPrice?: number;
  sort?: 'popular' | 'rating' | 'price-asc' | 'price-desc' | 'newest';
}

@Injectable({
  providedIn: 'root'
})
export class CoursService {
  // ============================================
  // DONNÉES
  // ============================================
  private courses: Course[] = [
    {
      id: 1,
      title: 'Angular pour débutants',
      description: 'Apprenez à créer des applications web modernes et performantes avec Angular 18. Cours complet avec projets pratiques.',
      category: 'Web',
      subCategory: 'Frontend',
      image: '/ang.png',
      rating: 4.8,
      reviewsCount: 342,
      lessons: 24,
      duration: 12.5,
      price: 49,
      enrolledCount: 1250,
      instructor: 'Dr. Sarah Martin',
      level: 'Débutant',
      tags: ['Angular', 'TypeScript', 'SPA', 'RxJS'],
      publishedDate: new Date('2024-01-15'),
      isPremium: true
    },
    {
      id: 2,
      title: 'Python pour débutants',
      description: 'Découvrez les bases de la programmation Python et développez vos premières applications dans les domaines du web, de la data et de l\'IA.',
      category: 'Programmation',
      subCategory: 'Langages',
      image: '/python.png',
      rating: 4.9,
      reviewsCount: 521,
      lessons: 30,
      duration: 15.0,
      price: 39,
      enrolledCount: 2150,
      instructor: 'Prof. Jean Dupont',
      level: 'Débutant',
      tags: ['Python', 'Data Science', 'Django', 'Flask'],
      publishedDate: new Date('2024-02-01'),
      isPremium: false
    },
    {
      id: 3,
      title: 'Java programmation',
      description: 'Maîtrisez les concepts fondamentaux de la programmation Java : POO, collections, exceptions, et développez des applications d\'entreprise.',
      category: 'Programmation',
      subCategory: 'Langages',
      image: '/java.png',
      rating: 4.7,
      reviewsCount: 289,
      lessons: 28,
      duration: 14.0,
      price: 45,
      enrolledCount: 980,
      instructor: 'Dr. Marie Chen',
      level: 'Intermédiaire',
      tags: ['Java', 'POO', 'Spring', 'Hibernate'],
      publishedDate: new Date('2023-11-20'),
      isPremium: true
    },
    {
      id: 4,
      title: 'HTML & CSS - Le guide complet',
      description: 'Créez des sites web modernes et responsives avec HTML5 et CSS3. Maîtrisez le layout, les animations et les designs avancés.',
      category: 'Web',
      subCategory: 'Frontend',
      image: 'html_css.png',
      rating: 4.6,
      reviewsCount: 415,
      lessons: 20,
      duration: 10.0,
      price: 29,
      enrolledCount: 1780,
      instructor: 'Prof. Sophie Laurent',
      level: 'Débutant',
      tags: ['HTML5', 'CSS3', 'Responsive', 'Flexbox', 'Grid'],
      publishedDate: new Date('2023-12-05'),
      isPremium: false
    },
    {
      id: 5,
      title: 'React.js - Le guide avancé',
      description: 'Maîtrisez React.js pour créer des interfaces utilisateur réactives et évolutives. Hooks, Context API, et optimisation.',
      category: 'Web',
      subCategory: 'Frontend',
      image: '/react.png',
      rating: 4.9,
      reviewsCount: 267,
      lessons: 35,
      duration: 18.0,
      price: 59,
      enrolledCount: 820,
      instructor: 'Dr. Thomas Müller',
      level: 'Intermédiaire',
      tags: ['React', 'JavaScript', 'Hooks', 'Redux'],
      publishedDate: new Date('2024-03-10'),
      isPremium: true
    },
    {
    
  id: 6,
  title: 'Algèbre',
  description: "Contrairement à l'arithmétique qui travaille avec des nombres précis (2 + 3 = 5) l'algèbre généralise en utilisant des variables. On peut ainsi écrire des règles valables pour tous les cas : par exemple, a + b = b + a est vrai quels que soient les nombres choisis.",
  category: 'Mathématiques',
  subCategory: 'Algèbre générale',
  image: '/algebra.jpg',
  rating: 4.8,
  reviewsCount: 198,
  lessons: 32,
  duration: 16.0,
  price: 55,
  enrolledCount: 650,
  instructor: 'Prof. Amine Benali',
  level: 'Débutant',
  tags: ['Équations', 'Polynômes', 'Fonctions', 'Factorisation'],
  publishedDate: new Date('2024-02-15'),
  isPremium: true
    },
  {
  id: 7,
  title: 'Analyse',
  description: "L'analyse mathématique étudie les notions de limite, de continuité, de dérivée et d'intégrale. Elle permet de comprendre comment les fonctions varient et de modéliser des phénomènes continus, comme la vitesse ou l'accumulation d'une quantité au fil du temps.",
  category: 'Mathématiques',
  subCategory: 'Calcul différentiel et intégral',
  image: '/analyse.jpg',
  rating: 4.7,
  reviewsCount: 156,
  lessons: 28,
  duration: 14.5,
  price: 60,
  enrolledCount: 520,
  instructor: 'Prof. Amine Benali',
  level: 'Intermédiaire',
  tags: ['Limites', 'Dérivées', 'Intégrales', 'Fonctions'],
  publishedDate: new Date('2024-03-10'),
  isPremium: true
}
  ];

  // ============================================
  // MÉTHODES PUBLIQUES
  // ============================================

  /**
   * Récupère tous les cours
   */
  getCourses(): Course[] {
    return [...this.courses]; // Copie pour éviter la mutation
  }

  /**
   * Récupère les cours avec filtres (simulation API)
   */
  getCoursesWithFilters(filters: CourseFilters = {}): Observable<Course[]> {
    let filtered = [...this.courses];

    // Filtre par recherche
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(c =>
        c.title.toLowerCase().includes(searchLower) ||
        c.description.toLowerCase().includes(searchLower) ||
        c.tags.some(tag => tag.toLowerCase().includes(searchLower))
      );
    }

    // Filtre par catégorie
    if (filters.category && filters.category !== 'Tous') {
      filtered = filtered.filter(c => c.category === filters.category);
    }

    // Filtre par niveau
    if (filters.level) {
      filtered = filtered.filter(c => c.level === filters.level);
    }

    // Filtre par prix
    if (filters.minPrice !== undefined) {
      filtered = filtered.filter(c => c.price >= filters.minPrice!);
    }
    if (filters.maxPrice !== undefined) {
      filtered = filtered.filter(c => c.price <= filters.maxPrice!);
    }

    // Tri
    switch (filters.sort) {
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
      case 'newest':
        filtered.sort((a, b) => b.publishedDate.getTime() - a.publishedDate.getTime());
        break;
      default:
        break;
    }

    // Simulation d'appel API avec délai
    return of(filtered).pipe(delay(300));
  }

  /**
   * Récupère un cours par son ID
   */
  getCourseById(id: number): Course | undefined {
    return this.courses.find(c => c.id === id);
  }

  /**
   * Récupère les cours par catégorie
   */
  getCoursesByCategory(category: string): Course[] {
    return this.courses.filter(c => c.category === category);
  }

  /**
   * Récupère les meilleurs cours (top 3)
   */
  getTopCourses(limit: number = 3): Course[] {
    return [...this.courses]
      .sort((a, b) => b.rating - a.rating)
      .slice(0, limit);
  }

  /**
   * Récupère les cours les plus populaires
   */
  getPopularCourses(limit: number = 6): Course[] {
    return [...this.courses]
      .sort((a, b) => b.enrolledCount - a.enrolledCount)
      .slice(0, limit);
  }

  /**
   * Recherche avancée
   */
  searchCourses(query: string): Course[] {
    const lowerQuery = query.toLowerCase();
    return this.courses.filter(c =>
      c.title.toLowerCase().includes(lowerQuery) ||
      c.description.toLowerCase().includes(lowerQuery) ||
      c.tags.some(tag => tag.toLowerCase().includes(lowerQuery)) ||
      c.instructor.toLowerCase().includes(lowerQuery)
    );
  }
}