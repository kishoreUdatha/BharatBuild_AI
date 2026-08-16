export interface ProjectDTO { id: string; name: string; description?: string; status: string; tech_stack?: string; created_at: string; }
export interface UserDTO { id: string; email: string; name: string; full_name?: string; tier: string; subscription_plan?: string; token_balance?: number; tokens_remaining?: number; }
export interface APIKeyDTO { id: string; name: string; key_prefix: string; created_at: string; last_used?: string; is_active: boolean; }
