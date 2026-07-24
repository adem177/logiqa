import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

type Role = 'etudiant' | 'enseignant' | 'administration';

@Component({
  selector: 'app-inscription',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './inscription.html',
  styleUrls: ['./inscription.css']
})
export class InscriptionComponent {
  role = signal<Role>('etudiant');

  nom = '';
  prenom = '';
  email = '';
  telephone = '';
  password = '';
  confirmPassword = '';
  acceptTerms = false;

  errorVisible = false;
  errorMessage = '';
  successVisible = false;

  // ===== Validation en temps réel =====
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

  setRole(r: Role) {
    this.role.set(r);
  }

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
    this.fieldErrors.password = this.password.length < 6
      ? 'Le mot de passe doit contenir au moins 6 caractères.'
      : '';
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

  isFormValid = computed(() => {
    return (
      this.nom.trim().length >= 2 &&
      this.prenom.trim().length >= 2 &&
      /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.email) &&
      this.password.length >= 6 &&
      this.confirmPassword === this.password &&
      this.acceptTerms
    );
  });

  private showError(msg: string) {
    this.errorMessage = msg;
    this.errorVisible = true;
    this.successVisible = false;
  }

  validerInscription() {
    // Force l'affichage de toutes les erreurs si soumis directement
    this.validateNom();
    this.validatePrenom();
    this.validateEmail();
    this.validatePassword();
    this.validateConfirmPassword();

    this.errorVisible = false;

    if (!this.nom || !this.prenom || !this.email || !this.password) {
      this.showError('Veuillez remplir tous les champs obligatoires.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.email)) {
      this.showError('Adresse email invalide.');
      return;
    }

    if (this.password.length < 6) {
      this.showError('Le mot de passe doit contenir au moins 6 caractères.');
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.showError('Les mots de passe ne correspondent pas.');
      return;
    }

    if (!this.acceptTerms) {
      this.showError("Veuillez accepter les conditions d'utilisation.");
      return;
    }

    this.http.post('http://localhost:3000/api/register', {
      nom: this.nom,
      prenom: this.prenom,
      email: this.email,
      password: this.password,
      telephone: this.telephone,
      role: this.role()
    }).subscribe({
      next: () => {
        this.successVisible = true;
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 1500);
      },
      error: (err) => {
        this.showError(err.error?.error || 'Erreur lors de la création du compte.');
      }
    });
  }
}