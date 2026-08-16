export type CatalogSection = 'upper' | 'lower' | 'stock' | 'optics' | 'accessories';

export type StockStatus = 'in_stock' | 'out_of_stock' | 'unknown';

export type ProductSort = 'price_asc' | 'price_desc' | 'name_asc' | 'newest';

export interface PartCategory {
  id: string;
  slug: string;
  name: string;
  section: CatalogSection;
  productCount: number;
}

export interface ProductSummary {
  id: string;
  categoryId: string;
  brand: string;
  name: string;
  slug: string;
  priceCents: number;
  weightOz: number;
  imageUrl: string | null;
  stockStatus: StockStatus;
  attributeTags: string[];
}

export interface ProductDetail extends ProductSummary {
  sku: string | null;
  description: string;
  affiliateUrl: string;
  affiliateRetailerName: string | null;
}

export interface ProductFacets {
  brands: string[];
  attributeTagGroups: Record<string, string[]>;
  priceMinCents: number;
  priceMaxCents: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductQuery {
  category?: string;
  brand?: string[];
  priceMin?: number;
  priceMax?: number;
  stock?: StockStatus;
  tag?: string[];
  sort?: ProductSort;
  limit?: number;
  offset?: number;
}
