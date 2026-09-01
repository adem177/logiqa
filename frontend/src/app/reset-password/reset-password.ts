import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './reset-password.html',
  styleUrls: ['./reset-password.css']
})
export class ResetPasswordComponent implements OnInit {
  resetForm: FormGroup;
  token: string = '';
  userId: string = '';
  message: string = '';
  errorMessage: string = '';
  loading: boolean = false;

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.resetForm = this.fb.group({
      password: ['', [Validators.required, Validators.minLength(8)]]
    });
  }

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.token = params['token'] || '';
      this.userId = params['user_id'] || '';
    });
  }

  onSubmit() {
    if (this.resetForm.invalid || !this.token || !this.userId) return;

    this.loading = true;
    this.message = '';
    this.errorMessage = '';

    const payload = {
      user_id: this.userId,
      token: this.token,
      password: this.resetForm.value.password
    };

    this.http.post('http://localhost:3000/api/reset-password', payload)
      .subscribe({
        next: (res: any) => {
          this.message = res.message;
          this.loading = false;
          setTimeout(() => this.router.navigate(['/login']), 2000);
        },
        error: (err) => {
          this.errorMessage = err.error?.error || 'Une erreur est survenue.';
          this.loading = false;
        }
      });
  }
}