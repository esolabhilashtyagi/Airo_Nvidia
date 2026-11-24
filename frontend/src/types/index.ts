export type UserRole = 'candidate' | 'content_manager' | 'administrator';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  candidate_profile_id?: string;
}

export interface IndustryCategory {
  id: string;
  name: string;
  description?: string;
}

export interface JobRole {
  id: string;
  industry_id: string;
  title: string;
  description?: string;
  experience_level: string;
  is_active: boolean;
}

export interface Industry {
  id: string;
  name: string;
  slug: string;
  description?: string;
  icon?: string;
  is_active: boolean;
  categories: IndustryCategory[];
  job_roles: JobRole[];
}

export interface Education {
  id?: string;
  degree: string;
  field_of_study: string;
  institution: string;
  start_year?: number;
  end_year?: number;
  grade?: string;
  is_current: boolean;
}

export interface Experience {
  id?: string;
  company_name: string;
  job_title: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  description?: string;
}

export interface TargetCompany {
  company_name: string;
  target_role?: string;
}

export interface CandidateProfile {
  id: string;
  user_id: string;
  candidate_type?: 'working_professional' | 'student_fresher';
  sub_category?: string;
  industry_id?: string;
  industry?: Industry;
  current_company?: string;
  current_role?: string;
  target_role?: string;
  total_experience_months: number;
  relevant_experience_months: number;
  employment_status?: string;
  key_skills: string[];
  career_goals?: string;
  onboarding_completed: boolean;
  onboarding_step: number;
  interview_rounds_preferred: string[];
  interaction_preference: 'text' | 'voice';
  interview_readiness_score: number;
  education_history: Education[];
  experience_history: Experience[];
  target_companies: { id: string; target_role?: string; company?: { name: string } | null }[];
}

export interface ResumeSuggestion {
  id: string;
  resume_analysis_id: string;
  category: string;
  original_text?: string;
  suggested_text: string;
  reason?: string;
  supporting_context?: string;
  status: 'pending' | 'accepted' | 'rejected';
}

export interface ResumeAnalysis {
  id: string;
  resume_id: string;
  overall_score: number;
  status: 'processing' | 'analysis_completed' | 'analysis_failed';
  category_scores: Record<string, number>;
  completeness_score: number;
  skills_relevance_score: number;
  experience_quality_score: number;
  target_role_alignment_score: number;
  formatting_score: number;
  strengths: string[];
  weaknesses: string[];
  summary_analysis?: string;
  missing_keywords: string[];
  improvement_opportunities: string[];
  suggestions: ResumeSuggestion[];
  extraction_confidence: number;
  analysis_provider?: string;
  created_at: string;
}

export interface ResumeATSReview {
  id: string;
  resume_id: string;
  job_title: string;
  ats_score: number;
  keyword_match_score: number;
  section_match_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  matched_sections: string[];
  missing_sections: string[];
  formatting_warnings: string[];
  created_at: string;
}

export interface ResumeVersion {
  id: string;
  resume_id: string;
  version_number: number;
  content: Record<string, unknown>;
  change_summary?: string;
  created_at: string;
}

export interface ResumeParsedData {
  contact_info: Record<string, unknown>;
  skills: string[];
  skill_categories: Record<string, string[]>;
  education: Record<string, unknown>[];
  experience: Record<string, unknown>[];
  projects: string[];
  certifications: string[];
  publications: string[];
  awards: string[];
  languages: string[];
  accepted_suggestions?: Record<string, unknown>[];
  [key: string]: unknown;
}

export interface Resume {
  id: string;
  candidate_profile_id: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  sha256_hash: string;
  parsing_status: string;
  analysis_status: string;
  extraction_confidence: number;
  extraction_error?: string;
  analysis_error?: string;
  parsed_data: ResumeParsedData;
  created_at: string;
  updated_at: string;
  latest_analysis?: ResumeAnalysis;
}

export interface ResumeDetail extends Resume {
  raw_text?: string;
  versions: ResumeVersion[];
}

export interface QuestionOption {
  id: string;
  text: string;
  is_correct?: boolean;
}

export interface Question {
  id: string;
  question_text: string;
  question_type: string;
  industry_id: string;
  job_role_id?: string;
  subject: string;
  topic: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  interview_round: string;
  options: QuestionOption[];
  expected_answer?: string;
  explanation?: string;
  tags: string[];
  is_bookmarked: boolean;
  source_provenance: 'source_verified' | 'source_formatted' | 'ai_generated' | 'editorially_reviewed';
  approval_status: string;
  workflow_status?: 'draft' | 'pending_review' | 'approved' | 'published' | 'rejected' | 'archived' | 'superseded';
  version_number?: number;
  root_question_id?: string | null;
  industry?: { name: string };
  job_role?: { title: string };
}

export interface CompanyInterviewQuestion {
  id: string;
  company_name: string;
  job_role: string;
  round_number: number;
  interview_round: string;
  question_text: string;
  category: string;
  difficulty: string;
  source_platform: string;
  original_url?: string;
  confidence_score: number;
  verification_status: string;
  skills_tested: string[];
  solution_approach?: string;
  code_template?: string;
}

export interface CompanySummary {
  name: string;
  question_count: number;
  industry: string;
  roles: string[];
  rounds_covered: string[];
}

