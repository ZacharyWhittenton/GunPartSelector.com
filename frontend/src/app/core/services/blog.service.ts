import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { BlogComment, BlogPostDetail, BlogPostSummary } from '../models/blog.model';

@Injectable({
  providedIn: 'root'
})
export class BlogService {
  constructor(private readonly http: HttpClient) {}

  listPosts(tag?: string): Observable<BlogPostSummary[]> {
    const params = tag ? new HttpParams().set('tag', tag) : undefined;
    return this.http.get<BlogPostSummary[]>('/api/blog/posts', { params });
  }

  getPost(slug: string): Observable<BlogPostDetail> {
    return this.http.get<BlogPostDetail>(`/api/blog/posts/${slug}`);
  }

  listComments(slug: string): Observable<BlogComment[]> {
    return this.http.get<BlogComment[]>(`/api/blog/posts/${slug}/comments`);
  }

  addComment(slug: string, body: string): Observable<BlogComment> {
    return this.http.post<BlogComment>(`/api/blog/posts/${slug}/comments`, { body });
  }

  deleteComment(commentId: string): Observable<void> {
    return this.http.delete<void>(`/api/blog/comments/${commentId}`);
  }

  listTags(): Observable<string[]> {
    return this.http.get<string[]>('/api/blog/tags');
  }

  listSubscriptions(): Observable<string[]> {
    return this.http.get<string[]>('/api/blog/subscriptions');
  }

  subscribeToTag(tagName: string): Observable<void> {
    return this.http.post<void>(`/api/blog/tags/${encodeURIComponent(tagName)}/subscribe`, {});
  }

  unsubscribeFromTag(tagName: string): Observable<void> {
    return this.http.delete<void>(`/api/blog/tags/${encodeURIComponent(tagName)}/subscribe`);
  }
}
