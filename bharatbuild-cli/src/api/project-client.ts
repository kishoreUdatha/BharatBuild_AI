import { BharatBuildClient } from "./client.js";
import type { ProjectDTO } from "./types.js";
export class ProjectClient {
  constructor(private c: BharatBuildClient) {}
  async list(limit = 20) {
    const d = await this.c.get<{ projects?: ProjectDTO[]; items?: ProjectDTO[] }>(`/api/v1/projects?limit=${limit}`);
    return (d.projects ?? d.items ?? (Array.isArray(d) ? d : [])) as ProjectDTO[];
  }
  async get(id: string) { return this.c.get<ProjectDTO>(`/api/v1/projects/${id}`); }
  async create(p: { name: string; description?: string; tech_stack?: string }) { return this.c.post<ProjectDTO>("/api/v1/projects", p); }
  async delete(id: string) { await this.c.delete(`/api/v1/projects/${id}`); }
}
