import axios from 'axios';
import type { ChatResponse, MaterialsData } from '../types/chat';

// AWS API Gateway endpoint - update this after deploying your CDK stack
// Get the URL from: `cdk deploy` output or AWS Console > API Gateway
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://msl5bygkaj.execute-api.us-east-1.amazonaws.com/prod';

// Generate a unique session ID for this browser session
const SESSION_ID = `web-${Date.now()}-${Math.random().toString(36).substring(7)}`;

/**
 * Fetch the complete materials.json from the Lambda /materials endpoint
 */
export async function getMaterials(): Promise<MaterialsData> {
  try {
    const response = await axios.get<MaterialsData>(`${API_BASE_URL}/materials`);
    return response.data;
  } catch (error) {
    console.error('Error fetching materials:', error);
    // Return empty structure on error
    return {
      topics: [],
      metadata: {
        course: '',
        level: '',
        last_updated: '',
        total_topics: 0,
      },
    };
  }
}

/**
 * Send a message to the chat API (AWS Lambda backend via API Gateway)
 * 
 * @param message - The message to send
 * @param sessionId - Optional session ID for conversation persistence
 * @returns The response from the serverless backend
 */
export async function sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
  try {
    // Use provided sessionId or generate one for this browser session
    const sid = sessionId || SESSION_ID;
    
    const requestBody = { 
      message,
      sessionId: sid,
    };
    
    const response = await axios.post<ChatResponse>(
      `${API_BASE_URL}/chat`,
      requestBody,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // Server responded with error status
        console.error('Lambda error:', error.response.data);
        throw new Error(error.response.data.error || 'Backend error occurred');
      } else if (error.request) {
        // Request made but no response received
        console.error('No response from AWS backend');
        throw new Error('Cannot connect to backend. Please check your internet connection.');
      }
    }
    console.error('Error sending message:', error);
    throw error;
  }
}

/**
 * Check API Gateway health
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await axios.post(`${API_BASE_URL}/chat`, {
      message: "health check",
      sessionId: "health"
    });
    return response.status === 200;
  } catch (error) {
    return false;
  }
}