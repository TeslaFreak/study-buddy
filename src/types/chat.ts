export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: SourceMaterial[];
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  response: string;
  sessionId?: string;
  sources?: SourceMaterial[];
  relevantMaterialId?: string;
}

export interface SourceMaterial {
  content: string;
  score: number;
  source: string;
  documentName: string;
}

export interface StudyMaterial {
  id: string;
  title: string;
  category: string;
  content: string;
  key_concepts: string[];
  study_questions: string[];
}

export interface MaterialsData {
  topics: StudyMaterial[];
  metadata: {
    course: string;
    level: string;
    last_updated: string;
    total_topics: number;
  };
}