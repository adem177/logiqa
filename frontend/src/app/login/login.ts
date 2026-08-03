import { Component, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { Subject, EMPTY } from 'rxjs';
import { takeUntil, timeout, catchError, finalize } from 'rxjs/operators';
import { environment } from '../../environments/environements';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent implements OnDestroy {
  login: string = '';
  password: string = '';
  captchaInput: string = '';
  captchaCode: string = '';
  isSubmitting: boolean = false;

  otpStep: boolean = false;
  otpCode: string = '';
  pendingUserId: number | null = null;
  emailDisplay: string = '';
  isVerifying: boolean = false;
  isResending: boolean = false;

  timer: number = 300;
  timerInterval: any = null;

  errorVisible: boolean = false;
  errorMessage: string = '';
  successVisible: boolean = false;
  successMessage: string = '';

  private readonly HTTP_TIMEOUT = 15000; // 15 secondes
  private readonly SAFETY_TIMEOUT = 20000; // 20 secondes filet absolu
  private destroy$ = new Subject<void>();

  constructor(
    private http: HttpClient,
    private router: Router,
    private cdr: ChangeDetectorRef   // ← AJOUTÉ
  ) {
    this.refreshCaptcha();
  }

  ngOnDestroy(): void {
    this.stopTimer();
    this.destroy$.next();
    this.destroy$.complete();
  }

  get formattedTimer(): string {
    const m = Math.floor(this.timer / 60);
    const s = this.timer % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }

  isValidEmail(): boolean {
    return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(this.login.trim());
  }

  maskEmail(email: string): string {
    const [name, domain] = email.split('@');
    if (!domain) return email;
    if (name.length <= 2) return `${name.charAt(0)}***@${domain}`;
    return `${name.charAt(0)}***${name.charAt(name.length - 1)}@${domain}`;
  }

  isValidPassword(): boolean {
    return this.password.length >= 8 && /[A-Za-z]/.test(this.password) && /\d/.test(this.password);
  }

  refreshCaptcha(): void {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < 6; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    this.captchaCode = result;
  }

  // ===== CONNEXION ÉTAPE 1 =====
  validerConnexion(): void {
    if (this.isSubmitting) return;

    this.errorVisible = false;
    this.successVisible = false;

    // Validations
    if (this.captchaInput.trim() !== this.captchaCode) {
      this.errorMessage = 'Code de vérification incorrect.';
      this.errorVisible = true;
      this.refreshCaptcha();
      this.captchaInput = '';
      return;
    }
    if (!this.isValidEmail()) {
      this.errorMessage = 'Veuillez saisir une adresse e-mail valide.';
      this.errorVisible = true;
      return;
    }
    if (!this.isValidPassword()) {
      this.errorMessage = 'Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre.';
      this.errorVisible = true;
      return;
    }

    const cleanEmail = this.login.trim().toLowerCase();
    this.isSubmitting = true;

    /* ═══════════════════════════════════════════════
       FILET DE SÉCURITÉ ABSOLU (navigateur/extension)
       Si RxJS timeout ne suffit pas, ce timer natif
       débloquera le bouton après 20 secondes MAXIMUM.
       ═══════════════════════════════════════════════ */
    const safetyTimer = setTimeout(() => {
      if (this.isSubmitting) {
        console.warn('🛡️ Safety timeout déclenché — déblocage forcé');
        this.isSubmitting = false;
        this.errorMessage = 'Le serveur ne répond pas. Vérifiez votre connexion ou désactivez vos extensions.';
        this.errorVisible = true;
        this.cdr.detectChanges(); // force la mise à jour du bouton
      }
    }, this.SAFETY_TIMEOUT);

    this.http.post(`${environment.apiUrl}/api/login`, {
      email: cleanEmail,
      password: this.password
    }).pipe(
      // 1. Timeout RxJS
      timeout(this.HTTP_TIMEOUT),

      // 2. catchError AVANT finalize — intercepte et STOPPE l'erreur
      catchError(err => {
        clearTimeout(safetyTimer);
        console.error('🔴 Erreur login:', err);

        if (err.name === 'TimeoutError') {
          this.errorMessage = '⏱️ Le serveur met trop de temps à répondre.';
        } else if (err.status === 0) {
          this.errorMessage = '❌ Impossible de joindre le serveur (CORS / réseau / extension bloquante).';
        } else {
          this.errorMessage = err.error?.error || err.error?.message || 'Identifiants incorrects.';
        }

        this.errorVisible = true;
        this.refreshCaptcha();
        this.captchaInput = '';

        // ⛔ EMPTY = on arrête l'erreur ici. Elle n'atteindra PLUS le subscribe.
        return EMPTY;
      }),

      // 3. Nettoyage si le composant est détruit
      takeUntil(this.destroy$),

      // 4. finalize = exécuté TOUJOURS, même après catchError
      finalize(() => {
        clearTimeout(safetyTimer);
        this.isSubmitting = false;
        this.cdr.detectChanges(); // force Angular à rafraîchir le bouton
      })
    ).subscribe({
      next: (response: any) => {
        if (!response?.user_id) {
          this.errorMessage = 'Réponse du serveur invalide.';
          this.errorVisible = true;
          return;
        }

        this.pendingUserId = response.user_id;
        this.emailDisplay = this.maskEmail(cleanEmail);
        this.otpStep = true;
        this.otpCode = '';
        this.errorVisible = false;
        this.startTimer();

        this.successMessage = '📨 Un code de vérification a été envoyé par e-mail.';
        this.successVisible = true;
        setTimeout(() => this.successVisible = false, 4000);
      },
      // Filet supplémentaire (ne devrait jamais être appelé avec EMPTY)
      error: () => {
        clearTimeout(safetyTimer);
        this.isSubmitting = false;
        this.cdr.detectChanges();
      }
    });
  }

  // ===== VÉRIFICATION OTP ÉTAPE 2 =====
  validerOtp(): void {
    if (this.isVerifying) return;
    if (this.otpCode.trim().length !== 6) {
      this.errorMessage = 'Le code doit contenir exactement 6 chiffres.';
      this.errorVisible = true;
      return;
    }

    this.isVerifying = true;
    this.errorVisible = false;

    const safetyTimer = setTimeout(() => {
      if (this.isVerifying) {
        this.isVerifying = false;
        this.errorMessage = 'Le serveur ne répond pas.';
        this.errorVisible = true;
        this.cdr.detectChanges();
      }
    }, this.SAFETY_TIMEOUT);

    this.http.post(`${environment.apiUrl}/api/verify-otp`, {
      user_id: this.pendingUserId,
      code: this.otpCode.trim()
    }).pipe(
      timeout(this.HTTP_TIMEOUT),
      catchError(err => {
        clearTimeout(safetyTimer);
        if (err.name === 'TimeoutError') {
          this.errorMessage = '⏱️ Délai dépassé.';
        } else if (err.status === 0) {
          this.errorMessage = '❌ Problème de connexion.';
        } else {
          this.errorMessage = err.error?.error || err.error?.message || 'Code incorrect ou expiré.';
        }
        this.errorVisible = true;
        this.otpCode = '';
        return EMPTY;
      }),
      takeUntil(this.destroy$),
      finalize(() => {
        clearTimeout(safetyTimer);
        this.isVerifying = false;
        this.cdr.detectChanges();
      })
    ).subscribe({
      next: (response: any) => {
        localStorage.setItem('token', response.token);
        localStorage.setItem('user', JSON.stringify(response.user));
        this.stopTimer();
        this.redirectByRole(response.user?.role);
      },
      error: () => {
        clearTimeout(safetyTimer);
        this.isVerifying = false;
        this.cdr.detectChanges();
      }
    });
  }

  // ===== RENVOYER OTP =====
  renvoyerEmail(): void {
    if (this.timer > 0 || this.isResending) return;

    this.isResending = true;
    this.errorVisible = false;

    const safetyTimer = setTimeout(() => {
      if (this.isResending) {
        this.isResending = false;
        this.errorMessage = 'Le serveur ne répond pas.';
        this.errorVisible = true;
        this.cdr.detectChanges();
      }
    }, this.SAFETY_TIMEOUT);

    this.http.post(`${environment.apiUrl}/api/resend-email`, {
      user_id: this.pendingUserId,
      email: this.login.trim().toLowerCase()
    }).pipe(
      timeout(this.HTTP_TIMEOUT),
      catchError(err => {
        clearTimeout(safetyTimer);
        if (err.name === 'TimeoutError') {
          this.errorMessage = '⏱️ Délai dépassé.';
        } else if (err.status === 0) {
          this.errorMessage = '❌ Problème de connexion.';
        } else {
          this.errorMessage = err.error?.error || err.error?.message || "Erreur lors de l'envoi.";
        }
        this.errorVisible = true;
        return EMPTY;
      }),
      takeUntil(this.destroy$),
      finalize(() => {
        clearTimeout(safetyTimer);
        this.isResending = false;
        this.cdr.detectChanges();
      })
    ).subscribe({
      next: () => {
        this.successMessage = '📨 Un nouveau code a été envoyé.';
        this.successVisible = true;
        this.otpCode = '';
        this.startTimer();
        setTimeout(() => this.successVisible = false, 4000);
      },
      error: () => {
        clearTimeout(safetyTimer);
        this.isResending = false;
        this.cdr.detectChanges();
      }
    });
  }

  startTimer(): void {
    this.timer = 300;
    this.stopTimer();
    this.timerInterval = setInterval(() => {
      this.timer--;
      if (this.timer <= 0) {
        this.stopTimer();
        this.errorMessage = '⏰ Le code a expiré. Veuillez renvoyer un nouveau code.';
        this.errorVisible = true;
      }
    }, 1000);
  }

  stopTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  retournerConnexion(): void {
    this.otpStep = false;
    this.otpCode = '';
    this.pendingUserId = null;
    this.stopTimer();
    this.errorVisible = false;
    this.successVisible = false;
    this.refreshCaptcha();
    this.captchaInput = '';
  }

  private redirectByRole(role: string | undefined): void {
    switch (role) {
      case 'etudiant':
      case 'student':
        this.router.navigate(['/dashboard-etudiant']);
        break;
      case 'enseignant':
      case 'teacher':
        this.router.navigate(['/dashboard-enseignant']);
        break;
      default:
        this.router.navigate(['/dashboard']);
        break;
    }
  }
}