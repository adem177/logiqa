// app.routes.ts

import { Routes } from '@angular/router';
import { HomeComponent } from './features/home/home';
import { LoginComponent } from './login/login';
import { InscriptionComponent } from './inscription/inscription';
import { TeacherDashboardComponent } from './dashboard-enseignant/enseignant';
import { CoursesComponent } from './cours/cours';
import { CoursContentComponent } from './matiere/matiere';
import { EnseignantUploadComponent } from './upload_enseignant/enseignant-upload';
import { ForgotPasswordComponent } from './motdepasse/forgot-password'; // ← Import Mot de passe oublié
import { ResetPasswordComponent } from './reset-password/reset-password'; // ← Import Réinitialisation
import { AboutComponent } from './about-us/about-us'; // ← Import About us

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'inscription', component: InscriptionComponent },
  { path: 'forgot-password', component: ForgotPasswordComponent }, // ← Route mot de passe oublié
  { path: 'reset-password', component: ResetPasswordComponent },   // ← Route nouveau mot de passe
  { path: 'dashboard-enseignant', component: TeacherDashboardComponent },
  { path: 'matiere', component: CoursContentComponent }, 
  { path: 'cours', component: CoursesComponent },
  { path: 'enseignant/upload-cours', component: EnseignantUploadComponent },
  { path: 'cours/:id', component: CoursContentComponent },
  { path: 'about-us', component: AboutComponent }, // ← Route About us
  { path: '**', redirectTo: '' }
];