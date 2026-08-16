import fs from "fs"; import path from "path";
export interface Dependency { name:string; version:string; isDev:boolean; }
export function analyzeDependencies(projectDir: string): Dependency[] {
  const pkgPath=path.join(projectDir,"package.json"); if (!fs.existsSync(pkgPath)) return [];
  try { const p=JSON.parse(fs.readFileSync(pkgPath,"utf8")) as Record<string,Record<string,string>>; return [...Object.entries(p["dependencies"]??{}).map(([n,v])=>({name:n,version:v,isDev:false})),...Object.entries(p["devDependencies"]??{}).map(([n,v])=>({name:n,version:v,isDev:true}))]; } catch { return []; }
}
