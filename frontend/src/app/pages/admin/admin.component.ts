import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, finalize } from 'rxjs';

import { AccountNote, AdminUserSummary } from '../../core/models/admin.model';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [FormsModule, DatePipe, RouterLink],
  templateUrl: './admin.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);

  readonly currentUserId = this.authService.currentUser()?.id ?? null;

  readonly users = signal<AdminUserSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly rowErrors = signal<Record<string, string>>({});
  readonly pendingUserIds = signal<Set<string>>(new Set());

  readonly selectedUserId = signal<string | null>(null);
  readonly notes = signal<AccountNote[]>([]);
  readonly notesLoading = signal(false);
  readonly isAddingNote = signal(false);
  newNoteBody = '';

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.adminService
      .listUsers()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: users => this.users.set(users),
        error: () => this.errorMessage.set('Unable to load accounts. Please try again.')
      });
  }

  toggleRole(user: AdminUserSummary): void {
    const nextRole = user.role === 'admin' ? 'customer' : 'admin';
    this.runUserAction(user.id, () =>
      this.adminService.updateRole(user.id, nextRole)
    );
  }

  toggleStatus(user: AdminUserSummary): void {
    const nextStatus = user.status === 'active' ? 'suspended' : 'active';
    this.runUserAction(user.id, () =>
      this.adminService.updateStatus(user.id, nextStatus)
    );
  }

  toggleNotesPanel(user: AdminUserSummary): void {
    if (this.selectedUserId() === user.id) {
      this.selectedUserId.set(null);
      return;
    }

    this.selectedUserId.set(user.id);
    this.newNoteBody = '';
    this.notesLoading.set(true);

    this.adminService
      .listNotes(user.id)
      .pipe(finalize(() => this.notesLoading.set(false)))
      .subscribe({
        next: notes => this.notes.set(notes),
        error: () => this.setRowError(user.id, 'Unable to load notes.')
      });
  }

  submitNote(userId: string): void {
    const body = this.newNoteBody.trim();
    if (!body) {
      return;
    }

    this.isAddingNote.set(true);

    this.adminService
      .addNote(userId, body)
      .pipe(finalize(() => this.isAddingNote.set(false)))
      .subscribe({
        next: note => {
          this.notes.update(existing => [note, ...existing]);
          this.newNoteBody = '';
        },
        error: () => this.setRowError(userId, 'Unable to add note.')
      });
  }

  isPending(userId: string): boolean {
    return this.pendingUserIds().has(userId);
  }

  rowError(userId: string): string {
    return this.rowErrors()[userId] ?? '';
  }

  private runUserAction(userId: string, action: () => Observable<AdminUserSummary>): void {
    this.setRowError(userId, '');
    this.pendingUserIds.update(pending => new Set(pending).add(userId));

    action()
      .pipe(
        finalize(() => {
          this.pendingUserIds.update(pending => {
            const next = new Set(pending);
            next.delete(userId);
            return next;
          });
        })
      )
      .subscribe({
        next: updated => {
          this.users.update(users =>
            users.map(user => (user.id === updated.id ? updated : user))
          );
        },
        error: error => {
          this.setRowError(
            userId,
            error.status === 400
              ? 'You cannot change your own account.'
              : 'That action failed. Please try again.'
          );
        }
      });
  }

  private setRowError(userId: string, message: string): void {
    this.rowErrors.update(errors => ({ ...errors, [userId]: message }));
  }
}
