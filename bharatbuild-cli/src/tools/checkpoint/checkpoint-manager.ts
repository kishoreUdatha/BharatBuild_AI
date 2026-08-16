/**
 * BharatBuild CLI - Checkpoint Manager
 * 
 * File restore point system for safe experimentation.
 */
import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { getConfigDir } from "../../config/config.js";

export interface Checkpoint {
  id: string;
  name: string;
  timestamp: number;
  files: Array<{
    path: string;
    hash: string;
    size: number;
  }>;
  workingDir: string;
  branch?: string;
  commit?: string;
}

export class CheckpointManager {
  private checkpointsDir: string;
  
  constructor() {
    this.checkpointsDir = path.join(getConfigDir(), "checkpoints");
    this.ensureDir();
  }

  private ensureDir(): void {
    if (!fs.existsSync(this.checkpointsDir)) {
      fs.mkdirSync(this.checkpointsDir, { recursive: true });
    }
  }

  private getCheckpointPath(id: string): string {
    return path.join(this.checkpointsDir, `${id}.json`);
  }

  private getFilesDir(id: string): string {
    return path.join(this.checkpointsDir, id);
  }

  private generateId(): string {
    return crypto.randomBytes(8).toString('hex');
  }

  private hashFile(filePath: string): string {
    if (!fs.existsSync(filePath)) return "";
    const content = fs.readFileSync(filePath);
    return crypto.createHash('sha256').update(content).digest('hex');
  }

  /**
   * Create a new checkpoint of current working directory state
   */
  async init(name?: string): Promise<Checkpoint> {
    const id = this.generateId();
    const workingDir = process.cwd();
    const checkpointName = name || `checkpoint-${new Date().toISOString().slice(0, 16).replace(/[:.]/g, '-')}`;
    
    // Get git info if available
    let branch: string | undefined;
    let commit: string | undefined;
    try {
      branch = execSync('git branch --show-current', { cwd: workingDir, encoding: 'utf8' }).trim();
      commit = execSync('git rev-parse HEAD', { cwd: workingDir, encoding: 'utf8' }).trim();
    } catch {
      // Not a git repo or git not available
    }

    // Find all files to checkpoint (respect gitignore if available)
    const files: Array<{ path: string; hash: string; size: number }> = [];
    const filesDir = this.getFilesDir(id);
    fs.mkdirSync(filesDir, { recursive: true });

    const walkDir = (dir: string, relativeTo: string = workingDir) => {
      const items = fs.readdirSync(dir);
      for (const item of items) {
        const fullPath = path.join(dir, item);
        const relativePath = path.relative(relativeTo, fullPath);
        
        // Skip common ignored patterns
        if (this.shouldIgnore(relativePath)) continue;
        
        const stat = fs.statSync(fullPath);
        if (stat.isDirectory()) {
          walkDir(fullPath, relativeTo);
        } else if (stat.isFile()) {
          const hash = this.hashFile(fullPath);
          files.push({
            path: relativePath,
            hash,
            size: stat.size
          });
          
          // Copy file to checkpoint storage
          const targetPath = path.join(filesDir, relativePath);
          fs.mkdirSync(path.dirname(targetPath), { recursive: true });
          fs.copyFileSync(fullPath, targetPath);
        }
      }
    };

    walkDir(workingDir);

    const checkpoint: Checkpoint = {
      id,
      name: checkpointName,
      timestamp: Date.now(),
      files,
      workingDir,
      branch,
      commit
    };

    // Save checkpoint metadata
    fs.writeFileSync(this.getCheckpointPath(id), JSON.stringify(checkpoint, null, 2));
    
    return checkpoint;
  }

