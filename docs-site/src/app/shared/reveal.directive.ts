import { Directive, ElementRef, OnDestroy, OnInit, inject, input } from '@angular/core';

/** Añade animación de aparición cuando el elemento entra en el viewport. */
@Directive({ selector: '[appReveal]' })
export class RevealDirective implements OnInit, OnDestroy {
  /** Retardo escalonado en ms (para efectos en cascada). */
  readonly delay = input(0);

  private readonly el = inject(ElementRef<HTMLElement>);
  private observer?: IntersectionObserver;

  ngOnInit(): void {
    const native = this.el.nativeElement;
    native.classList.add('reveal');
    if (this.delay() > 0) {
      native.style.transitionDelay = `${this.delay()}ms`;
    }
    this.observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            this.observer?.disconnect();
          }
        }
      },
      { threshold: 0.12 },
    );
    this.observer.observe(native);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}
