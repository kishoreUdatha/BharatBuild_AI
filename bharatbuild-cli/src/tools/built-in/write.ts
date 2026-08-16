/**
 * BharatBuild CLI — Built-in Tool: write
 * A tool for creating and editing text files.
 * Supports create, strReplace, and insert operations matching Kiro CLI.
 */

import fs from "fs";
import path from "path";
import type { BuiltInTool, ToolResult } from "./types.js";

export const writeTool: BuiltInTool = {
  definition: {
    name: "write",
    source: "built-in",
    status: "approval_required",
    description:
      "A tool for creating and editing text files. Supports create, strReplace, and insert operations.",
    parameters: {
      type: "object",
      properties: {
        command: {
          type: "string",
          enum: ["create", "strReplace", "insert"],
          description: "The command to run: create, strReplace, or insert.",
        },
        path: { type: "string", description: "Path to the file." },
        content: { type: "string", description: "Content for create/insert commands." },
        oldStr: { type: "string", description: "String to replace (required for strReplace)." },
        newStr: { type: "string", description: "Replacement string (required for strReplace)." },
        replaceAll: {
          type: "boolean",
          description: "Replace all occurrences (optional for strReplace, default false).",
        },
        insertLine: {
          type: "number",
          description: "Line number (0-indexed) to insert at (optional for insert). If omitted, appends to end.",
        },
      },
      required: ["command", "path"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const command = params["command"] as string;
    const filePath = params["path"] as string;

    if (!command) return { content: "Error: 'command' is required.", isError: true };
    if (!filePath) return { content: "Error: 'path' is required.", isError: true };

    const resolved = path.resolve(filePath);

    switch (command) {
      case "create":
        return executeCreate(resolved, params);
      case "strReplace":
        return executeStrReplace(resolved, params);
      case "insert":
        return executeInsert(resolved, params);
      default:
        return { content: `Error: Unknown command '${command}'. Use 'create', 'strReplace', or 'insert'.`, isError: true };
    }
  },
};

function executeCreate(filePath: string, params: Record<string, unknown>): ToolResult {
  const content = params["content"] as string;
  if (content === undefined || content === null) {
    return { content: "Error: 'content' is required for create.", isError: true };
  }

  try {
    // Create parent directories if they don't exist
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content, "utf8");
    const lines = content.split("\n").length;
    return {
      content: `Successfully created ${filePath} (${lines} lines).`,
      isError: false,
    };
  } catch (err) {
    return { content: `Error creating file: ${err instanceof Error ? err.message : String(err)}`, isError: true };
  }
}

function executeStrReplace(filePath: string, params: Record<string, unknown>): ToolResult {
  const oldStr = params["oldStr"] as string;
  const newStr = params["newStr"] as string;
  const replaceAll = params["replaceAll"] as boolean ?? false;

  if (oldStr === undefined || oldStr === null) {
    return { content: "Error: 'oldStr' is required for strReplace.", isError: true };
  }
  if (newStr === undefined || newStr === null) {
    return { content: "Error: 'newStr' is required for strReplace.", isError: true };
  }

  try {
    if (!fs.existsSync(filePath)) {
      return { content: `Error: File not found: '${filePath}'`, isError: true };
    }

    let content = fs.readFileSync(filePath, "utf8");

    if (!content.includes(oldStr)) {
      return {
        content: `Error: 'oldStr' not found in file. Make sure the string matches exactly (including whitespace and newlines).`,
        isError: true,
      };
    }

    if (replaceAll) {
      // Replace all occurrences
      const count = content.split(oldStr).length - 1;
      content = content.split(oldStr).join(newStr);
      fs.writeFileSync(filePath, content, "utf8");
      return { content: `Replaced ${count} occurrence(s) in ${filePath}.`, isError: false };
    } else {
      // Replace first occurrence only
      const idx = content.indexOf(oldStr);
      content = content.slice(0, idx) + newStr + content.slice(idx + oldStr.length);
      fs.writeFileSync(filePath, content, "utf8");
      return { content: `Replaced 1 occurrence in ${filePath}.`, isError: false };
    }
  } catch (err) {
    return { content: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true };
  }
}

function executeInsert(filePath: string, params: Record<string, unknown>): ToolResult {
  const content = params["content"] as string;
  const insertLine = params["insertLine"] as number | undefined;

  if (content === undefined || content === null) {
    return { content: "Error: 'content' is required for insert.", isError: true };
  }

  try {
    if (!fs.existsSync(filePath)) {
      // If file doesn't exist, create it
      fs.mkdirSync(path.dirname(filePath), { recursive: true });
      fs.writeFileSync(filePath, content + "\n", "utf8");
      return { content: `Created ${filePath} with inserted content.`, isError: false };
    }

    let fileContent = fs.readFileSync(filePath, "utf8");

    if (insertLine === undefined || insertLine === null) {
      // Append to end
      if (!fileContent.endsWith("\n") && fileContent.length > 0) {
        fileContent += "\n";
      }
      fileContent += content;
      fs.writeFileSync(filePath, fileContent, "utf8");
      return { content: `Appended content to end of ${filePath}.`, isError: false };
    }

    // Insert at specific line
    const lines = fileContent.split("\n");
    const insertAt = Math.max(0, Math.min(insertLine, lines.length));
    const contentLines = content.split("\n");
    lines.splice(insertAt, 0, ...contentLines);
    fs.writeFileSync(filePath, lines.join("\n"), "utf8");
    return { content: `Inserted ${contentLines.length} line(s) at line ${insertAt} in ${filePath}.`, isError: false };
  } catch (err) {
    return { content: `Error: ${err instanceof Error ? err.message : String(err)}`, isError: true };
  }
}
