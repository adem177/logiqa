import { Component, EventEmitter, Output } from '@angular/core';

/**
 * Fenêtre de confirmation « Se déconnecter ? » (boutons Oui / Non)
 * affichée avant toute déconnexion déclenchée par un clic sur le logo.
 * Le composant parent décide : (confirmed) → déconnexion, (cancelled) → fermeture.
 */
@Component({
  selector: 'app-logout-confirm',
  standalone: true,
  template: `
    <div
      class="fixed inset-0 z-[70] flex items-center justify-center bg-[#101828]/45 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="logoutConfirmTitle"
      tabindex="-1"
      (click)="onOverlayClick($event)"
      (keydown.escape)="cancelled.emit()">
      <div class="w-full max-w-[380px] rounded-2xl border border-[#edeff5] bg-white p-6 shadow-[0_24px_60px_-20px_rgba(16,24,40,0.4)]">
        <div class="mb-4 grid h-12 w-12 place-items-center rounded-xl bg-[#fef3f2] text-[#f04438]">
          <i class="bi bi-box-arrow-right text-[21px]" aria-hidden="true"></i>
        </div>
        <h2 id="logoutConfirmTitle" class="text-[17px] font-extrabold text-[#101828]">
          Se déconnecter ?
        </h2>
        <p class="mt-1.5 text-[13.5px] leading-relaxed text-[#667085]">
          Voulez-vous vous déconnecter de LOGIQA ?
        </p>
        <div class="mt-5 flex gap-3">
          <button type="button" class="ui-btn flex-1" (click)="confirmed.emit()">Oui</button>
          <button type="button" class="ui-btn ui-btn--ghost flex-1" (click)="cancelled.emit()">Non</button>
        </div>
      </div>
    </div>
  `
})
export class LogoutConfirmComponent {
  /** L'utilisateur confirme : le parent lance la déconnexion. */
  @Output() confirmed = new EventEmitter<void>();
  /** L'utilisateur renonce : fermeture de la fenêtre. */
  @Output() cancelled = new EventEmitter<void>();

  /** Clic sur le fond sombre = « Non ». */
  onOverlayClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.cancelled.emit();
    }
  }
}
