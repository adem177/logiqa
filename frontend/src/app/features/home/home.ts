import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './home.html',
  styleUrls: ['./home.css']
})
export class HomeComponent {
  currentSlide = 0;

  slides = [
    {
      title: 'LOGIQA',
      subtitle: 'La plateforme E-Learning qui connecte étudiants, enseignants et administrations',
      description: 'Un espace pédagogique unique, simple et sécurisé',
      detail: 'Profitez du meilleur contenu pédagogique et de la plus grande bibliothèque numérique pour vous accompagner tout au long de votre parcours.', 
    }
  ];

  nextSlide() {
    this.currentSlide = (this.currentSlide + 1) % this.slides.length;
  }

  prevSlide() {
    this.currentSlide = (this.currentSlide - 1 + this.slides.length) % this.slides.length;
  }
}