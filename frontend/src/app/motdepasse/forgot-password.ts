import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './forgot-password.html'
})
export class ForgotPasswordComponent {
  forgotForm: FormGroup;
  // Signaux : garantissent le rendu après un subscribe (mode zoneless)
  message = signal('');
  errorMessage = signal('');
  loading = signal(false);

  constructor(private fb: FormBuilder, private http: HttpClient) {
    this.forgotForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]]
    });
  }

  onSubmit() {
    if (this.forgotForm.invalid) return;

    this.loading.set(true);
    this.message.set('');
    this.errorMessage.set('');

    // Port 3000 au lieu de 5000 pour correspondre à Flask
    this.http.post('http://localhost:3000/api/forgot-password', this.forgotForm.value)
      .subscribe({
        next: (res: any) => {
          this.message.set(res.message);
          this.loading.set(false);
        },
        error: (err) => {
          this.errorMessage.set(err.error?.error || 'Une erreur est survenue.');
          this.loading.set(false);
        }
      });
  }
}