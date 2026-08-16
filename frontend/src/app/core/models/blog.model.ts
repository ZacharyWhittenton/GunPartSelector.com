export type PostStatus = 'draft' | 'published';

export interface BlogPostSummary {
  id: string;
  title: string;
  slug: string;
  excerpt: string;
  coverImageUrl: string | null;
  tags: string[];
  authorName: string;
  status: PostStatus;
  publishedAt: string | null;
  createdAt: string;
}

export interface BlogPostDetail extends BlogPostSummary {
  body: string;
  updatedAt: string;
}

export interface BlogComment {
  id: string;
  authorId: string;
  authorName: string;
  body: string;
  createdAt: string;
}