export interface RoundBlueprint {
  round_number: number;
  round_name: string;
  round_type: string;
  weightage_percent: number;
  focus_areas: string[];
  sample_topics: string[];
  preparation_tips: string;
  typical_duration_minutes: number;
}

export interface CompanyBlueprint {
  company_name: string;
  target_role: string;
  seniority_tier: string;
  total_rounds: number;
  hiring_philosophy: string;
  rounds: RoundBlueprint[];
}

export interface DynamicDorks {
  company: string;
  role: string;
  seniority_tier: string;
  skills: string[];
  round_dorks: Record<string, string[] | string | { name?: string; dork_query?: string; competencies?: string[] }>;
  platform_queries: Record<string, string>;
}

export interface SynthesizedRoundQuestion {
  round_number: number;
  interview_round: string;
  company: string;
  role: string;
  question_text: string;
  category: string;
  difficulty: string;
  skills_tested: string[];
  solution_approach?: string;
  source_platform: string;
  confidence_score: number;
  verification_status: string;
}

export interface Lesson {
  id: string;
  module_id: string;
  title: string;
  content: string;
  duration_minutes: number;
  order_index: number;
  is_archived?: boolean;
}

export interface Module {
  id: string;
  industry_id: string;
  title: string;
  description: string;
  difficulty: string;
  duration_minutes: number;
  order_index: number;
  is_published: boolean;
  is_archived?: boolean;
  lessons: Lesson[];
  job_role_ids?: string[];
  skill_ids?: string[];
  completed_lesson_ids: string[];
  progress_status: 'not_started' | 'in_progress' | 'completed';
  completion_percentage: number;
}

export interface QuestionPracticeResult {
  question_id: string;
  is_correct?: boolean | null;
  score_percentage?: number | null;
  evaluation_status: 'evaluated' | 'unavailable';
  evaluation_provenance: 'deterministic' | 'ai' | 'none';
  expected_answer: string;
  explanation?: string;
  feedback: string;
}

export interface QuestionPracticeHistory {
  id: string;
  question_id: string;
  question_text: string;
  question_type: string;
  user_response: string;
  is_correct?: boolean | null;
  score_percentage?: number | null;
  evaluation_status: 'evaluated' | 'unavailable';
  evaluation_provenance: 'deterministic' | 'ai' | 'none';
  feedback?: string | null;
  created_at: string;
}

export interface RoadmapTask {
  id: string;
  roadmap_id: string;
  title: string;
  description?: string;
  module_id?: string | null;
  order_index: number;
  is_completed: boolean;
}

export interface Roadmap {
  id: string;
  candidate_profile_id: string;
  title: string;
  description?: string;
  status: string;
  tasks: RoadmapTask[];
}

export interface AssessmentAttempt {
  id: string;
  assessment_id: string;
  assessment_title: string;
  started_at: string;
  completed_at?: string;
  status: string;
  percentage?: number | null;
  passed?: boolean | null;
  evaluation_status?: string;
}

export interface AssessmentResult {
  id: string;
  assessment_attempt_id: string;
  total_score: number;
  max_score: number;
  percentage: number | null;
  passed: boolean | null;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  topic_breakdown: Record<string, { correct: number; total: number }>;
  difficulty_breakdown: Record<string, { correct: number; total: number }>;
  strong_areas: string[];
  weak_areas: string[];
  recommendations?: string;
  evaluation_status: 'evaluated' | 'partial' | 'unavailable' | 'legacy_unverified';
  evaluation_provenance: string;
  question_feedback: Array<{
    question_id: string;
    topic: string;
    question_type: string;
    status: string;
    provenance?: string;
    marks_awarded: number | null;
    max_marks: number;
    feedback?: string;
    missing_concepts?: string[];
    rubric_breakdown?: Record<string, number>;
    expected_answer?: string;
    explanation?: string;
    candidate_answer?: string | string[];
  }>;
  time_spent_seconds: number;
  completed_at?: string;
}

export interface MockInterviewSession {
  id: string;
  job_role: string;
  target_company?: string;
  interview_round: string;
  difficulty: string;
  mode: string;
  status: string;
  current_question_index: number;
  total_questions: number;
  interviewer_message: string;
  current_question_id?: string;
  history: { q: string; a: string }[];
}

export interface InterviewReport {
  id: string;
  mock_interview_id: string;
  overall_score: number;
  technical_score: number;
  domain_score: number;
  communication_score: number;
  structure_score: number;
  key_strengths: string[];
  improvement_areas: string[];
  detailed_feedback: {
    summary?: string;
    readiness_verdict?: string;
  };
  question_evaluations: {
    question_number: number;
    score: number;
    positive_points: string;
    missed_points: string;
    model_answer_summary: string;
  }[];
  completed_at?: string;
}

export interface DashboardOverview {
  candidate_name: string;
  target_role?: string;
  industry_name?: string;
  interview_readiness_score: number;
  readiness_factors: Record<string, string>;
  metrics: {
    title: string;
    value: string | number;
    change_text?: string;
    change_type?: 'positive' | 'negative' | 'neutral';
    icon: string;
  }[];
  recent_activity: { action: string; detail: string; timestamp: string }[];
  recommended_actions: { title: string; link: string; category: string }[];
}
