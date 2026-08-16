export interface Criterion { description: string; met: boolean; }
export function parseCriteria(markdown: string): Criterion[] {
  return markdown.split("\n").filter((l) => l.trim().startsWith("- ")).map((l) => ({ description: l.replace(/^-\s*/, "").trim(), met: false }));
}
export function checkCriteria(criteria: Criterion[], testOutput: string): Criterion[] {
  return criteria.map((c) => ({ ...c, met: testOutput.toLowerCase().includes(c.description.toLowerCase().split(" ").slice(0, 3).join(" ")) }));
}
