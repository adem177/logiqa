import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CoursService, Cours } from './cours.service';

@Component({
  selector: 'app-cours',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cours.html',
  styleUrls: ['./cours.css']
})
export class CoursComponent implements OnInit {
  coursList: Cours[] = [];
  loading = false;
  errorMessage = '';

  // État du formulaire (utilisé pour créer ET modifier)
  showForm = false;
  isEditMode = false;
  formModel: Cours = this.emptyCours();

  constructor(private coursService: CoursService) {}

  ngOnInit(): void {
    this.loadCours();
  }

  private emptyCours(): Cours {
    return { titre: '', description: '', categorie: '', niveau: 'Débutant' };
  }

  loadCours(): void {
    this.loading = true;
    this.coursService.getAll().subscribe({
      next: (data) => {
        this.coursList = data;
        this.loading = false;
      },
      error: () => {
        this.errorMessage = "Impossible de charger les cours.";
        this.loading = false;
      }
    });
  }

  openCreateForm(): void {
    this.isEditMode = false;
    this.formModel = this.emptyCours();
    this.showForm = true;
  }

  openEditForm(cours: Cours): void {
    this.isEditMode = true;
    this.formModel = { ...cours };
    this.showForm = true;
  }

  cancelForm(): void {
    this.showForm = false;
    this.formModel = this.emptyCours();
  }

  submitForm(): void {
    if (!this.formModel.titre || !this.formModel.description) {
      this.errorMessage = 'Veuillez remplir au moins le titre et la description.';
      return;
    }

    if (this.isEditMode && this.formModel.id) {
      this.coursService.update(this.formModel.id, this.formModel).subscribe({
        next: (updated) => {
          const index = this.coursList.findIndex(c => c.id === updated.id);
          if (index !== -1) this.coursList[index] = updated;
          this.cancelForm();
        },
        error: () => this.errorMessage = "Erreur lors de la modification du cours."
      });
    } else {
      this.coursService.create(this.formModel).subscribe({
        next: (created) => {
          this.coursList.push(created);
          this.cancelForm();
        },
        error: () => this.errorMessage = "Erreur lors de la création du cours."
      });
    }
  }

  deleteCours(cours: Cours): void {
    if (!cours.id) return;
    const confirmed = confirm(`Supprimer le cours "${cours.titre}" ?`);
    if (!confirmed) return;

    this.coursService.delete(cours.id).subscribe({
      next: () => {
        this.coursList = this.coursList.filter(c => c.id !== cours.id);
      },
      error: () => this.errorMessage = "Erreur lors de la suppression du cours."
    });
  }
}
