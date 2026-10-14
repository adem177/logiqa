import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { QuizService, Quiz, QuizQuestion, QuizCorrection } from '../services/quiz.service';

@Component({
  selector: 'app-quiz',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './quiz.html'
})
export class QuizComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private quizService = inject(QuizService);

  quiz = signal<Quiz | null>(null);
  questions = signal<QuizQuestion[]>([]);
  currentQuestionIndex = signal(0);
  answers = signal<Map<number, number>>(new Map());
  showResult = signal(false);
  score = signal(0);
  totalQuestions = signal(0);
  loading = signal(true);
  error = signal<string | null>(null);
  correction = signal<Record<number, QuizCorrection> | null>(null);
  showCorrection = signal(false);
  regenerating = signal(false);

  currentQuestion = computed<QuizQuestion | null>(
    () => this.questions()[this.currentQuestionIndex()] || null
  );

  progress = computed(() => {
    if (this.totalQuestions() === 0) return 0;
    return Math.round((this.answers().size / this.totalQuestions()) * 100);
  });

  correctionList = computed(() => {
    const corr = this.correction();
    if (!corr) return [];
    return Object.entries(corr).map(([qId, c]) => ({
      questionId: Number(qId),
      ...c
    }));
  });

  ngOnInit(): void {
    const quizId = this.route.snapshot.paramMap.get('id');
    if (quizId) {
      this.loadQuiz(Number(quizId));
    } else {
      this.error.set('Quiz non spécifié.');
      this.loading.set(false);
    }
  }

  private loadQuiz(quizId: number): void {
    this.resetQuizState();
    this.loading.set(true);
    this.quizService.getQuiz(quizId).subscribe({
      next: (quiz) => {
        this.quiz.set(quiz);
        this.questions.set(quiz.questions || []);
        this.totalQuestions.set(quiz.nombre_questions);
        this.loading.set(false);
        this.regenerating.set(false);
      },
      error: (err) => {
        const status = err.status;
        const message = err.error?.error || 'Erreur lors du chargement du quiz.';
        if (status === 410) {
          this.error.set(`⏰ ${message}`);
        } else {
          this.error.set(message);
        }
        this.loading.set(false);
        this.regenerating.set(false);
      }
    });
  }

  selectOption(questionId: number, optionId: number): void {
    const newAnswers = new Map(this.answers());
    newAnswers.set(questionId, optionId);
    this.answers.set(newAnswers);
  }

  isSelected(questionId: number, optionId: number): boolean {
    return this.answers().get(questionId) === optionId;
  }

  nextQuestion(): void {
    if (this.currentQuestionIndex() < this.questions().length - 1) {
      this.currentQuestionIndex.update(i => i + 1);
    }
  }

  prevQuestion(): void {
    if (this.currentQuestionIndex() > 0) {
      this.currentQuestionIndex.update(i => i - 1);
    }
  }

  submitQuiz(): void {
    if (this.answers().size < this.totalQuestions()) {
      if (!confirm(`Vous avez répondu à ${this.answers().size}/${this.totalQuestions()} questions. Soumettre quand même ?`)) {
        return;
      }
    }

    const reponses = Array.from(this.answers().entries()).map(([question_id, option_id]) => ({
      question_id,
      option_id
    }));

    this.quizService.soumettreQuiz(this.quiz()!.id, reponses).subscribe({
      next: (result) => {
        this.score.set(result.score);
        this.totalQuestions.set(result.total);
        this.correction.set(result.correction || null);
        this.showResult.set(true);
      },
      error: (err) => {
        const status = err.status;
        const message = err.error?.error || 'Erreur lors de la soumission.';
        if (status === 410) {
          this.error.set(`⏰ ${message}`);
        } else {
          this.error.set(message);
        }
      }
    });
  }

  private resetQuizState(): void {
    this.answers.set(new Map());
    this.currentQuestionIndex.set(0);
    this.showResult.set(false);
    this.score.set(0);
    this.correction.set(null);
    this.showCorrection.set(false);
    this.error.set(null);
  }

  retryQuiz(): void {
    this.answers.set(new Map());
    this.currentQuestionIndex.set(0);
    this.showResult.set(false);
    this.score.set(0);
    this.correction.set(null);
    this.showCorrection.set(false);
  }

  newQuiz(): void {
    const currentQuizId = this.quiz()?.id;
    if (!currentQuizId) return;

    this.resetQuizState();
    this.regenerating.set(true);
    this.loading.set(true);
    this.quizService.regenererQuiz(currentQuizId).subscribe({
      next: (result) => {
        this.loadQuiz(result.new_quiz_id);
      },
      error: (err) => {
        this.error.set(err.error?.error || 'Erreur lors de la génération du nouveau quiz.');
        this.regenerating.set(false);
        this.loading.set(false);
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/cours']);
  }

  toggleCorrection(): void {
    this.showCorrection.update(v => !v);
  }

  isCorrectAnswer(questionId: number, optionId: number): boolean {
    const corr = this.correction();
    if (!corr || !corr[questionId]) return false;
    const opt = corr[questionId].options.find(o => o.option_id === optionId);
    return opt?.est_correcte ?? false;
  }

  isStudentAnswer(questionId: number, optionId: number): boolean {
    return this.answers().get(questionId) === optionId;
  }

  getCorrectionStatus(questionId: number): 'correct' | 'incorrect' | 'unanswered' | null {
    const corr = this.correction();
    if (!corr || !corr[questionId]) return null;
    const studentAnswer = corr[questionId].reponse_etudiant;
    if (studentAnswer === null) return 'unanswered';
    const correctOption = corr[questionId].options.find(o => o.est_correcte);
    if (correctOption && studentAnswer === correctOption.option_id) return 'correct';
    return 'incorrect';
  }
}
