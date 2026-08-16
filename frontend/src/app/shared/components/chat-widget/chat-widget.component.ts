import { ChangeDetectionStrategy, Component, ElementRef, inject, signal, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';

import { ChatTurn } from '../../../core/models/chat.model';
import { AuthService } from '../../../core/services/auth.service';
import { ChatService } from '../../../core/services/chat.service';

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './chat-widget.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './chat-widget.component.css'
})
export class ChatWidgetComponent {
  private readonly chatService = inject(ChatService);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  @ViewChild('scrollAnchor') private scrollAnchor?: ElementRef<HTMLDivElement>;

  readonly currentUser = this.authService.currentUser;

  readonly isOpen = signal(false);
  readonly messages = signal<ChatTurn[]>([]);
  readonly isSending = signal(false);
  readonly errorMessage = signal('');
  draftMessage = '';

  toggle(): void {
    this.isOpen.update(open => !open);
  }

  get greeting(): string {
    const user = this.currentUser();
    return user
      ? `Hi ${user.fullName.split(' ')[0]}, how can I help?`
      : 'Ask me about our services, or how to get started.';
  }

  send(): void {
    const content = this.draftMessage.trim();
    if (!content || this.isSending()) {
      return;
    }

    this.errorMessage.set('');
    this.messages.update(existing => [...existing, { role: 'user', content }]);
    this.draftMessage = '';
    this.isSending.set(true);

    this.chatService
      .sendMessage(this.messages(), this.router.url)
      .pipe(finalize(() => this.isSending.set(false)))
      .subscribe({
        next: response => {
          this.messages.update(existing => [
            ...existing,
            { role: 'assistant', content: response.message }
          ]);
          this.scrollToBottom();
        },
        error: error => {
          this.errorMessage.set(
            error.status === 503
              ? 'The assistant is not set up yet. Add an Anthropic API key to backend/.env to enable it.'
              : 'Something went wrong. Please try again.'
          );
        }
      });
  }

  private scrollToBottom(): void {
    queueMicrotask(() => {
      this.scrollAnchor?.nativeElement.scrollIntoView({ behavior: 'smooth' });
    });
  }
}
