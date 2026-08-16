export const DANGEROUS_PATTERNS=[/rm\s+-rf?\s+[/\\]/i,/format\s+[a-z]:/i,/mkfs/i,/dd\s+if=/i,/DROP\s+(TABLE|DATABASE)/i,/DELETE\s+FROM/i,/TRUNCATE\s+TABLE/i,/git\s+push\s+--force/i];
export function isDangerousCommand(cmd: string): boolean { return DANGEROUS_PATTERNS.some((p)=>p.test(cmd)); }
