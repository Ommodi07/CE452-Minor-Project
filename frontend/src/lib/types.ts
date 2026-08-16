export type SubQuestionStatus = "pending" | "in_progress" | "answered" | "failed";
export type ResearchAngle =
  | "factual"
  | "current_status"
  | "causal"
  | "comparative"
  | "risk_controversy"
  | "stakeholder"
  | "forecast";
export type ResearchMethod = "web_search" | "api" | "both";
export type SourceType = "news" | "academic" | "primary" | "blog" | "gov" | "other";
export type VerificationStatus = "corroborated" | "disputed" | "unverified";
export type GraphStatus =
  | "planning"
  | "researching"
  | "critiquing"
  | "writing"
  | "done"
  | "error"
  | "created";

export interface SubQuestion {
  id: string;
  parent_query: string;
  question_text: string;
  rationale: string;
  angle: ResearchAngle;
  research_method: ResearchMethod;
  priority: number;
  status: SubQuestionStatus;
  refined_query?: string | null;
}

export interface SourceDoc {
  id: string;
  sub_question_id: string;
  url: string;
  title: string;
  snippet: string;
  retrieved_at: string;
  source_type: SourceType;
  credibility_score?: number | null;
  content_ref?: string | null;
  author?: string | null;
  published_date?: string | null;
  quality_flags: string[];
}

export interface Claim {
  id: string;
  source_doc_id: string;
  sub_question_id: string;
  claim_text: string;
  confidence: number;
  supporting_excerpt: string;
}

export interface VerifiedClaim extends Claim {
  verification_status: VerificationStatus;
  corroborating_source_ids: string[];
  contradicting_source_ids: string[];
  critic_notes: string;
  adjusted_confidence: number;
}

export interface ReportSection {
  heading: string;
  content: string;
  cited_claim_ids: string[];
}

export interface Report {
  id: string;
  session_id: string;
  title: string;
  executive_summary: string;
  sections: ReportSection[];
  citations: Record<string, SourceDoc>;
  limitations: string[];
  generated_at: string;
  markdown: string;
}

export interface ResearchRequest {
  query: string;
  session_id?: string | null;
  max_iterations?: number | null;
}

export interface ResearchResponse {
  session_id: string;
  status: GraphStatus;
  report: Report | null;
  open_questions: string[];
  errors: string[];
}

export interface SessionCreateResponse {
  session_id: string;
}

export interface GraphState {
  session_id: string;
  original_query?: string;
  sub_questions?: SubQuestion[];
  source_docs?: SourceDoc[];
  claims?: Claim[];
  verified_claims?: VerifiedClaim[];
  critic_feedback?: string[];
  open_questions?: string[];
  iteration_count?: number;
  max_iterations?: number;
  status?: GraphStatus;
  errors?: string[];
  report?: Report | null;
}

export interface SessionResponse {
  session_id: string;
  state: GraphState;
}

export interface HealthResponse {
  status: string;
  app: string;
}

export interface ApiEndpointStatus {
  method: string;
  path: string;
  description: string;
  active: boolean;
}

export interface ConnectionStatus {
  name: string;
  active: boolean;
  configured: boolean;
  details: string;
}

export interface StatusResponse {
  app_name: string;
  environment: string;
  endpoints: ApiEndpointStatus[];
  connections: ConnectionStatus[];
  overall_ok: boolean;
}

export interface ApiError {
  detail: string;
}
