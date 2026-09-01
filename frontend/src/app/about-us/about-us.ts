import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-about',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './about-us.html',
  styleUrls: ['./about-us.css']
})
export class AboutComponent {
  valeurs = [
    {
      icone: '🎯',
      titre: 'Notre mission',
      description: 'Rendre l\'éducation accessible à tous en connectant étudiants, enseignants et administrations sur une seule plateforme simple et sécurisée.'
    },
    {
      icone: '🤝',
      titre: 'Nos valeurs',
      description: 'Confiance, simplicité et innovation guident chacune de nos décisions pour accompagner votre réussite académique.'
    }
  ];
}