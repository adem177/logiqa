import { Component, ElementRef, HostListener, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { Auth } from '../../../core/auth';
import { LogoutConfirmComponent } from '../logout-confirm/logout-confirm';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, LogoutConfirmComponent],
  templateUrl: './navbar.html'
})
export class NavbarComponent implements OnInit, OnDestroy {
  isDropdownOpen = false;
  isLoggedIn = false;
  showLogoutConfirm = false;
  espaceLink = '/login';
  userLabel = '';
  userRole = '';

  private storageHandler = () => this.refreshAuth();

  constructor(
    private elementRef: ElementRef,
    private auth: Auth,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.refreshAuth();
    // window n'existe pas côté serveur (SSR) : on n'attache l'écouteur qu'en navigateur.
    if (typeof window !== 'undefined') {
      window.addEventListener('storage', this.storageHandler);
    }
    this.router.events.subscribe(() => {
      this.refreshAuth();
      this.closeDropdown();
    });
  }

  ngOnDestroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('storage', this.storageHandler);
    }
  }

  private refreshAuth(): void {
    this.isLoggedIn = this.auth.isLoggedIn();
    const role = this.auth.getRole();
    this.userRole = role || '';
    this.espaceLink =
      role === 'admin' ? '/dashboard-admin' :
      role === 'enseignant' ? '/dashboard-enseignant' :
      role ? '/cours' : '/login';

    // Nom affiché dans le menu
    const user = this.auth.getUser();
    if (user) {
      const nom = user.nom || '';
      const prenom = user.prenom || '';
      this.userLabel = `${prenom} ${nom}`.trim() || user.email || '';
    } else {
      this.userLabel = '';
    }
  }

  logout(): void {
    this.closeDropdown();
    this.auth.logout();
  }

  /**
   * Clic sur le logo LOGIQA : demande de confirmation puis déconnexion
   * (identique à « Déconnexion ») si une session est active,
   * sinon retour à l'accueil.
   */
  onLogoClick(): void {
    if (this.isLoggedIn) {
      this.showLogoutConfirm = true;
    } else {
      this.router.navigate(['/']);
    }
  }

  /** Confirmation « Oui » : ferme la fenêtre et déconnecte. */
  confirmLogout(): void {
    this.showLogoutConfirm = false;
    this.logout();
  }

  toggleDropdown(event: MouseEvent) {
    event.stopPropagation();
    this.isDropdownOpen = !this.isDropdownOpen;
  }

  closeDropdown() {
    this.isDropdownOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isDropdownOpen = false;
    }
  }
}
