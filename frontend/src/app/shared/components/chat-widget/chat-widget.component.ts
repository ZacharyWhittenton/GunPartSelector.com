import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

interface QuickFaqEntry {
  question: string;
}

const QUICK_FAQ_ENTRIES: QuickFaqEntry[] = [
  { question: 'What is GunPartSelector.com?' },
  { question: 'Do you sell parts directly?' },
  { question: 'How does compatibility checking work?' },
  { question: 'Can I save or share a build?' },
  { question: 'Where does my order actually go?' },
  { question: 'Do you ship firearms or regulated parts?' }
];

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './chat-widget.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './chat-widget.component.css'
})
export class ChatWidgetComponent {
  readonly isOpen = signal(false);
  readonly quickFaqEntries = QUICK_FAQ_ENTRIES;

  toggle(): void {
    this.isOpen.update(open => !open);
  }
}
