import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  // Étape 1 : identifiants
  login: string = '';
  password: string = '';
  captchaInput: string = '';
  captchaCode: string = '';

  // Étape 2 : code OTP
  otpStep = false;
  otpCode = '';
  pendingUserId: number | null = null;

  errorMessage: string = '';
  errorVisible: boolean = false;

  constructor(private http: HttpClient, private router: Router) {
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

  validerConnexion(): void {
    if (this.captchaInput !== this.captchaCode) {
      this.errorMessage = 'Code de vérification incorrect. Veuillez réessayer.';
      this.errorVisible = true;
      this.refreshCaptcha();
      this.captchaInput = '';
      return;
    }

    if (!this.login || !this.password) {
      this.errorMessage = 'Veuillez remplir tous les champs.';
      this.errorVisible = true;
      return;
    }

    this.http.post('http://localhost:3000/api/login', {
      email: this.login,
      password: this.password
    }).subscribe({
      next: (response: any) => {
        this.pendingUserId = response.user_id;
        this.otpStep = true;
        this.errorVisible = false;
      },
      error: (err) => {
        this.errorMessage = err.error?.error || 'Email ou mot de passe incorrect.';
        this.errorVisible = true;
        this.refreshCaptcha();
        this.captchaInput = '';
      }
    });
  }

  validerOtp(): void {
    this.http.post('http://localhost:3000/api/verify-otp', {
      user_id: this.pendingUserId,
      code: this.otpCode
    }).subscribe({
      next: (response: any) => {
        localStorage.setItem('token', response.token);
        localStorage.setItem('user', JSON.stringify(response.user));
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.errorMessage = err.error?.error || 'Code incorrect.';
        this.errorVisible = true;
      }
    });
  }
}