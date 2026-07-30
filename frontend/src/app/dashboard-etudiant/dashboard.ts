import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface Cours {
  id: string;
  title: string;
  category: string;
  progress: number;
  color: string;
  nextLesson: string;
}

interface Activity {
  id: string;
  text: string;
  time: string;
  icon: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.html',      // ← vérifie ce nom aussi
  styleUrls: ['./dashboard.css']        // ← doit matcher le vrai fichier
})
export class Dashboard {
  userName = signal('Adem');

  // Nouveau compte : tout démarre à zéro
  stats = signal([
    { label: 'Cours en cours', value: 0, icon: '📘', trend: 'Aucun pour le moment' },
    { label: 'Heures étudiées', value: 0, icon: '⏱️', trend: 'Commencez à apprendre' },
    { label: 'Certificats', value: 0, icon: '🏆', trend: 'Aucun obtenu' },
    { label: 'Score moyen', value: 0, icon: '📊', trend: '—', suffix: '%' },
  ]);

  courses = signal<Cours[]>([]);
  activities = signal<Activity[]>([]);

  overallProgress = computed(() => {
    const list = this.courses();
    if (!list.length) return 0;
    return Math.round(list.reduce((sum, c) => sum + c.progress, 0) / list.length);
  });
}