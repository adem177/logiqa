import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './forgot-password.html',
  styleUrls: ['./forgot-password.css']
})
export class ForgotPasswordComponent {
  forgotForm: FormGroup;
  message: string = '';
  errorMessage: string = '';
  loading: boolean = false;

  constructor(private fb: FormBuilder, private http: HttpClient) {
    this.forgotForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]]
    });
  }

  onSubmit() {
    if (this.forgotForm.invalid) return;

    this.loading = true;
    this.message = '';
    this.errorMessage = '';

    // Port 3000 au lieu de 5000 pour correspondre à Flask
    this.http.post('http://localhost:3000/api/forgot-password', this.forgotForm.value)
      .subscribe({
        next: (res: any) => {
          this.message = res.message;
          this.loading = false;
        },
        error: (err) => {
          this.errorMessage = err.error?.error || 'Une erreur est survenue.';
          this.loading = false;
        }
      });
  }
}