import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { QuizService } from '../services/quiz.service';
import { COURSES_DETAILS, CourseDetail, Chapter } from '../data/course-data';

@Component({
  selector: 'app-generer-quiz',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './generer-quiz.html',
  styleUrls: ['./generer-quiz.css']
})
export class GenererQuizComponent implements OnInit {
  private router = inject(Router);
  private quizService = inject(QuizService);

  courses = signal<CourseDetail[]>([]);
  selectedCourse = signal<CourseDetail | null>(null);
  selectedChapter = signal<Chapter | null>(null);
  nombreQuestions = signal(10); // 10 questions par défaut
  methode = signal<'groq'>('groq');
  generating = signal(false);
  successMessage = signal<string | null>(null);
  errorMessage = signal<string | null>(null);

  ngOnInit(): void {
    this.courses.set(COURSES_DETAILS);
  }

  selectCourse(course: CourseDetail): void {
    this.selectedCourse.set(course);
    this.selectedChapter.set(null);
    this.successMessage.set(null);
    this.errorMessage.set(null);
  }

  selectChapter(chapter: Chapter): void {
    this.selectedChapter.set(chapter);
    this.successMessage.set(null);
    this.errorMessage.set(null);
  }

  setMethode(m: 'groq'): void {
    this.methode.set(m);
  }

  generateQuiz(): void {
    if (!this.selectedChapter()) return;

    this.generating.set(true);
    this.successMessage.set(null);
    this.errorMessage.set(null);

    this.quizService.genererQuiz(
      this.selectedChapter()!.id,
      this.nombreQuestions(),
      this.methode()
    ).subscribe({
      next: (result) => {
        this.generating.set(false);
        this.successMessage.set(
          `Quiz "${result.titre}" généré avec succès ! ${result.nombre_questions} questions créées.`
        );
        // Réinitialiser la sélection
        this.selectedChapter.set(null);
      },
      error: (err) => {
        this.generating.set(false);
        this.errorMessage.set(err.error?.error || 'Erreur lors de la génération du quiz.');
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/dashboard-enseignant']);
  }
}
