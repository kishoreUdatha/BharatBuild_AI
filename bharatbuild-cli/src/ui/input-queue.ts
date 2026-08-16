export class InputQueue {
  private queue: string[] = [];

  enqueue(input: string): void {
    this.queue.push(input);
  }

  dequeue(): string | undefined {
    return this.queue.shift();
  }

  peek(): string | undefined {
    return this.queue[0];
  }

  get size(): number {
    return this.queue.length;
  }

  clear(): void {
    this.queue = [];
  }

  hasQueued(): boolean {
    return this.queue.length > 0;
  }
}
