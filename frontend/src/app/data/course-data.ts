// src/app/data/course-data.ts

export interface Chapter {
  id: number;
  number: number;
  title: string;
  videosCount: number;
  pdfsCount: number;
  progress: number;
}

export interface CourseDetail {
  id: number;
  title: string;
  slug: string;
  chapters: Chapter[];
}

export const COURSES_DETAILS: CourseDetail[] = [
  // ═══════════════════════════════════════════
  // 1. LANGAGE C
  // ═══════════════════════════════════════════
  {
    id: 1,
    title: 'Langage C',
    slug: 'langage-c',
    chapters: [
      { id: 1, number: 1, title: 'Introduction et structure d\'un programme C', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 2, number: 2, title: 'Variables, types de données et opérateurs', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 3, number: 3, title: 'Structures de contrôle (if, switch, while, for)', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 4, number: 4, title: 'Fonctions et passage de paramètres', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 5, number: 5, title: 'Pointeurs et gestion de la mémoire', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 6, number: 6, title: 'Tableaux, chaînes et structures (struct)', videosCount: 4, pdfsCount: 2, progress: 0 }
    ]
  },

  // ═══════════════════════════════════════════
  // 2. ALGÈBRE
  // ═══════════════════════════════════════════
  {
    id: 2,
    title: 'Algèbre',
    slug: 'algebre',
    chapters: [
      { id: 7, number: 1, title: 'Introduction à l\'algèbre', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 8, number: 2, title: 'Les nombres réels et les opérations', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 9, number: 3, title: 'Équations du premier et second degré', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 10, number: 4, title: 'Polynômes et factorisation', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 11, number: 5, title: 'Fonctions affines et linéaires', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 12, number: 6, title: 'Fonctions polynômes du second degré', videosCount: 6, pdfsCount: 3, progress: 0 }
    ]
  },

  // ═══════════════════════════════════════════
  // 3. ANALYSE
  // ═══════════════════════════════════════════
  {
    id: 3,
    title: 'Analyse',
    slug: 'analyse',
    chapters: [
      { id: 13, number: 1, title: 'Introduction aux suites numériques', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 14, number: 2, title: 'Suites arithmétiques et géométriques', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 15, number: 3, title: 'Limites et continuité', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 16, number: 4, title: 'Règles de dérivation', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 17, number: 5, title: 'Étude de fonctions', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 18, number: 6, title: 'Primitives et intégrales', videosCount: 5, pdfsCount: 2, progress: 0 }
    ]
  },

  // ═══════════════════════════════════════════
  // 4. SYSTÈMES LOGIQUES ET ARCHITECTURE
  // ═══════════════════════════════════════════
  {
    id: 4,
    title: 'Systèmes logiques et architecture',
    slug: 'systemes-logiques',
    chapters: [
      { id: 19, number: 1, title: 'Systèmes de numération et codage de l\'information', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 20, number: 2, title: 'Algèbre de Boole et portes logiques', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 21, number: 3, title: 'Simplification des fonctions logiques (Tables de Karnaugh)', videosCount: 6, pdfsCount: 2, progress: 0 },
      { id: 22, number: 4, title: 'Circuits combinatoires (Multiplexeurs, Décodeurs, Additionneurs)', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 23, number: 5, title: 'Circuits séquentiels (Basculeurs, Compteurs, Registres)', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 24, number: 6, title: 'Architecture de Von Neumann et jeu d\'instructions', videosCount: 5, pdfsCount: 2, progress: 0 }
    ]
  },

  // ═══════════════════════════════════════════
  // 5. ALGORITHMES
  // ═══════════════════════════════════════════
  {
    id: 5,
    title: 'Algorithmes',
    slug: 'algorithmes',
    chapters: [
      { id: 25, number: 1, title: 'Introduction à l\'algorithmique', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 26, number: 2, title: 'Variables, conditions et boucles', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 27, number: 3, title: 'Complexité algorithmique et notation Big O', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 28, number: 4, title: 'Algorithmes de tri (bulles, insertion, rapide)', videosCount: 6, pdfsCount: 2, progress: 0 },
      { id: 29, number: 5, title: 'Recherche linéaire et dichotomique', videosCount: 4, pdfsCount: 1, progress: 0 },
      { id: 30, number: 6, title: 'Piles, files et listes chaînées', videosCount: 5, pdfsCount: 2, progress: 0 }
    ]
  },

  // ═══════════════════════════════════════════
  // 6. BASE DE DONNÉES
  // ═══════════════════════════════════════════
  {
    id: 6,
    title: 'Base de données',
    slug: 'base-de-donnees',
    chapters: [
      { id: 31, number: 1, title: 'Introduction et modèle entité-association', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 32, number: 2, title: 'Passage au modèle relationnel et normalisation', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 33, number: 3, title: 'Création et manipulation des tables (DDL/DML)', videosCount: 6, pdfsCount: 2, progress: 0 },
      { id: 34, number: 4, title: 'Requêtes de sélection et filtres SQL', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 35, number: 5, title: 'Jointures et sous-requêtes SQL', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 36, number: 6, title: 'Index, transactions et performances', videosCount: 5, pdfsCount: 2, progress: 0 }
    ]
  },

  // ═══════════════════════════════════════════
  // 7. RÉSEAUX
  // ═══════════════════════════════════════════
  {
    id: 7,
    title: 'Réseaux',
    slug: 'reseaux',
    chapters: [
      { id: 37, number: 1, title: 'Introduction aux réseaux et modèle OSI', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 38, number: 2, title: 'Le modèle TCP/IP', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 39, number: 3, title: 'Adressage IP et sous-réseaux', videosCount: 6, pdfsCount: 2, progress: 0 },
      { id: 40, number: 4, title: 'Routage et commutation', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 41, number: 5, title: 'Protocoles applicatifs (HTTP, DNS, DHCP)', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 42, number: 6, title: 'Sécurité réseau de base (pare-feu, VPN)', videosCount: 5, pdfsCount: 2, progress: 0 }
    ]
  },

  // ═══════════════════════════════════════════
  // 8. SYSTÈME D'EXPLOITATION
  // ═══════════════════════════════════════════
  {
    id: 8,
    title: 'Système d\'exploitation',
    slug: 'systeme-exploitation',
    chapters: [
      { id: 43, number: 1, title: 'Architecture d\'un système d\'exploitation', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 44, number: 2, title: 'Notion de processus et de thread', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 45, number: 3, title: 'Ordonnancement des processus', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 46, number: 4, title: 'Synchronisation et interblocage', videosCount: 6, pdfsCount: 3, progress: 0 },
      { id: 47, number: 5, title: 'Mémoire virtuelle et pagination', videosCount: 5, pdfsCount: 2, progress: 0 },
      { id: 48, number: 6, title: 'Systèmes de fichiers et entrées/sorties', videosCount: 5, pdfsCount: 2, progress: 0 }
    ]
  }
];