export interface CrewAgent { id: string; name: string; role: string; model?: string; status: "idle"|"running"|"complete"|"failed"; task?: string; result?: string; startedAt?: string; completedAt?: string; }
export interface CrewSession { id: string; title: string; agents: CrewAgent[]; createdAt: string; status: "active"|"complete"|"failed"; }
export interface CrewTask { id: string; description: string; assignedTo?: string; dependsOn?: string[]; status: "pending"|"running"|"complete"|"failed"; result?: string; }
