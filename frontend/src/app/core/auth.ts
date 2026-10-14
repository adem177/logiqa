import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class Auth {
  private router = inject(Router);
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private API_URL = 'http://localhost:3000';

  /** localStorage n'existe que dans le navigateur (pas en SSR/serveur). */
  private get storage(): Storage | null {
    return isPlatformBrowser(this.platformId) ? localStorage : null;
  }

  getToken(): string | null {
    return this.storage?.getItem('token') ?? null;
  }

  getUser(): any | null {
    const raw = this.storage?.getItem('user');
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  }

  getRole(): string | null {
    const payload = this.decodeToken();
    if (payload && payload.role) return payload.role;
    return this.getUser()?.role ?? null;
  }

  isLoggedIn(): boolean {
    // Côté serveur : toujours déconnecté (pas de session côté Node).
    if (!isPlatformBrowser(this.platformId)) return false;

    const token = this.getToken();
    if (!token) return false;
    if (this.isTokenExpired()) {
      this.clearSession();
      return false;
    }
    return true;
  }

  hasRole(roles: string[]): boolean {
    const role = this.getRole();
    return !!role && roles.includes(role);
  }

  isTokenExpired(): boolean {
    const payload = this.decodeToken();
    if (!payload || !payload.exp) return true;
    return payload.exp * 1000 <= Date.now();
  }

  logout(): void {
    const token = this.getToken();
    if (token) {
      this.http.post(`${this.API_URL}/api/logout`, {}).subscribe({
        error: () => {}
      });
    }
    this.clearSession();
    this.router.navigate(['/login']);
  }

  clearSession(): void {
    this.storage?.removeItem('token');
    this.storage?.removeItem('user');
  }

  private decodeToken(): any | null {
    const token = this.getToken();
    if (!token) return null;
    try {
      const payload = token.split('.')[1];
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decoded);
    } catch {
      return null;
    }
  }
}
