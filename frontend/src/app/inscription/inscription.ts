import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

type Role = 'etudiant' | 'enseignant';

@Component({
  selector: 'app-inscription',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './inscription.html',
  styleUrls: ['./inscription.css']
})
export class InscriptionComponent {
  // Rôle
  role = signal<Role>('etudiant');

  // Champs
  nom = '';
  prenom = '';
  email = '';
  telephone = '';
  password = '';
  confirmPassword = '';
  acceptTerms = false;

  // États
  errorVisible = false;
  errorMessage = '';
  successVisible = false;
  isSubmitting = false;
  showPassword = false;

  // Validation
  fieldErrors = {
    nom: '',
    prenom: '',
    email: '',
    password: '',
    confirmPassword: ''
  };

  touched = {
    nom: false,
    prenom: false,
    email: false,
    password: false,
    confirmPassword: false
  };

  constructor(private http: HttpClient, private router: Router) {}

  // --- Rôle ---
  setRole(r: Role) {
    this.role.set(r);
  }

  // --- Formatage téléphone ---
  formatPhoneNumber() {
    let cleaned = this.telephone.replace(/\D/g, '');
    if (cleaned.length > 8) {
      cleaned = cleaned.slice(0, 8);
    }
    if (cleaned.length > 2) {
      cleaned = cleaned.slice(0, 2) + ' ' + cleaned.slice(2);
    }
    if (cleaned.length > 6) {
      cleaned = cleaned.slice(0, 6) + ' ' + cleaned.slice(6);
    }
    this.telephone = cleaned;
  }

  // --- Force du mot de passe ---
  getPasswordStrength(): number {
    let score = 0;
    if (this.password.length >= 8) score += 33;
    if (/[A-Za-z]/.test(this.password)) score += 33;
    if (/\d/.test(this.password)) score += 34;
    return Math.min(score, 100);
  }

  getPasswordStrengthText(): string {
    const strength = this.getPasswordStrength();
    if (strength <= 33) return 'Faible';
    if (strength <= 66) return 'Moyen';
    return 'Fort';
  }

  // --- Validations ---
  validateNom() {
    this.touched.nom = true;
    this.fieldErrors.nom = this.nom.trim().length < 2
      ? 'Le nom doit contenir au moins 2 caractères.'
      : '';
  }

  validatePrenom() {
    this.touched.prenom = true;
    this.fieldErrors.prenom = this.prenom.trim().length < 2
      ? 'Le prénom doit contenir au moins 2 caractères.'
      : '';
  }

  validateEmail() {
    this.touched.email = true;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    this.fieldErrors.email = !emailRegex.test(this.email)
      ? 'Adresse email invalide.'
      : '';
  }

  validatePassword() {
    this.touched.password = true;
    const hasLetter = /[A-Za-z]/.test(this.password);
    const hasDigit = /\d/.test(this.password);

    if (this.password.length < 8) {
      this.fieldErrors.password = 'Le mot de passe doit contenir au moins 8 caractères.';
    } else if (!hasLetter) {
      this.fieldErrors.password = 'Le mot de passe doit contenir au moins une lettre.';
    } else if (!hasDigit) {
      this.fieldErrors.password = 'Le mot de passe doit contenir au moins un chiffre.';
    } else {
      this.fieldErrors.password = '';
    }

    if (this.touched.confirmPassword) {
      this.validateConfirmPassword();
    }
  }

  validateConfirmPassword() {
    this.touched.confirmPassword = true;
    this.fieldErrors.confirmPassword = this.confirmPassword !== this.password
      ? 'Les mots de passe ne correspondent pas.'
      : '';
  }

  // ─── VALIDATION GLOBALE : méthode normale (PAS computed) ───
  isFormValid(): boolean {
    const hasLetter = /[A-Za-z]/.test(this.password);
    const hasDigit = /\d/.test(this.password);

    return (
      this.nom.trim().length >= 2 &&
      this.prenom.trim().length >= 2 &&
      /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.email) &&
      this.password.length >= 8 &&
      hasLetter &&
      hasDigit &&
      this.confirmPassword === this.password &&
      this.confirmPassword !== '' &&   // ← évite que '' === '' soit valide
      this.acceptTerms
    );
  }

  // --- Erreurs ---
  private showError(msg: string) {
    this.errorMessage = msg;
    this.errorVisible = true;
    this.successVisible = false;
  }

  // --- Inscription ---
  validerInscription() {
    // Force les validations visuelles
    this.validateNom();
    this.validatePrenom();
    this.validateEmail();
    this.validatePassword();
    this.validateConfirmPassword();

    this.errorVisible = false;

    // Vérifications finales
    if (!this.isFormValid()) {
      this.showError('Veuillez remplir correctement tous les champs obligatoires.');
      return;
    }

    this.isSubmitting = true;

    // Envoi des données
    const formData = {
      nom: this.nom.trim(),
      prenom: this.prenom.trim(),
      email: this.email.toLowerCase().trim(),
      password: this.password,
      telephone: this.telephone ? '+216' + this.telephone.replace(/\s/g, '') : '',
      role: this.role()
    };

    this.http.post('http://localhost:3000/api/register', formData)
      .subscribe({
        next: () => {
          this.successVisible = true;
          this.isSubmitting = false;
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 1500);
        },
        error: (err) => {
          this.showError(err.error?.error || 'Erreur lors de la création du compte.');
          this.isSubmitting = false;
        }
      });
  }
}