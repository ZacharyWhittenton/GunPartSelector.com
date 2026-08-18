import { AfterViewInit, Directive, ElementRef, OnDestroy, inject } from '@angular/core';

/**
 * Fades and slides an element in the first time it scrolls into view.
 * Mirrors the reveal-on-scroll feel used across the reference design
 * (roeeby.com) without pulling in an animation library for it.
 */
@Directive({
  selector: '[appScrollReveal]',
  standalone: true,
  host: {
    class: 'scroll-reveal'
  }
})
export class ScrollRevealDirective implements AfterViewInit, OnDestroy {
  private readonly elementRef = inject(ElementRef<HTMLElement>);
  private observer?: IntersectionObserver;

  ngAfterViewInit(): void {
    const element = this.elementRef.nativeElement;

    if (typeof IntersectionObserver === 'undefined' || matchMedia('(prefers-reduced-motion: reduce)').matches) {
      element.classList.add('scroll-reveal--visible');
      return;
    }

    this.observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            element.classList.add('scroll-reveal--visible');
            this.observer?.unobserve(element);
          }
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' }
    );
    this.observer.observe(element);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}
