import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { BlogPostDetail, BlogPostSummary } from '../models/blog.model';

export interface PostWritePayload {
  title: string;
  excerpt: string;
  body: string;
  tags: string[];
  coverImageUrl: string | null;
}

export interface ImageUploadResponse {
  url: string;
}

@Injectable({
  providedIn: 'root'
})
export class BlogAdminService {
  constructor(private readonly http: HttpClient) {}

  listAllPosts(): Observable<BlogPostSummary[]> {
    return this.http.get<BlogPostSummary[]>('/api/admin/blog/posts');
  }

  createPost(payload: PostWritePayload): Observable<BlogPostDetail> {
    return this.http.post<BlogPostDetail>('/api/admin/blog/posts', payload);
  }

  updatePost(id: string, payload: PostWritePayload): Observable<BlogPostDetail> {
    return this.http.patch<BlogPostDetail>(`/api/admin/blog/posts/${id}`, payload);
  }

  publishPost(id: string): Observable<BlogPostDetail> {
    return this.http.post<BlogPostDetail>(`/api/admin/blog/posts/${id}/publish`, {});
  }

  unpublishPost(id: string): Observable<BlogPostDetail> {
    return this.http.post<BlogPostDetail>(`/api/admin/blog/posts/${id}/unpublish`, {});
  }

  deletePost(id: string): Observable<void> {
    return this.http.delete<void>(`/api/admin/blog/posts/${id}`);
  }

  uploadImage(file: File): Observable<ImageUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImageUploadResponse>('/api/admin/blog/images', formData);
  }
}
