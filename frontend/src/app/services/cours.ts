import {
  Component,
  signal,
  computed,
  OnInit,
  inject
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { CourseService } from '../services/course.service';


interface Course {
  id: number;
  slug?: string;
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
  imports: [
    CommonModule,
    RouterModule,
    FormsModule
  ],
  templateUrl: './cours.html',
  styleUrls: ['./cours.css']
})
export class CoursesComponent implements OnInit {

  private router = inject(Router);
  private courseService = inject(CourseService);


  // ==========================================
  // LISTE DES COURS
  // ==========================================

  courses = signal<Course[]>([]);

  searchTerm = signal<string>('');
  selectedCategory = signal<string>('Tous');
  selectedSort = signal<string>('popular');

  isSearchFocused = false;
  isLoading = signal<boolean>(false);
  error = signal<string | null>(null);

  currentPage = signal<number>(1);
  itemsPerPage = 6;


  // ==========================================
  // COURS STATIQUES
  // ==========================================

  allCourses: Course[] = [

    {
      id: 1,
      slug: 'langage-c',
      title: 'Python',
      category: 'Programmation',
      description:
        'Maîtrisez Python. Variables, boucles, fonctions, POO et projets concrets.',
      lessons: 28,
      tags: [
        'Bases',
        'POO',
        'Fichiers'
      ],
      image: 'python.png'
    },

    {
      id: 2,
      slug: 'algebre',
      title: 'Algèbre',
      category: 'Mathématiques',
      description:
        'De l\'arithmétique à l\'algèbre généralisée. Équations, polynômes et fonctions.',
      lessons: 32,
      tags: [
        'Équations',
        'Polynômes',
        'Fonctions'
      ],
      image: 'algebra.jpg'
    },

    {
      id: 3,
      slug: 'analyse',
      title: 'Analyse',
      category: 'Mathématiques',
      description:
        'Suites numériques, limites, dérivation et intégration.',
      lessons: 30,
      tags: [
        'Suites',
        'Limites',
        'Intégrales'
      ],
      image: 'analyse.jpg'
    },

    {
      id: 4,
      slug: 'systeme-exploitation',
      title: 'Système d\'exploitation',
      category: 'Informatique',
      description:
        'Découvrez les concepts fondamentaux des systèmes d\'exploitation. Processus, mémoire et fichiers.',
      lessons: 25,
      tags: [
        'Processus',
        'Mémoire',
        'Fichiers'
      ],
      image: 'windows.jpg'
    },

    {
      id: 5,
      slug: 'base-de-donnees',
      title: 'Base de données',
      category: 'Informatique',
      description:
        'Concevez et gérez des bases de données relationnelles. Modélisation, SQL et normalisation.',
      lessons: 24,
      tags: [
        'SQL',
        'Modélisation',
        'Normalisation'
      ],
      image: 'bdd.jpg'
    },

    {
      id: 6,
      slug: 'reseaux',
      title: 'Réseaux',
      category: 'Informatique',
      description:
        'Comprenez le fonctionnement des réseaux informatiques. Modèle OSI, TCP/IP et protocoles.',
      lessons: 22,
      tags: [
        'OSI',
        'TCP/IP',
        'Protocoles'
      ],
      image: 'reseaux.jpg'
    },

    {
      id: 7,
      slug: 'systemes-logiques',
      title: 'Systèmes logiques et architecture',
      category: 'Informatique',
      description:
        'Systèmes de numération, codage de l\'information et architecture des ordinateurs.',
      lessons: 20,
      tags: [
        'Binaire',
        'Portes Logiques',
        'CPU'
      ],
      image: 'architecture.jpg'
    }

  ];


  // ==========================================
  // CATEGORIES
  // ==========================================

  categories = signal<string[]>([
    'Tous',
    'Programmation',
    'Mathématiques',
    'Informatique',
    'Développement Web'
  ]);


  // ==========================================
  // OPTIONS DE TRI
  // ==========================================

  sortOptions = [
    {
      value: 'popular',
      label: 'Plus consultés'
    },
    {
      value: 'recent',
      label: 'Plus récents'
    },
    {
      value: 'lessons',
      label: 'Par nombre de leçons'
    }
  ];


  // ==========================================
  // INITIALISATION
  // ==========================================

  ngOnInit(): void {
    this.loadCourses();
  }


  // ==========================================
  // CHARGER LES COURS
  // ==========================================

