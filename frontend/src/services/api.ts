const API_BASE_URL = 'http://localhost:8000/api';

export interface UserProfile {
  uid: string;
  name: string;
  working_hours_start: string;
  working_hours_end: string;
  energy_profile: string;
  stress_handling: string;
}

export interface SubTask {
  id: string;
  title: string;
  duration_hours: number;
  importance: number;
  status: 'todo' | 'in_progress' | 'done' | 'skipped';
  scheduled_start?: string;
  scheduled_end?: string;
}

export interface Deadline {
  id: string;
  user_id: string;
  title: string;
  description: string;
  due_date: string;
  estimated_hours: number;
  category: string;
  status: 'active' | 'completed' | 'panicked';
  subtasks: SubTask[];
  created_at: string;
}

export interface PanicRequest {
  current_time: string;
  lost_hours: number;
  custom_panic_reason?: string;
}

export interface RecoveryPlan {
  generated_at: string;
  triage_strategy: string;
  rearranged_subtasks: SubTask[];
  motivation_tip: string;
}

export const api = {
  async getProfile(): Promise<UserProfile> {
    const response = await fetch(`${API_BASE_URL}/schedule/profile`);
    if (!response.ok) throw new Error('Failed to fetch user profile');
    return response.json();
  },

  async updateProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
    const response = await fetch(`${API_BASE_URL}/schedule/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    });
    if (!response.ok) throw new Error('Failed to update user profile');
    return response.json();
  },

  async getDeadlines(): Promise<Deadline[]> {
    const response = await fetch(`${API_BASE_URL}/deadlines`);
    if (!response.ok) throw new Error('Failed to fetch deadlines');
    return response.json();
  },

  async getDeadline(id: string): Promise<Deadline> {
    const response = await fetch(`${API_BASE_URL}/deadlines/${id}`);
    if (!response.ok) throw new Error('Failed to fetch deadline');
    return response.json();
  },

  async createDeadline(payload: { title: string; description: string; due_date: string; estimated_hours?: number; category: string }): Promise<Deadline> {
    const response = await fetch(`${API_BASE_URL}/deadlines`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to create deadline');
    return response.json();
  },

  async deleteDeadline(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/deadlines/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete deadline');
  },

  async updateSubtaskStatus(deadlineId: string, subtaskId: string, status: 'todo' | 'in_progress' | 'done'): Promise<Deadline> {
    const response = await fetch(`${API_BASE_URL}/deadlines/${deadlineId}/subtasks/${subtaskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (!response.ok) throw new Error('Failed to update subtask status');
    return response.json();
  },

  async triggerPanic(deadlineId: string, payload: PanicRequest): Promise<RecoveryPlan> {
    const response = await fetch(`${API_BASE_URL}/recovery/panic/${deadlineId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error('Failed to trigger panic recovery plan');
    return response.json();
  },

  async rescheduleDeadline(deadlineId: string): Promise<Deadline> {
    const response = await fetch(`${API_BASE_URL}/schedule/reschedule/${deadlineId}`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to reschedule deadline');
    return response.json();
  }
};
