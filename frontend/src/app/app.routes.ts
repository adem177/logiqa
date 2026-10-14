// app.routes.ts

import { Routes } from '@angular/router';
import { HomeComponent } from './features/home/home';
import { LoginComponent } from './login/login';
import { InscriptionComponent } from './inscription/inscription';
import { TeacherDashboardComponent } from './dashboard-enseignant/enseignant';
import { CoursesComponent } from './cours/cours';
import { CoursContentComponent } from './matiere/matiere';
import { EnseignantUploadComponent } from './upload_enseignant/enseignant-upload';
import { ForgotPasswordComponent } from './motdepasse/forgot-password';
import { ResetPasswordComponent } from './reset-password/reset-password';
import { AboutComponent } from './about-us/about-us';
import { QuizComponent } from './quiz/quiz';
import { GenererQuizComponent } from './generer-quiz/generer-quiz';
import { AdminDashboardComponent } from './dashboard-admin/dashboard-admin';
import { ProfilComponent } from './profil/profil';
import { authGuard, roleGuard } from './core/auth-guard';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'inscription', component: InscriptionComponent },
  { path: 'forgot-password', component: ForgotPasswordComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  { path: 'dashboard-enseignant', component: TeacherDashboardComponent, canActivate: [roleGuard(['enseignant', 'admin'])] },
  { path: 'dashboard-admin', component: AdminDashboardComponent, canActivate: [roleGuard(['admin'])] },
  { path: 'matiere', component: CoursContentComponent, canActivate: [authGuard] }, 
  { path: 'cours', component: CoursesComponent, canActivate: [authGuard] },
  { path: 'enseignant/upload-cours', component: EnseignantUploadComponent, canActivate: [roleGuard(['enseignant', 'admin'])] },
  { path: 'cours/:id', component: CoursContentComponent, canActivate: [authGuard] },
  { path: 'about-us', component: AboutComponent },
  { path: 'profil', component: ProfilComponent, canActivate: [authGuard] },
  { path: 'quiz/:id', component: QuizComponent, canActivate: [authGuard] },
  { path: 'generer-quiz', component: GenererQuizComponent, canActivate: [roleGuard(['enseignant', 'admin'])] },
  { path: '**', redirectTo: '' }
];