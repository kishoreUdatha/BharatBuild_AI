/**
 * useContainerExecution - Frontend hook for container-based code execution
 *
 * This hook connects the frontend to the backend container system,
 * exactly like how Bolt.new and Replit work:
 *
 * 1. Create container for project
 * 2. Execute commands (npm install, npm run dev, python main.py)
 * 3. Stream output in real-time
 * 4. Get preview URL
 */

import { useState, useCallback, useRef, useEffect } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Types
export interface ContainerInfo {
  container_id: string;
  project_id: string;
  status: 'creating' | 'running' | 'stopped' | 'error' | 'deleted';
  ports: Record<number, number>;
  preview_urls: Record<string, string>;
  created_at: string;
  memory_limit: string;
  cpu_limit: number;
}

export interface ExecutionEvent {
  type: 'status' | 'stdout' | 'stderr' | 'exit' | 'error' | 'done' | 'command_start' | 'batch_stopped';
  data?: string | number | boolean;
  success?: boolean;
  index?: number;
  command?: string;
  reason?: string;
}

export interface FileInfo {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size: number;
}

export interface ContainerStats {
  cpu_percent: number;
  memory_usage_mb: number;
  memory_limit_mb: number;
  memory_percent: number;
  status: string;
}

// Hook state
interface ContainerState {
  container: ContainerInfo | null;
  isCreating: boolean;
  isExecuting: boolean;
  output: string[];
  error: string | null;
  previewUrl: string | null;
  stats: ContainerStats | null;
}

// Hook options
interface UseContainerExecutionOptions {
  projectId: string;
  projectType?: 'node' | 'python' | 'java' | 'go' | 'rust' | 'ruby' | 'php' | 'static';
  autoCreate?: boolean;
  memoryLimit?: string;
  cpuLimit?: number;
  onOutput?: (line: string) => void;
  onError?: (error: string) => void;
  onCommandComplete?: (exitCode: number, success: boolean) => void;
}

