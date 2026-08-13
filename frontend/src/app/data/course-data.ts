// src/app/data/course-data.ts

export interface Chapter {
  id: number;
  number: number;
  title: string;
  videosCount: number;
  pdfsCount: number;
  progress: number;
}

export interface Section {
  id: number;
  title: string;
  chapters: Chapter[];
}

export interface CourseDetail {
  id: number;
  title: string;
  sections: Section[];
}

export const COURSES_DETAILS: CourseDetail[] = [
  // ═══════════════════════════════════════════
  // 1. PYTHON
  // ═══════════════════════════════════════════
  {
    id: 1,
    title: 'Python',
    sections: [
      {
        id: 1,
        title: 'Section 1 : Les fondamentaux',
        chapters: [
          { id: 1, number: 1, title: 'Introduction à Python', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 2, number: 2, title: 'Variables et types de données', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 3, number: 3, title: 'Structures de contrôle (if, for, while)', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 4, number: 4, title: 'Fonctions et modules', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 2,
        title: 'Section 2 : Structures de données',
        chapters: [
          { id: 5, number: 5, title: 'Listes, tuples et dictionnaires', videosCount: 4, pdfsCount: 2, progress: 0 },
          { id: 6, number: 6, title: 'Manipulation de fichiers', videosCount: 4, pdfsCount: 1, progress: 0 },
        ]
      }
    ]
  },

  // ═══════════════════════════════════════════
  // 2. ALGÈBRE
  // ═══════════════════════════════════════════
  {
    id: 2,
    title: 'Algèbre',
    sections: [
      {
        id: 1,
        title: 'Section 1 : Les fondamentaux de l\'algèbre',
        chapters: [
          { id: 1, number: 1, title: 'Introduction à l\'algèbre', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 2, number: 2, title: 'Les nombres réels et les opérations', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 3, number: 3, title: 'Les puissances et les racines', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 4, number: 4, title: 'Les identités remarquables', videosCount: 4, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 2,
        title: 'Section 2 : Équations et inéquations',
        chapters: [
          { id: 5, number: 5, title: 'Équations du premier degré', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 6, number: 6, title: 'Équations du second degré', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 7, number: 7, title: 'Inéquations et systèmes d\'équations', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 3,
        title: 'Section 3 : Polynômes et factorisation',
        chapters: [
          { id: 8, number: 8, title: 'Définition et degré d\'un polynôme', videosCount: 4, pdfsCount: 1, progress: 0 },
          { id: 9, number: 9, title: 'Factorisation et développement', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 10, number: 10, title: 'Division euclidienne des polynômes', videosCount: 4, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 4,
        title: 'Section 4 : Fonctions algébriques',
        chapters: [
          { id: 11, number: 11, title: 'Fonctions affines et linéaires', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 12, number: 12, title: 'Fonctions polynômes du second degré', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 13, number: 13, title: 'Fonctions rationnelles', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      }
    ]
  },

  // ═══════════════════════════════════════════
  // 3. ANALYSE
  // ═══════════════════════════════════════════
  {
    id: 3,
    title: 'Analyse',
    sections: [
      {
        id: 1,
        title: 'Section 1 : Suites numériques',
        chapters: [
          { id: 1, number: 1, title: 'Introduction aux suites', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 2, number: 2, title: 'Suites arithmétiques et géométriques', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 3, number: 3, title: 'Monotonie et convergence', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 4, number: 4, title: 'Suites récurrentes', videosCount: 4, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 2,
        title: 'Section 2 : Limites et continuité',
        chapters: [
          { id: 5, number: 5, title: 'Limite d\'une fonction', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 6, number: 6, title: 'Opérations sur les limites', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 7, number: 7, title: 'Continuité et théorème des valeurs intermédiaires', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 3,
        title: 'Section 3 : Dérivation',
        chapters: [
          { id: 8, number: 8, title: 'Nombre dérivé et interprétation géométrique', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 9, number: 9, title: 'Règles de dérivation', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 10, number: 10, title: 'Étude de fonctions', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 4,
        title: 'Section 4 : Intégration',
        chapters: [
          { id: 11, number: 11, title: 'Primitives et intégrales', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 12, number: 12, title: 'Méthodes d\'intégration', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 13, number: 13, title: 'Intégrales et calcul d\'aires', videosCount: 4, pdfsCount: 2, progress: 0 },
        ]
      }
    ]
  },

  // ═══════════════════════════════════════════
  // 4. HTML & CSS
  // ═══════════════════════════════════════════
  {
    id: 4,
    title: 'HTML & CSS',
    sections: [
      {
        id: 1,
        title: 'Section 1 : Bases du HTML',
        chapters: [
          { id: 1, number: 1, title: 'Structure d\'une page HTML', videosCount: 4, pdfsCount: 2, progress: 0 },
          { id: 2, number: 2, title: 'Balises texte et liens', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 3, number: 3, title: 'Images, tableaux et formulaires', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 4, number: 4, title: 'Sémantique HTML5', videosCount: 4, pdfsCount: 1, progress: 0 },
        ]
      },
      {
        id: 2,
        title: 'Section 2 : CSS fondamental',
        chapters: [
          { id: 5, number: 5, title: 'Sélecteurs et propriétés CSS', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 6, number: 6, title: 'Le modèle de boîte (box model)', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 7, number: 7, title: 'Positionnement et display', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 3,
        title: 'Section 3 : Mise en page moderne',
        chapters: [
          { id: 8, number: 8, title: 'Flexbox', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 9, number: 9, title: 'CSS Grid', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 10, number: 10, title: 'Media queries et responsive design', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 4,
        title: 'Section 4 : CSS avancé',
        chapters: [
          { id: 11, number: 11, title: 'Animations et transitions', videosCount: 5, pdfsCount: 1, progress: 0 },
          { id: 12, number: 12, title: 'Variables CSS et préprocesseurs', videosCount: 4, pdfsCount: 2, progress: 0 },
        ]
      }
    ]
  },

  // ═══════════════════════════════════════════
  // 5. JAVA
  // ═══════════════════════════════════════════
  {
    id: 5,
    title: 'Java',
    sections: [
      {
        id: 1,
        title: 'Section 1 : Les bases de Java',
        chapters: [
          { id: 1, number: 1, title: 'Introduction à Java et la JVM', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 2, number: 2, title: 'Variables, types et opérateurs', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 3, number: 3, title: 'Structures conditionnelles et boucles', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 4, number: 4, title: 'Tableaux et méthodes', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 2,
        title: 'Section 2 : Programmation orientée objet',
        chapters: [
          { id: 5, number: 5, title: 'Classes et objets', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 6, number: 6, title: 'Encapsulation et constructeurs', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 7, number: 7, title: 'Héritage et polymorphisme', videosCount: 6, pdfsCount: 3, progress: 0 },
        ]
      },
      {
        id: 3,
        title: 'Section 3 : Java avancé',
        chapters: [
          { id: 8, number: 8, title: 'Collections (List, Set, Map)', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 9, number: 9, title: 'Gestion des exceptions', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 10, number: 10, title: 'Fichiers et streams', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 4,
        title: 'Section 4 : Projets pratiques',
        chapters: [
          { id: 11, number: 11, title: 'Application console gestionnaire', videosCount: 5, pdfsCount: 1, progress: 0 },
          { id: 12, number: 12, title: 'Mini projet final', videosCount: 6, pdfsCount: 1, progress: 0 },
        ]
      }
    ]
  },

  // ═══════════════════════════════════════════
  // 6. REACT
  // ═══════════════════════════════════════════
  {
    id: 6,
    title: 'React',
    sections: [
      {
        id: 1,
        title: 'Section 1 : Fondamentaux React',
        chapters: [
          { id: 1, number: 1, title: 'Introduction à React et JSX', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 2, number: 2, title: 'Components et Props', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 3, number: 3, title: 'State et cycle de vie', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 4, number: 4, title: 'Gestion des événements', videosCount: 4, pdfsCount: 1, progress: 0 },
        ]
      },
      {
        id: 2,
        title: 'Section 2 : Hooks',
        chapters: [
          { id: 5, number: 5, title: 'useState et useEffect', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 6, number: 6, title: 'useContext et useReducer', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 7, number: 7, title: 'Custom Hooks', videosCount: 4, pdfsCount: 1, progress: 0 },
        ]
      },
      {
        id: 3,
        title: 'Section 3 : État global et routing',
        chapters: [
          { id: 8, number: 8, title: 'React Router', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 9, number: 9, title: 'Redux Toolkit', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 10, number: 10, title: 'Zustand vs Redux', videosCount: 4, pdfsCount: 1, progress: 0 },
        ]
      },
      {
        id: 4,
        title: 'Section 4 : React avancé',
        chapters: [
          { id: 11, number: 11, title: 'Next.js et SSR', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 12, number: 12, title: 'Tests avec React Testing Library', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      }
    ]
  },

  // ═══════════════════════════════════════════
  // 7. ANGULAR
  // ═══════════════════════════════════════════
  {
    id: 7,
    title: 'Angular',
    sections: [
      {
        id: 1,
        title: 'Section 1 : Les bases d\'Angular',
        chapters: [
          { id: 1, number: 1, title: 'Architecture Angular et CLI', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 2, number: 2, title: 'Components et templates', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 3, number: 3, title: 'Data binding et directives', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 4, number: 4, title: 'Pipes et formulaires', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 2,
        title: 'Section 2 : Services et routing',
        chapters: [
          { id: 5, number: 5, title: 'Services et injection de dépendances', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 6, number: 6, title: 'Routing et navigation', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 7, number: 7, title: 'Guards et lazy loading', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 3,
        title: 'Section 3 : RxJS et HTTP',
        chapters: [
          { id: 8, number: 8, title: 'Introduction à RxJS et Observables', videosCount: 6, pdfsCount: 3, progress: 0 },
          { id: 9, number: 9, title: 'HttpClient et API REST', videosCount: 5, pdfsCount: 2, progress: 0 },
          { id: 10, number: 10, title: 'Gestion des erreurs et intercepteurs', videosCount: 5, pdfsCount: 2, progress: 0 },
        ]
      },
      {
        id: 4,
        title: 'Section 4 : Angular moderne',
        chapters: [
          { id: 11, number: 11, title: 'Standalone components', videosCount: 5, pdfsCount: 1, progress: 0 },
          { id: 12, number: 12, title: 'Signals et change detection', videosCount: 6, pdfsCount: 2, progress: 0 },
          { id: 13, number: 13, title: 'Déploiement et optimisation', videosCount: 4, pdfsCount: 1, progress: 0 },
        ]
      }
    ]
  }
];