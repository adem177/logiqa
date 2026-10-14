import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { Auth } from '../core/auth';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(Auth);
  const router = inject(Router);
  const token = auth.getToken();

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error) => {
      if (
        error.status === 401 &&
        !req.url.includes('/api/login') &&
        !req.url.includes('/api/verify-otp')
      ) {
        auth.clearSession();
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