  /**
   * List all available checkpoints
   */
  list(): Checkpoint[] {
    if (!fs.existsSync(this.checkpointsDir)) return [];
    
    const checkpoints: Checkpoint[] = [];
    const files = fs.readdirSync(this.checkpointsDir);
    
    for (const file of files) {
      if (file.endsWith('.json')) {
        try {
          const content = fs.readFileSync(path.join(this.checkpointsDir, file), 'utf8');
          const checkpoint = JSON.parse(content) as Checkpoint;
          checkpoints.push(checkpoint);
        } catch (error) {
          console.warn(`Failed to read checkpoint ${file}:`, error);
        }
      }
    }
    
    return checkpoints.sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * Get checkpoint by ID (supports partial ID matching)
   */
  get(idOrPartial: string): Checkpoint | null {
    const checkpoints = this.list();
    
    // Exact match first
    let found = checkpoints.find(c => c.id === idOrPartial);
    if (found) return found;
    
    // Partial match
    found = checkpoints.find(c => c.id.startsWith(idOrPartial));
    if (found) return found;
    
    // Name match
    return checkpoints.find(c => c.name.toLowerCase().includes(idOrPartial.toLowerCase())) || null;
  }

  /**
   * Restore files from a checkpoint
   */
  async restore(idOrPartial: string, files?: string[]): Promise<{ restored: string[], skipped: string[] }> {
    const checkpoint = this.get(idOrPartial);
    if (!checkpoint) {
      throw new Error(`Checkpoint not found: ${idOrPartial}`);
    }

    const filesDir = this.getFilesDir(checkpoint.id);
    if (!fs.existsSync(filesDir)) {
      throw new Error(`Checkpoint data missing for: ${checkpoint.id}`);
    }

    const restored: string[] = [];
    const skipped: string[] = [];

    const filesToRestore = files ? 
      checkpoint.files.filter(f => files.some(pattern => f.path.includes(pattern))) :
      checkpoint.files;

    for (const file of filesToRestore) {
      const sourcePath = path.join(filesDir, file.path);
      const targetPath = path.join(checkpoint.workingDir, file.path);
      
      if (!fs.existsSync(sourcePath)) {
        skipped.push(file.path);
        continue;
      }

      try {
        // Create directory if needed
        fs.mkdirSync(path.dirname(targetPath), { recursive: true });
        
        // Copy file
        fs.copyFileSync(sourcePath, targetPath);
        restored.push(file.path);
      } catch (error) {
        skipped.push(file.path);
        console.warn(`Failed to restore ${file.path}:`, error);
      }
    }

    return { restored, skipped };
  }

  /**
   * Show diff between current state and checkpoint
   */
  async diff(idOrPartial: string): Promise<{
    modified: string[];
    added: string[];
    deleted: string[];
    unchanged: string[];
  }> {
    const checkpoint = this.get(idOrPartial);
    if (!checkpoint) {
      throw new Error(`Checkpoint not found: ${idOrPartial}`);
    }

    const modified: string[] = [];
    const added: string[] = [];
    const deleted: string[] = [];
    const unchanged: string[] = [];

    // Check files in checkpoint vs current
    const currentFiles = new Map<string, string>();
    
    const walkDir = (dir: string, relativeTo: string = process.cwd()) => {
      if (!fs.existsSync(dir)) return;
      const items = fs.readdirSync(dir);
      for (const item of items) {
        const fullPath = path.join(dir, item);
        const relativePath = path.relative(relativeTo, fullPath);
        
        if (this.shouldIgnore(relativePath)) continue;
        
        const stat = fs.statSync(fullPath);
        if (stat.isDirectory()) {
          walkDir(fullPath, relativeTo);
        } else if (stat.isFile()) {
          const hash = this.hashFile(fullPath);
          currentFiles.set(relativePath, hash);
        }
      }
    };

    walkDir(process.cwd());

    // Compare checkpoint files to current
    for (const file of checkpoint.files) {
      const currentHash = currentFiles.get(file.path);
      if (!currentHash) {
        deleted.push(file.path);
      } else if (currentHash !== file.hash) {
        modified.push(file.path);
      } else {
        unchanged.push(file.path);
      }
      currentFiles.delete(file.path);
    }

    // Remaining current files are new
    added.push(...Array.from(currentFiles.keys()));

    return { modified, added, deleted, unchanged };
  }

  /**
   * Delete a checkpoint
   */
  delete(idOrPartial: string): boolean {
    const checkpoint = this.get(idOrPartial);
    if (!checkpoint) return false;

    try {
      // Delete metadata file
      const metaPath = this.getCheckpointPath(checkpoint.id);
      if (fs.existsSync(metaPath)) {
        fs.unlinkSync(metaPath);
      }

      // Delete files directory
      const filesDir = this.getFilesDir(checkpoint.id);
      if (fs.existsSync(filesDir)) {
        fs.rmSync(filesDir, { recursive: true, force: true });
      }

      return true;
    } catch {
      return false;
    }
  }

  private shouldIgnore(path: string): boolean {
    const patterns = [
      /^node_modules(\/|$)/,
      /^\.git(\/|$)/,
      /^\.bharatbuild(\/|$)/,
      /^dist(\/|$)/,
      /^build(\/|$)/,
      /^out(\/|$)/,
      /^target(\/|$)/,
      /^\.cache(\/|$)/,
      /^\.next(\/|$)/,
      /^coverage(\/|$)/,
      /^\.nyc_output(\/|$)/,
      /\.DS_Store$/,
      /\.log$/,
      /\.tmp$/,
      /\.temp$/,
      /~$/
    ];

    return patterns.some(pattern => pattern.test(path));
  }
}