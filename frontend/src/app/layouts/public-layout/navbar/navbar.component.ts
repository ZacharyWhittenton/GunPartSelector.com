import { Component, ChangeDetectionStrategy, HostListener, inject, signal } from '@angular/core';

import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive
} from '@angular/router';

import { DOCUMENT } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';
import { CartService } from '../../../core/services/cart.service';



@Component({

  selector: 'app-navbar',

  standalone: true,

  imports: [

    RouterLink,

    RouterLinkActive

  ],

  templateUrl:

    './navbar.component.html',

  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl:

    './navbar.component.css'

})
export class NavbarComponent {

  private readonly authService = inject(AuthService);
  private readonly cartService = inject(CartService);
  private readonly router = inject(Router);
  private readonly document = inject(DOCUMENT);

  readonly currentUser = this.authService.currentUser;
  readonly cartItemCount = this.cartService.itemCount;
  readonly isHome = signal(this.isHomeRoute(this.router.url));
  readonly isScrolled = signal(false);


  mobileMenuOpen = false;

  constructor() {
    this.onWindowScroll();
    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed()
      )
      .subscribe(event => {
        this.isHome.set(this.isHomeRoute(event.urlAfterRedirects));
        this.closeMenu();
        this.onWindowScroll();
      });
  }

  @HostListener('window:scroll')
  onWindowScroll(scrollY = this.document.defaultView?.scrollY ?? 0): void {
    this.isScrolled.set(scrollY > 24);
  }

  isTransparent(): boolean {
    return this.isHome() && !this.isScrolled() && !this.mobileMenuOpen;
  }



  toggleMenu(): void {

    this.mobileMenuOpen =
      !this.mobileMenuOpen;

  }



  closeMenu(): void {

    this.mobileMenuOpen =
      false;

  }


  @HostListener('document:keydown.escape')
  closeMenuWithEscape(): void {
    this.closeMenu();
  }



  logout(): void {

    this.authService.logout();

    this.closeMenu();

    this.router.navigateByUrl('/');

  }

  private isHomeRoute(url: string): boolean {
    return url.split(/[?#]/, 1)[0] === '/';
  }


}
