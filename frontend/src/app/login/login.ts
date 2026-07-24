import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  login: string = '';
  password: string = '';
  captchaInput: string = '';
  captchaCode: string = '';
  errorMessage: string = '';
  errorVisible: boolean = false;

  constructor(private router: Router) {
    this.refreshCaptcha();
  }

  refreshCaptcha(): void {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 7; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    this.captchaCode = result;
  }

  validerConnexion(): boolean {
    if (this.captchaInput !== this.captchaCode) {
      this.errorMessage = 'Code de vérification incorrect. Veuillez réessayer.';
      this.errorVisible = true;
      this.refreshCaptcha();
      this.captchaInput = '';
      return false;
    }

    if (!this.login || !this.password) {
      this.errorMessage = 'Veuillez remplir tous les champs.';
      this.errorVisible = true;
      return false;
    }

    // TODO : remplacer par un vrai appel API d'authentification
    console.log('Connexion réussie pour:', this.login);
    this.errorVisible = false;

    // Redirection vers le tableau de bord
    this.router.navigate(['/dashboard']);
    return true;
  }
}