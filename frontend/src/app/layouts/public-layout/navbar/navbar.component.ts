import { Component, ChangeDetectionStrategy, HostListener, inject, signal } from '@angular/core';
import { NavigationStart, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';
import { CartService } from '../../../core/services/cart.service';

export type NavDropdown = 'guides' | 'company' | null;

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './navbar.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './navbar.component.css'
})
export class NavbarComponent {
  private readonly authService = inject(AuthService);
  private readonly cartService = inject(CartService);
  private readonly router = inject(Router);

  readonly currentUser = this.authService.currentUser;
  readonly cartItemCount = this.cartService.itemCount;
  readonly openDropdown = signal<NavDropdown>(null);

  mobileMenuOpen = false;
  mobileGroupOpen: NavDropdown = null;

  constructor() {
    this.router.events
      .pipe(
        filter((event): event is NavigationStart => event instanceof NavigationStart),
        takeUntilDestroyed()
      )
      .subscribe(() => {
        this.closeMenu();
        this.openDropdown.set(null);
      });
  }

  toggleDropdown(dropdown: NavDropdown): void {
    this.openDropdown.set(this.openDropdown() === dropdown ? null : dropdown);
  }

  closeDropdown(): void {
    this.openDropdown.set(null);
  }

  toggleMobileGroup(dropdown: NavDropdown): void {
    this.mobileGroupOpen = this.mobileGroupOpen === dropdown ? null : dropdown;
  }

  toggleMenu(): void {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  closeMenu(): void {
    this.mobileMenuOpen = false;
    this.mobileGroupOpen = null;
  }

  @HostListener('document:keydown.escape')
  closeOnEscape(): void {
    this.closeMenu();
    this.closeDropdown();
  }

  @HostListener('document:click', ['$event'])
  closeOnOutsideClick(event: MouseEvent): void {
    if (this.openDropdown() === null) return;
    const target = event.target as HTMLElement;
    if (!target.closest('[data-nav-dropdown]')) {
      this.closeDropdown();
    }
  }

  logout(): void {
    this.authService.logout();
    this.closeMenu();
    this.router.navigateByUrl('/');
  }
}
