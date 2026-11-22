import type {
  AnnouncementDetail,
  AnnouncementListResponse,
  AnnouncementQueryParams,
  CustomSource,
  CustomSourceCreate,
  InstitutionsCatalogResponse,
  NitelikKodu,
  NotificationTestResponse,
  ScrapeStatusResponse,
  ScrapeTriggerResponse,
  StatsResponse,
  UserAnnouncementStatus,
  UserProfile,
} from './types';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Sunucu hatası (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data?.detail === 'string') {
        detail = data.detail;
      } else if (typeof data?.message === 'string') {
        detail = data.message;
      }
    } catch {
      // ignore non-json error body
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function getProfile(): Promise<UserProfile> {
  return request<UserProfile>('/profile');
}

export async function updateProfile(profile: UserProfile): Promise<UserProfile> {
  return request<UserProfile>('/profile', {
    method: 'PUT',
    body: JSON.stringify(profile),
  });
}

export async function getAnnouncements(
  params: AnnouncementQueryParams = {}
): Promise<AnnouncementListResponse> {
  const search = new URLSearchParams();
  if (params.match_status) search.set('match_status', params.match_status);
  if (params.category && params.category !== 'all') search.set('category', params.category);
  if (params.source && params.source !== 'all') search.set('source', params.source);
  if (params.city && params.city !== 'all') search.set('city', params.city);
  if (params.user_status) search.set('user_status', params.user_status);
  if (params.deadline_soon) search.set('deadline_soon', 'true');
  if (params.q && params.q.trim()) search.set('q', params.q.trim());
  if (params.sort) search.set('sort', params.sort);
  if (params.page) search.set('page', String(params.page));
  if (params.page_size) search.set('page_size', String(params.page_size));

  const qs = search.toString();
  return request<AnnouncementListResponse>(`/announcements${qs ? `?${qs}` : ''}`);
}

export async function getAnnouncementDetail(id: number): Promise<AnnouncementDetail> {
  return request<AnnouncementDetail>(`/announcements/${id}`);
}

export async function updateAnnouncementState(
  id: number,
  payload: { status: UserAnnouncementStatus; notes: string }
): Promise<{ id: number; status: UserAnnouncementStatus; notes: string }> {
  return request(`/announcements/${id}/state`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function getStats(): Promise<StatsResponse> {
  return request<StatsResponse>('/stats');
}

export async function triggerScrape(source = 'all'): Promise<ScrapeTriggerResponse> {
  return request<ScrapeTriggerResponse>('/scrape/trigger', {
    method: 'POST',
    body: JSON.stringify({ source }),
  });
}

export async function getScrapeStatus(): Promise<ScrapeStatusResponse> {
  return request<ScrapeStatusResponse>('/scrape/status');
}

export async function searchNitelikKodlari(q: string): Promise<NitelikKodu[]> {
  const qs = new URLSearchParams({ q: q.trim() }).toString();
  return request<NitelikKodu[]>(`/nitelik-kodlari?${qs}`);
}

export async function getCustomSources(): Promise<CustomSource[]> {
  return request<CustomSource[]>('/custom-sources');
}

export async function createCustomSource(payload: CustomSourceCreate): Promise<CustomSource> {
  return request<CustomSource>('/custom-sources', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteCustomSource(id: number): Promise<void> {
  await request<void>(`/custom-sources/${id}`, {
    method: 'DELETE',
  });
}

export async function getInstitutions(): Promise<InstitutionsCatalogResponse> {
  return request<InstitutionsCatalogResponse>('/institutions');
}

export async function sendTestNotification(): Promise<NotificationTestResponse> {
  return request<NotificationTestResponse>('/notifications/test', {
    method: 'POST',
  });
}

export async function importAnnouncementText(payload: {
  title: string;
  institution: string;
  url: string;
  raw_text: string;
}): Promise<AnnouncementDetail> {
  return request<AnnouncementDetail>('/announcements/import', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function importAnnouncementPdf(
  file: File,
  meta?: { title?: string; institution?: string; url?: string }
): Promise<AnnouncementDetail> {
  const formData = new FormData();
  formData.append('file', file);
  if (meta?.title) formData.append('title', meta.title);
  if (meta?.institution) formData.append('institution', meta.institution);
  if (meta?.url) formData.append('url', meta.url);

  return request<AnnouncementDetail>('/announcements/import-pdf', {
    method: 'POST',
    body: formData,
  });
}

export function getExportIcsUrl(): string {
  return '/api/announcements/export/ics';
}
