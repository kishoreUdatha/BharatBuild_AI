import { BharatBuildClient } from "./client.js";
export interface TaskDTO { id: string; title: string; status: string; description?: string; project_id?: string; }
export class TaskClient {
  constructor(private c: BharatBuildClient) {}
  async list(pid?: string) {
    const url = pid ? `/api/v1/tasks?project_id=${pid}` : "/api/v1/tasks";
    const d = await this.c.get<{ items?: TaskDTO[]; tasks?: TaskDTO[] }>(url);
    return (d.items ?? d.tasks ?? (Array.isArray(d) ? d : [])) as TaskDTO[];
  }
  async get(id: string) { return this.c.get<TaskDTO>(`/api/v1/tasks/${id}`); }
  async create(t: Partial<TaskDTO>) { return this.c.post<TaskDTO>("/api/v1/tasks", t); }
  async update(id: string, u: Partial<TaskDTO>) { return this.c.put<TaskDTO>(`/api/v1/tasks/${id}`, u); }
}
