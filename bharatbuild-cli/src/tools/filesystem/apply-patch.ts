import fs from "fs";
import path from "path";

export const applyPatchDefinition = {
  name: "apply_patch",
  description:
    "Apply a targeted string replacement to a file (str_replace). " +
    "Finds the exact occurrence of old_string and replaces it with new_string. " +
    "Use this for precise edits instead of rewriting the whole file. " +
    "Fails if old_string is not found or is ambiguous (occurs more than once — use a larger unique context in that case).",
  input_schema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to the file to edit (absolute or relative to working directory).",
      },
      old_string: {
        type: "string",
        description: "The exact string to find and replace. Must match character-for-character including whitespace.",
      },
      new_string: {
        type: "string",
        description: "The replacement string. Use empty string to delete old_string.",
      },
    },
    required: ["file_path", "old_string", "new_string"],
  },
};

export async function applyPatch(input: {
  file_path: string;
  old_string: string;
  new_string: string;
}): Promise<{ content: string; isError: boolean }> {
  const p = path.resolve(input.file_path);
  try {
    if (!fs.existsSync(p)) {
      return { content: `File not found: ${input.file_path}`, isError: true };
    }
    const c = fs.readFileSync(p, "utf8");

    // Count occurrences — ambiguous matches cause hard-to-debug bugs
    const occurrences = c.split(input.old_string).length - 1;
    if (occurrences === 0) {
      return {
        content: `String not found in ${input.file_path}. Make sure old_string matches exactly (check whitespace and indentation).`,
        isError: true,
      };
    }
    if (occurrences > 1) {
      return {
        content: `old_string appears ${occurrences} times in ${input.file_path}. Expand the context to make it unique.`,
        isError: true,
      };
    }

    fs.writeFileSync(p, c.replace(input.old_string, input.new_string), "utf8");
    const linesChanged = (input.new_string.split("\n").length - input.old_string.split("\n").length);
    const sign = linesChanged >= 0 ? `+${linesChanged}` : String(linesChanged);
    return { content: `Patched ${input.file_path} (${sign} lines)`, isError: false };
  } catch (err) {
    return { content: `Error patching file: ${err instanceof Error ? err.message : err}`, isError: true };
  }
}
