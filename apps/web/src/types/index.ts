export interface Evaluation {
  id: string;
  status: string;
  video_url: string;
  created_at: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
