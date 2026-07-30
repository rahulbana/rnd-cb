export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface NerTag {
  text: string;
  type: string;
}

export interface Source {
  title: string;
  url?: string | null;
  type: string;
  snippet?: string | null;
}

export interface Article {
  id: string;
  user_id: string;
  prompt: string | null;
  title: string;
  body: string;
  summary: string;
  seo_description: string;
  keywords: string[];
  sentiment: string;
  tags: string[];
  ner_tags: NerTag[];
  sources: Source[];
  banner_image: string | null;
  trace_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StyleReference {
  id: string;
  name: string;
  source_type: "file" | "link";
  origin: string;
  char_count: number;
  created_at: string;
}

export interface ArticleListItem {
  id: string;
  title: string;
  summary: string;
  sentiment: string;
  tags: string[];
  banner_image: string | null;
  status: string;
  updated_at: string;
}

export interface SearchResult {
  article: ArticleListItem;
  score: number;
}

export interface GeneratedContent {
  title: string;
  body: string;
  summary: string;
  seo_description: string;
  keywords: string[];
  sentiment: string;
  tags: string[];
  ner_tags: NerTag[];
  sources: Source[];
}

export interface DuplicateHit {
  article_id: string;
  title: string;
  distance: number;
}

export interface GenerationResponse {
  content: GeneratedContent;
  context_used: string[];
  possible_duplicates: DuplicateHit[];
  research_queries: string[];
  trace_id: string | null;
}

export interface GenerationRequest {
  prompt: string;
  tone?: string;
  audience?: string;
  length?: string;
  keywords?: string[];
  use_rag?: boolean;
  use_web_search?: boolean;
  research_depth?: string;
}

export type ArticleUpsert = Partial<
  Omit<Article, "id" | "user_id" | "created_at" | "updated_at">
>;
