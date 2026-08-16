import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { BlogComment, BlogPostDetail } from '../../../core/models/blog.model';
import { AuthService } from '../../../core/services/auth.service';
import { BlogService } from '../../../core/services/blog.service';
import { SeoService } from '../../../core/services/seo.service';

@Component({
  selector: 'app-blog-post-detail',
  standalone: true,
  imports: [DatePipe, RouterLink, FormsModule],
  templateUrl: './blog-post-detail.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './blog-post-detail.component.css'
})
export class BlogPostDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly blogService = inject(BlogService);
  private readonly authService = inject(AuthService);
  private readonly seoService = inject(SeoService);

  readonly currentUser = this.authService.currentUser;

  readonly post = signal<BlogPostDetail | null>(null);
  readonly notFound = signal(false);
  readonly isLoading = signal(true);

  readonly comments = signal<BlogComment[]>([]);
  readonly commentsLoading = signal(false);
  readonly isSubmittingComment = signal(false);
  readonly commentError = signal('');
  newCommentBody = '';

  readonly subscribedTags = signal<Set<string>>(new Set());
  readonly pendingTags = signal<Set<string>>(new Set());

  private slug = '';

  ngOnInit(): void {
    this.slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.loadPost();

    if (this.currentUser()) {
      this.blogService.listSubscriptions().subscribe({
        next: tags => this.subscribedTags.set(new Set(tags))
      });
    }
  }

  submitComment(): void {
    const body = this.newCommentBody.trim();
    if (!body) {
      return;
    }

    this.commentError.set('');
    this.isSubmittingComment.set(true);

    this.blogService
      .addComment(this.slug, body)
      .pipe(finalize(() => this.isSubmittingComment.set(false)))
      .subscribe({
        next: comment => {
          this.comments.update(existing => [...existing, comment]);
          this.newCommentBody = '';
        },
        error: () => this.commentError.set('Unable to post comment. Please try again.')
      });
  }

  deleteComment(commentId: string): void {
    this.blogService.deleteComment(commentId).subscribe({
      next: () =>
        this.comments.update(existing => existing.filter(comment => comment.id !== commentId))
    });
  }

  canDeleteComment(comment: BlogComment): boolean {
    const user = this.currentUser();
    if (!user) {
      return false;
    }
    return user.id === comment.authorId || user.role === 'admin';
  }

  isSubscribed(tag: string): boolean {
    return this.subscribedTags().has(tag);
  }

  isTagPending(tag: string): boolean {
    return this.pendingTags().has(tag);
  }

  toggleSubscription(tag: string): void {
    if (!this.currentUser()) {
      return;
    }

    this.pendingTags.update(pending => new Set(pending).add(tag));
    const action$ = this.isSubscribed(tag)
      ? this.blogService.unsubscribeFromTag(tag)
      : this.blogService.subscribeToTag(tag);

    action$
      .pipe(
        finalize(() => {
          this.pendingTags.update(pending => {
            const next = new Set(pending);
            next.delete(tag);
            return next;
          });
        })
      )
      .subscribe({
        next: () => {
          this.subscribedTags.update(tags => {
            const next = new Set(tags);
            if (next.has(tag)) {
              next.delete(tag);
            } else {
              next.add(tag);
            }
            return next;
          });
        }
      });
  }

  private loadPost(): void {
    this.isLoading.set(true);

    this.blogService
      .getPost(this.slug)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: post => {
          this.post.set(post);
          this.seoService.updatePage(
            `${post.title} | WD Web Solutions`,
            post.excerpt,
            post.coverImageUrl ?? undefined
          );
          this.loadComments();
        },
        error: () => this.notFound.set(true)
      });
  }

  private loadComments(): void {
    this.commentsLoading.set(true);

    this.blogService
      .listComments(this.slug)
      .pipe(finalize(() => this.commentsLoading.set(false)))
      .subscribe({
        next: comments => this.comments.set(comments)
      });
  }
}
