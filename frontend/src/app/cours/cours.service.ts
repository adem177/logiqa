import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Cours {
  id?: number;
  titre: string;
  description: string;
  categorie: string;
  niveau: string;
  enseignant?: string;
  image?: string;
}

@Injectable({
  providedIn: 'root'
})
export class CoursService {
  private baseUrl = 'http://localhost:3000/api/cours';

  constructor(private http: HttpClient) {}

  getAll(): Observable<Cours[]> {
    return this.http.get<Cours[]>(this.baseUrl);
  }

  getById(id: number): Observable<Cours> {
    return this.http.get<Cours>(`${this.baseUrl}/${id}`);
  }

  create(cours: Cours): Observable<Cours> {
    return this.http.post<Cours>(this.baseUrl, cours);
  }

  update(id: number, cours: Cours): Observable<Cours> {
    return this.http.put<Cours>(`${this.baseUrl}/${id}`, cours);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
