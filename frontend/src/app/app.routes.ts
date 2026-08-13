// app.routes.ts

import { Routes } from '@angular/router';
import { HomeComponent } from './features/home/home';
import { LoginComponent } from './login/login';
import { InscriptionComponent } from './inscription/inscription';
import { Dashboard } from './dashboard-etudiant/dashboard';
import { TeacherDashboardComponent } from './dashboard-enseignant/enseignant';
import { CoursesComponent } from './cours/cours';
import { CoursContentComponent } from './matiere/matiere_python'; // ← nouveau chemin
import { EnseignantUploadComponent } from './upload_enseignant/enseignant-upload'; // ← Nouveau composant d'upload
export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'inscription', component: InscriptionComponent },
  { path: 'dashboard', component: Dashboard },
  { path: 'dashboard-etudiant', component: Dashboard },
  { path: 'dashboard-enseignant', component: TeacherDashboardComponent },
  { path: 'cours', component: CoursesComponent },
  { path: 'enseignant/upload-cours', component: EnseignantUploadComponent },
  { path: 'cours/:id', component: CoursContentComponent }, // ← /cours/1 = Python, /cours/2 = Algèbre
  { path: '**', redirectTo: '' }
];