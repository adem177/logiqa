import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environements';

export interface QuizOption {
  id: number;
  texte: string;
}

export interface QuizQuestion {
  id: number;
  texte: string;
  ordre: number;
  options: QuizOption[];
}

export interface Quiz {
  id: number;
  titre: string;
  description: string;
  nombre_questions: number;
  methode_generation: string;
  questions?: QuizQuestion[];
  created_at?: string;
  createur_nom?: string | null;
  createur_prenom?: string | null;
  createur_role?: string | null;
}

export interface QuizCorrectionOption {
  option_id: number;
  option_texte: string;
  est_correcte: boolean;
}

export interface QuizCorrection {
  question_texte: string;
  options: QuizCorrectionOption[];
  reponse_correcte: string | null;
  reponse_etudiant: number | null;
}

export interface QuizAttemptResult {
  success: boolean;
  score: number;
  total: number;
  pourcentage: number;
  correction?: Record<number, QuizCorrection>;
}

@Injectable({ providedIn: 'root' })
export class QuizService {
  private http = inject(HttpClient);
  private readonly API_URL = environment.apiUrl;

  /**
   * Génère un quiz à partir des ressources d'un chapitre.
   */
  genererQuiz(chapitreId: number, nombreQuestions: number = 10, methode: string = 'auto'): Observable<any> {
    return this.http.post(`${this.API_URL}/api/chapitres/${chapitreId}/quiz/generer`, {
      nombre_questions: nombreQuestions,
      methode: methode
    });
  }

  /**
   * Liste les quiz d'un chapitre.
   */
  listerQuiz(chapitreId: number): Observable<Quiz[]> {
    return this.http.get<Quiz[]>(`${this.API_URL}/api/chapitres/${chapitreId}/quiz`);
  }

  /**
   * Récupère un quiz avec ses questions (sans les bonnes réponses).
   */
  getQuiz(quizId: number): Observable<Quiz> {
    return this.http.get<Quiz>(`${this.API_URL}/api/quiz/${quizId}`);
  }

  /**
   * Soumet les réponses d'un quiz.
   */
  soumettreQuiz(quizId: number, reponses: { question_id: number; option_id: number }[]): Observable<QuizAttemptResult> {
    return this.http.post<QuizAttemptResult>(`${this.API_URL}/api/quiz/${quizId}/soumettre`, { reponses });
  }

  /**
   * Régénère un nouveau quiz pour le même chapitre.
   */
  regenererQuiz(quizId: number): Observable<{ success: boolean; new_quiz_id: number; message: string }> {
    return this.http.post<{ success: boolean; new_quiz_id: number; message: string }>(
      `${this.API_URL}/api/quiz/${quizId}/regenerer`, {}
    );
  }

  /**
   * Récupère le dernier résultat d'un étudiant pour un quiz.
   */
  getResultat(quizId: number): Observable<QuizAttemptResult> {
    return this.http.get<QuizAttemptResult>(`${this.API_URL}/api/quiz/${quizId}/resultat`);
  }
}
