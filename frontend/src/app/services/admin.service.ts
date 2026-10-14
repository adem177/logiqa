import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AdminStats {
  total_users: number;
  total_etudiants: number;
  total_enseignants: number;
  total_admins: number;
  total_cours: number;
  total_chapitres: number;
  total_ressources: number;
  total_quiz: number;
  total_attempts: number;
  avg_score: number;
}

export interface AdminUser {
  id: number;
  nom: string;
  prenom: string;
  email: string;
  telephone: string | null;
  role: 'etudiant' | 'enseignant' | 'admin';
  status: number;
  created_at: string;
  last_login_at: string | null;
}

export interface AdminQuiz {
  id: number;
  titre: string;
  description: string;
  nombre_questions: number;
  methode_generation: string;
  created_at: string;
  chapitre_titre: string;
  cours_titre: string;
  createur_nom: string | null;
  createur_prenom: string | null;
  nb_attempts: number;
}

export interface AdminCours {
  id: number;
  titre: string;
  description: string;
  categorie: string;
  niveau: string;
  created_at: string;
  enseignant_id: number | null;
  enseignant_nom: string | null;
  enseignant_prenom: string | null;
  nb_chapitres: number;
}

export interface AdminRessource {
  id: number;
  type: 'pdf' | 'video';
  nom_original: string;
  taille: number | null;
  mime_type: string | null;
  created_at: string;
  chapitre_id: number;
  chapitre_titre: string;
  cours_titre: string;
  enseignant_nom: string | null;
  enseignant_prenom: string | null;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private API_URL = 'http://localhost:3000';

  constructor(private http: HttpClient) {}

  // ===== Statistiques =====
  getStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(`${this.API_URL}/api/admin/stats`);
  }

  // ===== Utilisateurs =====
  getUsers(): Observable<{ users: AdminUser[] }> {
    return this.http.get<{ users: AdminUser[] }>(`${this.API_URL}/api/admin/users`);
  }

  toggleUserStatus(userId: number): Observable<{ success: boolean; status: number }> {
    return this.http.put<{ success: boolean; status: number }>(
      `${this.API_URL}/api/admin/users/${userId}/status`, {}
    );
  }

  changeUserRole(userId: number, role: string): Observable<{ success: boolean; role: string }> {
    return this.http.put<{ success: boolean; role: string }>(
      `${this.API_URL}/api/admin/users/${userId}/role`, { role }
    );
  }

  deleteUser(userId: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.API_URL}/api/admin/users/${userId}`);
  }

  // ===== Matières =====
  getCours(): Observable<{ cours: AdminCours[] }> {
    return this.http.get<{ cours: AdminCours[] }>(`${this.API_URL}/api/admin/cours`);
  }

  createCours(data: { titre: string; description: string; categorie: string; niveau?: string }): Observable<any> {
    return this.http.post<any>(`${this.API_URL}/api/admin/cours`, data);
  }

  deleteCours(coursId: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.API_URL}/api/admin/cours/${coursId}`);
  }

  // ===== Quiz =====
  getQuiz(): Observable<{ quiz: AdminQuiz[] }> {
    return this.http.get<{ quiz: AdminQuiz[] }>(`${this.API_URL}/api/admin/quiz`);
  }

  deleteQuiz(quizId: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.API_URL}/api/admin/quiz/${quizId}`);
  }

  // ===== Ressources =====
  getRessources(): Observable<{ ressources: AdminRessource[] }> {
    return this.http.get<{ ressources: AdminRessource[] }>(`${this.API_URL}/api/admin/ressources`);
  }

  deleteRessource(resourceId: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(`${this.API_URL}/api/admin/ressources/${resourceId}`);
  }
}
