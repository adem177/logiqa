import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environements';

export interface EnseignantCours {
  id: number;
  titre: string;
  description: string;
  categorie: string;
  niveau: string;
  enseignant_id: number;
  nb_chapitres: number;
}

@Injectable({ providedIn: 'root' })
export class EnseignantService {
  private readonly API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /** Liste des cours appartenant à l'enseignant connecté. */
  getMesCours(): Observable<EnseignantCours[]> {
    return this.http.get<EnseignantCours[]>(`${this.API_URL}/api/enseignant/cours`);
  }

  /** Met à jour un cours (propriétaire uniquement, vérifié côté backend). */
  updateCours(coursId: number, data: {
    titre: string; description: string; categorie: string; niveau: string
  }): Observable<any> {
    return this.http.put<any>(`${this.API_URL}/api/cours/${coursId}`, data);
  }

  /** Supprime un cours (propriétaire uniquement, vérifié côté backend). */
  deleteCours(coursId: number): Observable<any> {
    return this.http.delete<any>(`${this.API_URL}/api/cours/${coursId}`);
  }
}
