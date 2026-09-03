/**
 * Jupyter notebooks.
 *
 * A .ipynb is JSON, so read_file returned the raw document: metadata, base64
 * image outputs, execution counts, and source split into one-line strings. A
 * twenty-cell notebook came back as hundreds of lines the model had to parse
 * before it could see any code, and editing meant rewriting that JSON by hand —
 * which corrupts the file the first time a quote is mismatched.
 *
 * These two tools read a notebook as cells and edit it one cell at a time,
 * leaving the surrounding structure alone.
 */

import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import type { ToolDefinition, ToolResult } from "../filesystem/index.js";

/** Output lines kept per cell. Enough to see a result or an error. */
const MAX_OUTPUT_LINES = 15;

interface NotebookCell {
  cell_type: "code" | "markdown" | "raw";
  /** nbformat allows a string or an array of lines; both appear in the wild. */
  source: string | string[];
  outputs?: unknown[];
  execution_count?: number | null;
  metadata?: Record<string, unknown>;
  id?: string;
}

interface Notebook {
  cells: NotebookCell[];
  metadata?: Record<string, unknown>;
  nbformat?: number;
  nbformat_minor?: number;
}

/** nbformat stores source either way; the model should only ever see text. */
export function cellText(cell: NotebookCell): string {
  return Array.isArray(cell.source) ? cell.source.join("") : (cell.source ?? "");
}

/**
 * Store source as an array of lines with their newlines kept.
 *
 * That is what Jupyter itself writes, and matching it keeps a diff against a
 * notebook edited in the browser down to the cell that actually changed rather
 * than the whole file.
 */
export function toSourceLines(text: string): string[] {
  if (text === "") return [];
  const parts = text.split("\n");
  return parts
    .map((line, i) => (i === parts.length - 1 ? line : line + "\n"))
    .filter((l) => l !== "");
}

/** Readable summary of a cell's outputs — never the base64 of an image. */
function renderOutputs(cell: NotebookCell): string[] {
  const outs = cell.outputs;
  if (!Array.isArray(outs) || outs.length === 0) return [];
  const lines: string[] = [];

  for (const raw of outs) {
    const o = raw as Record<string, unknown>;
    const type = String(o["output_type"] ?? "");
    if (type === "stream") {
      const text = o["text"];
      lines.push(...String(Array.isArray(text) ? text.join("") : text ?? "").split("\n"));
    } else if (type === "error") {
      lines.push(String(o["ename"]) + ": " + String(o["evalue"]));
    } else if (type === "execute_result" || type === "display_data") {
      const data = (o["data"] ?? {}) as Record<string, unknown>;
      const plain = data["text/plain"];
      if (plain !== undefined) {
        lines.push(...String(Array.isArray(plain) ? plain.join("") : plain).split("\n"));
      } else {
        // An image or HTML blob. Say what it is; the bytes help nobody.
        lines.push("[" + Object.keys(data).join(", ") + "]");
      }
    }
  }

  const trimmed = lines.filter((l) => l !== "");
  if (trimmed.length <= MAX_OUTPUT_LINES) return trimmed;
  return [
    ...trimmed.slice(0, MAX_OUTPUT_LINES),
    "… " + String(trimmed.length - MAX_OUTPUT_LINES) + " more output lines",
  ];
}

function load(file: string): Notebook {
  const nb = JSON.parse(fs.readFileSync(file, "utf8")) as Notebook;
  if (!Array.isArray(nb.cells)) throw new Error("not a notebook: no cells array");
  return nb;
}

/**
 * Write the notebook back.
 *
 * Two-space indent and a trailing newline, which is what Jupyter writes — any
 * other shape would show every line as changed in the next git diff.
 */
function save(file: string, nb: Notebook): void {
  fs.writeFileSync(file, JSON.stringify(nb, null, 2) + "\n", "utf8");
}

export const readNotebookDefinition: ToolDefinition = {
  name: "read_notebook",
  description:
    "Read a Jupyter notebook (.ipynb) as a numbered list of cells with their " +
    "source and outputs. Use this instead of read_file for notebooks: read_file " +
    "returns the raw JSON, which buries the code in metadata and base64 images.",
  input_schema: {
    type: "object",
    properties: {
      path: { type: "string", description: "Path to the .ipynb file" },
      include_outputs: { type: "boolean", description: "Include cell outputs (default: true)" },
    },
    required: ["path"],
  },
};

