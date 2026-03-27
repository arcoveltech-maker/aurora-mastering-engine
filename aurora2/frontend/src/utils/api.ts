const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, msg);
  }
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  subscription_tier: string;
  tracks_used: number;
  track_limit: number;
  storage_used_bytes: number;
  storage_limit_bytes: number;
}

export interface UploadResponse {
  upload_url: string;
  file_key: string;
  file_id: string;
}

export interface AnalysisResult {
  integrated_lufs: number;
  true_peak_dbtp: number;
  dynamic_range: number;
  spectral_centroid: number;
  bpm: number | null;
  key: string | null;
  duration_seconds: number;
  sample_rate: number;
  channels: number;
  codec: string;
}

export interface RenderJobResponse {
  job_id: string;
  status: string;
  progress: number;
  stage: string;
  output_url?: string;
}

export interface ColabMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ColabResponse {
  reply: string;
  actions?: { type: string; params: Record<string, unknown> }[];
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, password: string, displayName: string) =>
      request<UserProfile>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, display_name: displayName }),
      }),
    me: (token: string) => request<UserProfile>('/api/users/me', {}, token),
  },

  upload: {
    getUploadUrl: (token: string, filename: string, mimeType: string) =>
      request<UploadResponse>('/api/upload/presign', {
        method: 'POST',
        body: JSON.stringify({ filename, mime_type: mimeType }),
      }, token),
    putFile: (url: string, file: File) =>
      fetch(url, { method: 'PUT', body: file }),
    analyze: (token: string, fileId: string) =>
      request<AnalysisResult>(`/api/upload/${fileId}/analyze`, {}, token),
  },

  sessions: {
    create: (token: string, manifest: Record<string, unknown>) =>
      request<{ session_id: string; version_id: string }>('/api/sessions', {
        method: 'POST',
        body: JSON.stringify(manifest),
      }, token),
    update: (token: string, sessionId: string, manifest: Record<string, unknown>) =>
      request<{ version_id: string }>(`/api/sessions/${sessionId}`, {
        method: 'PUT',
        body: JSON.stringify(manifest),
      }, token),
  },

  render: {
    start: (token: string, sessionId: string) =>
      request<RenderJobResponse>(`/api/render/${sessionId}`, {
        method: 'POST',
      }, token),
    status: (token: string, jobId: string) =>
      request<RenderJobResponse>(`/api/render/jobs/${jobId}`, {}, token),
  },

  colab: {
    chat: (token: string, sessionId: string, messages: ColabMessage[]) =>
      request<ColabResponse>('/api/colab/chat', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, messages }),
      }, token),
    separateStems: (token: string, fileId: string, numStems: 12 | 6 | 4 | 2) =>
      request<{ job_id: string }>('/api/colab/stems', {
        method: 'POST',
        body: JSON.stringify({ file_id: fileId, num_stems: numStems }),
      }, token),
    writeMetadata: (token: string, fileId: string, tags: Record<string, string>) =>
      request<{ success: boolean }>('/api/colab/metadata', {
        method: 'POST',
        body: JSON.stringify({ file_id: fileId, tags }),
      }, token),
  },
};
