// This file mirrors the Pydantic models from your BFF. 
// It isolates all network logic using axios.

import axios from 'axios';

const API_URL = 'http://localhost:8000'; // Pointing to your FastAPI BFF

// --- Types (Mirroring BFF Pydantic Models) ---
export interface Difference {
  diff_id: string;
  field_name: string;
  value_a: string | null;
  value_b: string | null;
  diff_type: string;
}

export interface ReasonCode {
  reason_id: number;
  code: string;
  description: string;
  is_functional: boolean;
}

export interface ReviewItem {
  attribution_id: string;
  confidence_score: number;
  status: 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'UNKNOWN';
  source_a_ref_id: string;
  source_b_ref_id: string;
  difference: Difference;
  current_reason: ReasonCode | null;
}

// --- API Calls ---
export const fetchReviewQueue = async (): Promise<ReviewItem[]> => {
  const { data } = await axios.get(`${API_URL}/workflow/queue?limit=50`);
  return data;
};

export const resolveException = async (payload: {
  attribution_id: string;
  action: 'APPROVE' | 'OVERRIDE';
  actor_id: string;
  new_reason_code?: string;
  comments?: string;
}) => {
  const { data } = await axios.post(`${API_URL}/workflow/resolve`, payload);
  return data;
};
