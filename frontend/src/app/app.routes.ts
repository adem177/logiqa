import { Routes } from '@angular/router';
import { HomeComponent } from './features/home/home';
import { LoginComponent } from './login/login';
import { InscriptionComponent } from './inscription/inscription';
import { Dashboard } from './dashboard-etudiant/dashboard';
import { TeacherDashboardComponent } from './dashboard-enseignant/enseignant';
import { CoursComponent } from './cours/cours';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'login', component: LoginComponent },
  { path: 'inscription', component: InscriptionComponent },

  // Ancienne route générique, gardée pour compatibilité si utilisée ailleurs
  { path: 'dashboard', component: Dashboard },

  // Nouvelles routes séparées par rôle
  { path: 'dashboard-etudiant', component: Dashboard },
  { path: 'dashboard-enseignant', component: TeacherDashboardComponent },

  // Page catalogue de cours (étudiant)
  { path: 'cours', component: CoursComponent },

  { path: '**', redirectTo: '' }
];