  loadCourses(): void {

    this.isLoading.set(true);
    this.error.set(null);

    setTimeout(() => {

      try {

        // Récupérer les cours depuis CourseService
        const serviceCourses =
          this.courseService.courses();


        // Transformer les cours du service
        const formattedDynamic: Course[] =
          serviceCourses.map(course => {

            // Nombre de chapitres publiés
            let totalLessons = 0;

            course.sections.forEach(section => {
              totalLessons += section.chapters.length;
            });


            // Tags = titres des chapitres
            const tags: string[] = [];

            course.sections.forEach(section => {

              section.chapters.forEach(chapter => {

                if (tags.length < 3) {

                  const chapterName =
                    chapter.title.replace(
                      /Chapitre\s+\d+\s*:\s*/i,
                      ''
                    );

                  tags.push(chapterName);
                }

              });

            });


            // Tags par défaut
            if (tags.length === 0) {
              tags.push(
                course.category,
                'Formation',
                'Cours'
              );
            }


            return {
              id: course.id,
              slug: course.slug,
              title: course.title,
              category: course.category || 'Informatique',
              description: course.description || '',
              lessons: totalLessons > 0 ? totalLessons : 1,
              tags: tags,
              image: course.thumbnail || 'assets/placeholder-course.jpg'
            };

          });


        // Commencer avec les cours statiques
        const combined: Course[] = [
          ...this.allCourses
        ];


        // Fusion avec les cours du service
        formattedDynamic.forEach(dynamicCourse => {

          const index =
            combined.findIndex(
              staticCourse =>
                staticCourse.slug === dynamicCourse.slug
            );


          if (index !== -1) {

            // Le cours existe déjà
            const staticCourse = combined[index];

            combined[index] = {
              ...staticCourse,

              // Mettre à jour les leçons
              lessons: dynamicCourse.lessons,

              // Mettre à jour les tags
              tags:
                dynamicCourse.tags.length > 0
                  ? dynamicCourse.tags
                  : staticCourse.tags
            };

          } else {

            // Nouveau cours
            combined.push(dynamicCourse);
          }

        });


        // Mettre à jour la liste affichée
        this.courses.set(combined);

        this.isLoading.set(false);

      } catch (err) {

        console.error(err);

        this.error.set(
          'Impossible de charger les cours.'
        );

        this.isLoading.set(false);
      }

    }, 300);

  }


  // ==========================================
  // FILTRAGE DES COURS
  // ==========================================

  filteredCourses = computed(() => {

    let result = this.courses();


    // Filtre par catégorie
    if (this.selectedCategory() !== 'Tous') {

      result = result.filter(
        course =>
          course.category ===
          this.selectedCategory()
      );

    }


    // Recherche
    const term =
      this.searchTerm()
        .toLowerCase()
        .trim();


    if (term) {

      result = result.filter(
        course =>

          course.title
            .toLowerCase()
            .includes(term)

          ||

          course.description
            .toLowerCase()
            .includes(term)

          ||

          course.category
            .toLowerCase()
            .includes(term)

          ||

          course.tags.some(
            tag =>
              tag
                .toLowerCase()
                .includes(term)
          )
      );

    }


    // Tri
    switch (this.selectedSort()) {

      case 'lessons':

        result = [...result].sort(
          (a, b) =>
            b.lessons - a.lessons
        );

        break;


      case 'recent':

        result = [...result].sort(
          (a, b) =>
            b.id - a.id
        );

        break;


      default:

        result = [...result].sort(
          (a, b) =>
            a.id - b.id
        );

        break;

    }


    return result;

  });


  // ==========================================
  // PAGINATION
  // ==========================================

  paginatedCourses = computed(() => {

    const start =
      (this.currentPage() - 1) *
      this.itemsPerPage;

    return this.filteredCourses().slice(
      start,
      start + this.itemsPerPage
    );

  });


  // ==========================================
  // TOTAL DES PAGES
  // ==========================================

  totalPages = computed(() => {

    return Math.ceil(
      this.filteredCourses().length /
      this.itemsPerPage
    );

  });


  // ==========================================
  // NUMEROS DES PAGES
  // ==========================================

  pageNumbers = computed(() => {

    const pages: number[] = [];

    for (
      let i = 1;
      i <= this.totalPages();
      i++
    ) {
      pages.push(i);
    }

    return pages;

  });


  // ==========================================
  // STATISTIQUES
  // ==========================================

  stats = computed(() => ({
    categories:
      this.categories().length - 1
  }));


  // ==========================================
  // FILTRE PAR CATEGORIE
  // ==========================================

  selectCategory(category: string): void {

    this.selectedCategory.set(category);

    this.currentPage.set(1);

  }


  // ==========================================
  // CHANGER LE TRI
  // ==========================================

  changeSort(value: string): void {

    this.selectedSort.set(value);

  }


  // ==========================================
  // EFFACER LA RECHERCHE
  // ==========================================

  clearSearch(): void {

    this.searchTerm.set('');

    this.currentPage.set(1);

  }


  // ==========================================
  // PAGE PRECEDENTE
  // ==========================================

  previousPage(): void {

    if (this.currentPage() > 1) {

      this.currentPage.update(
        page => page - 1
      );

    }

  }


  // ==========================================
  // PAGE SUIVANTE
  // ==========================================

  nextPage(): void {

    if (
      this.currentPage() <
      this.totalPages()
    ) {

      this.currentPage.update(
        page => page + 1
      );

    }

  }


  // ==========================================
  // ALLER A UNE PAGE
  // ==========================================

  goToPage(page: number): void {

    this.currentPage.set(page);

  }


  // ==========================================
  // VOIR LE COURS
  // ==========================================

  viewCourse(course: Course): void {

    const targetParam =
      course.slug
        ? course.slug
        : course.id;

    this.router.navigate([
      '/cours',
      targetParam
    ]);

  }


  // ==========================================
  // IMAGE PAR DEFAUT
  // ==========================================

  onImageError(event: Event): void {

    const img = event.target as HTMLImageElement;

    img.src = 'assets/placeholder-course.jpg';

  }

}