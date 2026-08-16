import { marked } from "marked";
import TerminalRenderer from "marked-terminal";

marked.setOptions({ renderer: new TerminalRenderer() as never });

export function renderMarkdown(text: string): string {
  try {
    return marked(text) as string;
  } catch {
    return text;
  }
}

export function printMarkdown(text: string): void {
  process.stdout.write(renderMarkdown(text));
}
