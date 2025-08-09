export interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  traceId?: string;
  spanId?: string;
}

export interface QueryRequest {
  query: string;
}

export interface QueryResponse {
  response: string;
  vector_answer?: string;
  graph_answer?: string;
  trace_id?: string;
  span_id?: string;
  // graph_data removed - no longer providing graph visualization
}

export interface FeedbackRequest {
  trace_id?: string;
  span_id?: string;
  feedback_type: 'thumbs_up' | 'thumbs_down';
  reason?: string;
}
