const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

let token: string | null = null;

export function setToken(value: string | null) { token = value; }

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
  const text = await res.text();
  let body: any = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!res.ok) throw new Error(body?.detail || body?.message || `API error ${res.status}`);
  return body as T;
}

export const api = {
  login: (email: string, password: string) => request<any>("/auth/login", {method:"POST",body:JSON.stringify({email,password})}),
  refresh: () => request<any>("/auth/refresh", {method:"POST"}),
  logout: () => request<any>("/auth/logout", {method:"POST"}),
  register: (data:any) => request<any>("/auth/register", {method:"POST",body:JSON.stringify({
    ...data, orgType:data.orgType, graduationYear:data.graduationYear, githubUrl:data.githubUrl
  })}),
  me: () => request<any>("/auth/me"),
  events: () => request<any[]>("/events"),
  event: (id:string) => request<any>(`/events/${id}`),
  createEvent: (data:any) => request<any>("/events",{method:"POST",body:JSON.stringify(data)}),
  updateEvent: (id:string,data:any) => request<any>(`/events/${id}`,{method:"PATCH",body:JSON.stringify(data)}),
  registerEvent: (id:string,accessCode?:string) => request<any>(`/events/${id}/register`,{method:"POST",body:JSON.stringify({accessCode})}),
  joinByCode: (eventCode:string,accessCode?:string) => request<any>(`/events/join-by-code`,{method:"POST",body:JSON.stringify({eventCode,accessCode})}),
  participants: (id:string) => request<any[]>(`/events/${id}/participants`),
  decideParticipant: (eventId:string,participantId:string,status:string) => request<any>(`/events/${eventId}/participants/${participantId}`,{method:"PATCH",body:JSON.stringify({status})}),
  teams: (id:string) => request<any[]>(`/events/${id}/teams`),
  myTeams: () => request<any[]>("/me/teams"),
  createTeam: (id:string,data:any) => request<any>(`/events/${id}/teams`,{method:"POST",body:JSON.stringify({...data,eventId:id})}),
  addMember: (id:string,data:any) => request<any>(`/teams/${id}/members`,{method:"POST",body:JSON.stringify(data)}),
  projects: (id:string) => request<any[]>(`/events/${id}/projects`),
  myProjects: () => request<any[]>("/me/projects"),
  project: (id:string) => request<any>(`/projects/${id}`),
  createProject: (id:string,data:any) => request<any>(`/events/${id}/projects`,{method:"POST",body:JSON.stringify({...data,eventId:id})}),
  updateProject: (id:string,data:any) => request<any>(`/projects/${id}`,{method:"PATCH",body:JSON.stringify(data)}),
  judges: (id:string) => request<any[]>(`/events/${id}/judges`),
  assign: (projectId:string,judgeId:string) => request<any>("/assignments",{method:"POST",body:JSON.stringify({projectId,judgeId})}),
  unassign: (projectId:string,judgeId:string) => request<any>(`/assignments/${projectId}/${judgeId}`,{method:"DELETE"}),
  autoAssign: (id:string) => request<any>(`/events/${id}/auto-assign`,{method:"POST"}),
  conflict: (projectId:string,reason:string) => request<any>("/conflicts",{method:"POST",body:JSON.stringify({projectId,reason})}),
  saveReview: (data:any) => request<any>("/reviews",{method:"POST",body:JSON.stringify(data)}),
  reopenReview: (data:any) => request<any>("/reviews/reopen",{method:"POST",body:JSON.stringify(data)}),
  reviews: () => request<any[]>("/me/reviews"),
  calculate: (id:string,data:any={}) => request<any>(`/events/${id}/results/calculate`,{method:"POST",body:JSON.stringify(data)}),
  publish: (id:string) => request<any>(`/events/${id}/results/publish`,{method:"POST"}),
  results: (id:string) => request<any[]>(`/events/${id}/results`),
  audit: (id:string) => request<any[]>(`/events/${id}/audit`),
  integrity: (id:string) => request<any>(`/events/${id}/integrity`),
  judgeLens: (id:string) => request<any>(`/events/${id}/judgelens`),
  normalizationProof: (eventId:string,snapshotId:string) => request<any>(`/events/${eventId}/normalization-proof/${snapshotId}`),
  exportResults: (eventId:string,format:"json"|"csv"="json") => request<any>(`/events/${eventId}/export?format=${format}`),
  analytics: (eventId:string) => request<any>(`/events/${eventId}/analytics`),
  notifications: () => request<any[]>("/me/notifications"),
};
