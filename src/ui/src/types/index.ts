export interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

export interface QueryRequest {
  query: string;
}

export interface QueryResponse {
  response: string;
  vector_answer?: string;
  graph_answer?: string;
  // graph_data removed - no longer providing graph visualization
}