export async function readNotebook(input: {
  path: string;
  include_outputs?: boolean;
}): Promise<ToolResult> {
  const file = path.resolve(input.path);
  let nb: Notebook;
  try {
    nb = load(file);
  } catch (err) {
    const why = err instanceof Error ? err.message : String(err);
    return { content: "Could not read notebook " + input.path + ": " + why, isError: true };
  }

  const withOutputs = input.include_outputs !== false;
  const lines: string[] = [input.path + " — " + String(nb.cells.length) + " cell(s)"];

  nb.cells.forEach((cell, i) => {
    const kind = cell.cell_type ?? "code";
    const count = cell.execution_count == null ? " " : String(cell.execution_count);
    lines.push("", "[" + String(i) + "] " + kind + (kind === "code" ? " (exec " + count + ")" : ""));

    const text = cellText(cell);
    lines.push(...(text === "" ? ["    (empty)"] : text.split("\n").map((l) => "    " + l)));

    if (withOutputs) {
      const outs = renderOutputs(cell);
      if (outs.length) lines.push("  out:", ...outs.map((l) => "    " + l));
    }
  });

  return { content: lines.join("\n"), isError: false };
}

export const editNotebookDefinition: ToolDefinition = {
  name: "edit_notebook",
  description:
    "Edit one cell of a Jupyter notebook: replace its source, insert a new cell, " +
    "or delete it. Cells are addressed by the index shown by read_notebook. Only " +
    "the named cell is rewritten; the notebook metadata and every other cell are " +
    "left untouched.",
  input_schema: {
    type: "object",
    properties: {
      path: { type: "string", description: "Path to the .ipynb file" },
      cell: { type: "number", description: "Cell index, as shown by read_notebook" },
      mode: {
        type: "string",
        enum: ["replace", "insert", "delete"],
        description:
          "replace: overwrite the cell source. insert: add a new cell before this " +
          "index (pass the cell count to append). delete: remove the cell.",
      },
      source: { type: "string", description: "New cell contents, for replace and insert" },
      cell_type: {
        type: "string",
        enum: ["code", "markdown", "raw"],
        description: "Type for an inserted cell (default: code)",
      },
    },
    required: ["path", "cell", "mode"],
  },
};

export async function editNotebook(input: {
  path: string;
  cell: number;
  mode: "replace" | "insert" | "delete";
  source?: string;
  cell_type?: "code" | "markdown" | "raw";
}): Promise<ToolResult> {
  const file = path.resolve(input.path);
  let nb: Notebook;
  try {
    nb = load(file);
  } catch (err) {
    const why = err instanceof Error ? err.message : String(err);
    return { content: "Could not read notebook " + input.path + ": " + why, isError: true };
  }

  const n = nb.cells.length;
  const i = input.cell;

  if (input.mode === "insert") {
    // Appending is inserting at the count, so this bound is inclusive.
    if (!Number.isInteger(i) || i < 0 || i > n) {
      return {
        content: "Cell " + String(i) + " is out of range: the notebook has " + String(n) +
          " cell(s), so insert takes 0-" + String(n) + ".",
        isError: true,
      };
    }
    const cell: NotebookCell = {
      cell_type: input.cell_type ?? "code",
      source: toSourceLines(input.source ?? ""),
      metadata: {},
      // nbformat 4.5 requires an id; Jupyter rejects a cell without one.
      id: randomUUID().slice(0, 8),
    };
    if (cell.cell_type === "code") {
      cell.outputs = [];
      cell.execution_count = null;
    }
    nb.cells.splice(i, 0, cell);
    save(file, nb);
    return {
      content: "Inserted a " + cell.cell_type + " cell at index " + String(i) +
        ". The notebook now has " + String(nb.cells.length) + " cell(s).",
      isError: false,
    };
  }

  if (!Number.isInteger(i) || i < 0 || i >= n) {
    return {
      content: "Cell " + String(i) + " is out of range: the notebook has " + String(n) +
        " cell(s) (0-" + String(n - 1) + ").",
      isError: true,
    };
  }

  if (input.mode === "delete") {
    const removed = nb.cells.splice(i, 1)[0];
    save(file, nb);
    return {
      content: "Deleted the " + (removed?.cell_type ?? "cell") + " at index " + String(i) +
        ". The notebook now has " + String(nb.cells.length) + " cell(s).",
      isError: false,
    };
  }

  if (input.source === undefined) {
    return { content: "replace needs a `source`. To empty a cell, pass an empty string.", isError: true };
  }

  const cell = nb.cells[i]!;
  cell.source = toSourceLines(input.source);
  // Stored outputs describe code that no longer exists, and a stale execution
  // count claims a run that never happened for this source.
  if (cell.cell_type === "code") {
    cell.outputs = [];
    cell.execution_count = null;
  }
  save(file, nb);
  return {
    content: "Replaced the source of cell " + String(i) + " (" + cell.cell_type +
      "). Its outputs were cleared, since they described the previous code.",
    isError: false,
  };
}
