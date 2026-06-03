const BASE_URL = '/api';

function getHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `HTTP error ${response.status}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorMessage;
    } catch {
      errorMessage = errorText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  // Auth
  async login(email: string, password: string): Promise<{ access_token: string }> {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async getMe(): Promise<{ email: string; role: string; id: number }> {
    return request('/auth/me');
  },

  // Dashboard
  async getDashboardStats(): Promise<any> {
    return request('/dashboard');
  },

  // Sources
  async getSources(): Promise<any[]> {
    return request('/sources');
  },

  async createSource(source: any): Promise<any> {
    return request('/sources', {
      method: 'POST',
      body: JSON.stringify(source),
    });
  },

  async updateSource(id: number, source: any): Promise<any> {
    return request(`/sources/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(source),
    });
  },

  async deleteSource(id: number): Promise<any> {
    return request(`/sources/${id}`, {
      method: 'DELETE',
    });
  },

  async crawlSource(id: number): Promise<any> {
    return request(`/sources/${id}/crawl`, {
      method: 'POST',
    });
  },

  // Raw Items
  async getRawItems(status?: string, sourceId?: number): Promise<any[]> {
    let path = '/raw-items?limit=50';
    if (status) path += `&status=${status}`;
    if (sourceId) path += `&source_id=${sourceId}`;
    return request(path);
  },

  async reprocessRawItem(id: number): Promise<any> {
    return request(`/raw-items/${id}/reprocess`, {
      method: 'POST',
    });
  },

  // Events
  async getEvents(status?: string, category?: string): Promise<any[]> {
    let path = '/events?limit=80';
    if (status) path += `&status=${status}`;
    if (category) path += `&category=${category}`;
    return request(path);
  },

  async getEvent(id: number): Promise<any> {
    return request(`/events/${id}`);
  },

  async getPossibleDuplicates(id: number): Promise<any[]> {
    return request(`/events/${id}/possible-duplicates`);
  },

  async updateEvent(id: number, event: any): Promise<any> {
    return request(`/events/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(event),
    });
  },

  async approveEvent(id: number): Promise<any> {
    return request(`/events/${id}/approve`, {
      method: 'POST',
    });
  },

  async rejectEvent(id: number): Promise<any> {
    return request(`/events/${id}/reject`, {
      method: 'POST',
    });
  },

  async publishEvent(id: number): Promise<any> {
    return request(`/events/${id}/publish`, {
      method: 'POST',
    });
  },

  async scheduleEvent(id: number, scheduledAt: string): Promise<any> {
    return request(`/events/${id}/schedule`, {
      method: 'POST',
      body: JSON.stringify({ scheduled_at: scheduledAt }),
    });
  },

  async regenerateEventText(id: number): Promise<any> {
    return request(`/events/${id}/regenerate`, {
      method: 'POST',
    });
  },

  async mergeDuplicate(id: number, targetEventId: number): Promise<any> {
    return request(`/events/${id}/merge-duplicate`, {
      method: 'POST',
      body: JSON.stringify({ target_event_id: targetEventId }),
    });
  },

  // Submissions
  async getSubmissions(status?: string): Promise<any[]> {
    let path = '/submissions';
    if (status) path += `?status=${status}`;
    return request(path);
  },

  async acceptSubmission(id: number): Promise<any> {
    return request(`/submissions/${id}/accept`, {
      method: 'POST',
    });
  },

  async rejectSubmission(id: number): Promise<any> {
    return request(`/submissions/${id}/reject`, {
      method: 'POST',
    });
  },

  // Posts
  async getPosts(status?: string, postType?: string): Promise<any[]> {
    let path = '/posts?limit=50';
    if (status) path += `&status=${status}`;
    if (postType) path += `&post_type=${postType}`;
    return request(path);
  },

  async triggerDailyDigest(): Promise<any> {
    return request('/posts/daily-digest', {
      method: 'POST',
    });
  },

  async triggerTomorrowDigest(): Promise<any> {
    return request('/posts/tomorrow-digest', {
      method: 'POST',
    });
  },

  async triggerWeekendDigest(): Promise<any> {
    return request('/posts/weekend-digest', {
      method: 'POST',
    });
  },
};
