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
  ontology_context?: any;
  graph_context_str?: any;
  graph_data?: any;
}