export function useContainerExecution(options: UseContainerExecutionOptions) {
  const {
    projectId,
    projectType = 'node',
    autoCreate = true,
    memoryLimit = '512m',
    cpuLimit = 0.5,
    onOutput,
    onError,
    onCommandComplete,
  } = options;

  const [state, setState] = useState<ContainerState>({
    container: null,
    isCreating: false,
    isExecuting: false,
    output: [],
    error: null,
    previewUrl: null,
    stats: null,
  });

  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Create a container for the project
   */
  const createContainer = useCallback(async (): Promise<ContainerInfo | null> => {
    setState(prev => ({ ...prev, isCreating: true, error: null }));

    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_type: projectType,
          memory_limit: memoryLimit,
          cpu_limit: cpuLimit,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create container');
      }

      const container: ContainerInfo = await response.json();

      setState(prev => ({
        ...prev,
        container,
        isCreating: false,
        previewUrl: container.preview_urls['3000'] || null,
      }));

      return container;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({ ...prev, isCreating: false, error: message }));
      onError?.(message);
      return null;
    }
  }, [projectId, projectType, memoryLimit, cpuLimit, onError]);

  /**
   * Execute a command inside the container
   */
  const executeCommand = useCallback(async (command: string, timeout = 300): Promise<boolean> => {
    // Ensure container exists
    if (!state.container) {
      const container = await createContainer();
      if (!container) return false;
    }

    setState(prev => ({
      ...prev,
      isExecuting: true,
      output: [],
      error: null,
    }));

    // Cancel any existing execution
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/exec`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command, timeout }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error('Failed to execute command');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';
      let success = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: ExecutionEvent = JSON.parse(line.slice(6));

              switch (event.type) {
                case 'stdout':
                case 'stderr':
                  const text = String(event.data);
                  setState(prev => ({
                    ...prev,
                    output: [...prev.output, text],
                  }));
                  onOutput?.(text);
                  break;

                case 'exit':
                  success = event.success ?? (event.data === 0);
                  onCommandComplete?.(event.data as number, success);
                  break;

                case 'error':
                  const errorMsg = String(event.data);
                  setState(prev => ({ ...prev, error: errorMsg }));
                  onError?.(errorMsg);
                  success = false;
                  break;

                case 'done':
                  // Execution complete
                  break;
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }

      setState(prev => ({ ...prev, isExecuting: false }));
      return success;
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        setState(prev => ({ ...prev, isExecuting: false }));
        return false;
      }

      const message = error instanceof Error ? error.message : 'Unknown error';
      setState(prev => ({ ...prev, isExecuting: false, error: message }));
      onError?.(message);
      return false;
    }
  }, [state.container, projectId, createContainer, onOutput, onError, onCommandComplete]);

  /**
   * Execute multiple commands in sequence
   */
  const executeCommands = useCallback(async (
    commands: string[],
    stopOnError = true
  ): Promise<boolean> => {
    for (const command of commands) {
      const success = await executeCommand(command);
      if (!success && stopOnError) {
        return false;
      }
    }
    return true;
  }, [executeCommand]);

  /**
   * Write a file to the project
   */
  const writeFile = useCallback(async (path: string, content: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/files`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, content }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to write file');
      }

      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      onError?.(message);
      return false;
    }
  }, [projectId, onError]);

  /**
   * Write multiple files at once
   */
  const writeFiles = useCallback(async (
    files: Array<{ path: string; content: string }>
  ): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/files/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ files }),
      });

      if (!response.ok) {
        throw new Error('Failed to write files');
      }

      const result = await response.json();
      return result.success === result.total;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      onError?.(message);
      return false;
    }
  }, [projectId, onError]);

  /**
   * Read a file from the project
   */
  const readFile = useCallback(async (path: string): Promise<string | null> => {
    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/files/${encodeURIComponent(path)}`);

      if (!response.ok) {
        if (response.status === 404) return null;
        throw new Error('Failed to read file');
      }

      const data = await response.json();
      return data.content;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      onError?.(message);
      return null;
    }
  }, [projectId, onError]);

  /**
   * List files in directory
   */
  const listFiles = useCallback(async (path = '.'): Promise<FileInfo[]> => {
    try {
      const response = await fetch(
        `${API_BASE}/containers/${projectId}/files?path=${encodeURIComponent(path)}`
      );

      if (!response.ok) {
        throw new Error('Failed to list files');
      }

      return await response.json();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      onError?.(message);
      return [];
    }
  }, [projectId, onError]);

  /**
   * Get preview URL
   */
  const getPreviewUrl = useCallback(async (port = 3000): Promise<string | null> => {
    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/preview?port=${port}`);

      if (!response.ok) return null;

      const data = await response.json();
      setState(prev => ({ ...prev, previewUrl: data.url }));
      return data.url;
    } catch {
      return null;
    }
  }, [projectId]);

  /**
   * Get container stats
   */
  const getStats = useCallback(async (): Promise<ContainerStats | null> => {
    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/stats`);

      if (!response.ok) return null;

      const stats = await response.json();
      setState(prev => ({ ...prev, stats }));
      return stats;
    } catch {
      return null;
    }
  }, [projectId]);

  /**
   * Stop the container
   */
  const stopContainer = useCallback(async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/containers/${projectId}/stop`, {
        method: 'POST',
      });

      if (!response.ok) return false;

      setState(prev => ({
        ...prev,
        container: prev.container
          ? { ...prev.container, status: 'stopped' }
          : null,
      }));

      return true;
    } catch {
      return false;
    }
  }, [projectId]);

  /**
   * Delete the container
   */
  const deleteContainer = useCallback(async (deleteFiles = false): Promise<boolean> => {
    try {
      const response = await fetch(
        `${API_BASE}/containers/${projectId}?delete_files=${deleteFiles}`,
        { method: 'DELETE' }
      );

      if (!response.ok) return false;

      setState(prev => ({
        ...prev,
        container: null,
        previewUrl: null,
      }));

      return true;
    } catch {
      return false;
    }
  }, [projectId]);

  /**
   * Cancel current execution
   */
  const cancelExecution = useCallback(() => {
    abortControllerRef.current?.abort();
    setState(prev => ({ ...prev, isExecuting: false }));
  }, []);

  /**
   * Clear output
   */
  const clearOutput = useCallback(() => {
    setState(prev => ({ ...prev, output: [], error: null }));
  }, []);

  // Auto-create container on mount if enabled
  useEffect(() => {
    if (autoCreate && projectId && !state.container && !state.isCreating) {
      createContainer();
    }
  }, [autoCreate, projectId, state.container, state.isCreating, createContainer]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return {
    // State
    container: state.container,
    isCreating: state.isCreating,
    isExecuting: state.isExecuting,
    output: state.output,
    error: state.error,
    previewUrl: state.previewUrl,
    stats: state.stats,

    // Container actions
    createContainer,
    stopContainer,
    deleteContainer,

    // Execution
    executeCommand,
    executeCommands,
    cancelExecution,

    // File operations
    writeFile,
    writeFiles,
    readFile,
    listFiles,

    // Preview & stats
    getPreviewUrl,
    getStats,

    // Utilities
    clearOutput,
  };
}

export default useContainerExecution;
