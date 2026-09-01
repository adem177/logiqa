import { Component, inject, computed, ElementRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { CourseService } from '../services/course.service';

interface StatCard {
  icon: string;
  iconClass: string;
  value: string;
  title: string;
  sub: string;
  subMuted?: boolean;
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
  private courseService = inject(CourseService);
  private elementRef = inject(ElementRef);

  teacherName = 'Adem';
  teacherLastName = 'Ben Ali';
  teacherEmail = 'adem.benali@example.com';
  teacherId = 1;

  isProfileOpen = false;

  get teacherInitials(): string {
    const firstInitial = this.teacherName ? this.teacherName[0] : '';
    const lastInitial = this.teacherLastName ? this.teacherLastName[0] : '';
    return (firstInitial + lastInitial).toUpperCase();
  }

  toggleProfile(event?: MouseEvent): void {
    if (event) {
      event.stopPropagation();
    }
    this.isProfileOpen = !this.isProfileOpen;
  }

  closeProfile(): void {
    this.isProfileOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    // Ferme le menu de profil uniquement si le clic a lieu hors du composant
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isProfileOpen = false;
    }
  }

  courses = computed(() => this.courseService.getCoursesByTeacher(this.teacherId));
  teachersCount = 25;

  stats = computed<StatCard[]>(() => {
    const myCourses = this.courses();

    return [
      {
        icon: '📘',
        iconClass: 'icon-blue',
        value: String(myCourses.length),
        title: 'Cours publiés',
        sub: myCourses.length === 0 ? 'Aucun pour le moment' : `${myCourses.length} cours actif(s)`
      },
      {
        icon: '🧑‍🏫',
        iconClass: 'icon-purple',
        value: String(this.teachersCount),
        title: 'Enseignants',
        sub: `${this.teachersCount} sur la plateforme`
      }
    ];
  });

  activities: ActivityItem[] = [];

  onCreateCourse(): void {
    this.router.navigate(['/enseignant/upload-cours']);
  }

  goHome(): void {
    this.router.navigate(['/']);
  }
}