import { QueryRequest, QueryResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

export const queryAPI = async (message: string): Promise<QueryResponse> => {
  const requestBody: QueryRequest = { query: message };

  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data: QueryResponse = await response.json();
  return data;
};
