import { Component, inject } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

interface StatCard {
  icon: string;
  iconClass: string;
  value: string;
  title: string;
  sub: string;
  subMuted?: boolean;
}

interface Course {
  id: number;
  title: string;
  studentsCount: number;
  thumbnail: string;
}

interface ActivityItem {
  id: number;
  text: string;
  date: string;
}

@Component({
  selector: 'app-teacher-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './enseignant.html',
  styleUrls: ['./enseignant.css']
})
export class TeacherDashboardComponent {
  private router = inject(Router);

  teacherName = 'Adem';
  completionRate = 0; // 0-100

  stats: StatCard[] = [
    {
      icon: '📘',
      iconClass: 'icon-blue',
      value: '0',
      title: 'Cours publiés',
      sub: 'Aucun pour le moment'
    },
    {
      icon: '👥',
      iconClass: 'icon-purple',
      value: '0',
      title: 'Étudiants inscrits',
      sub: 'Commencez à enseigner'
    },
    {
      icon: '⏱️',
      iconClass: 'icon-amber',
      value: '0',
      title: 'Heures enseignées',
      sub: 'Aucune donnée'
    },
    {
      icon: '⭐',
      iconClass: 'icon-green',
      value: '—',
      title: 'Note moyenne',
      sub: 'Pas encore évalué',
      subMuted: true
    }
  ];

  // Remplacer par un appel à un service (HTTP) qui récupère les vrais cours
  courses: Course[] = [];

  // Remplacer par un appel à un service qui récupère l'activité réelle
  activities: ActivityItem[] = [];

  get progressStrokeDeg(): number {
    return (this.completionRate / 100) * 360;
  }

  // Redirection vers le formulaire d'upload de cours
  onCreateCourse(): void {
    this.router.navigate(['/enseignant/upload-cours']);
  }

  // Redirection vers l'accueil ou la liste générale
  goHome(): void {
    this.router.navigate(['/']);
  }
}