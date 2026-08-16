import { BharatBuildClient } from "./client.js";
import type { UserDTO } from "./types.js";
export class AuthClient {
  constructor(private c: BharatBuildClient) {}
  async me() { return this.c.get<UserDTO>("/api/v1/auth/me"); }
  async login(email: string, password: string) { return this.c.post<{ access_token: string; user?: UserDTO }>("/api/v1/auth/login", { email, password }); }
  async register(name: string, email: string, password: string) { return this.c.post<{ access_token: string; user?: UserDTO }>("/api/v1/auth/register", { full_name: name, email, password }); }
}
