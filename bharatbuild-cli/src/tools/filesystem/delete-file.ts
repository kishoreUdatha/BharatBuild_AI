import fs from "fs";
import path from "path";

export const deleteFileDefinition = {
  name: "delete_file",
  description:
    "Delete a file or directory. " +
    "Set recursive=true to delete a non-empty directory and all its contents. " +
    "This operation is irreversible — use with care.",
  input_schema: {
    type: "object" as const,
    properties: {
      path: {
        type: "string",
        description: "Path to the file or directory to delete.",
      },
      recursive: {
        type: "boolean",
        description: "Delete directory and all contents recursively (default: false). Required for non-empty directories.",
      },
    },
    required: ["path"],
  },
};

export async function deleteFile(input: {
  path: string;
  recursive?: boolean;
}): Promise<{ content: string; isError: boolean }> {
  const p = path.resolve(input.path);
  try {
    const stat = fs.statSync(p);
    if (stat.isDirectory()) {
      if (!input.recursive) {
        return {
          content: `"${input.path}" is a directory. Set recursive:true to delete it and its contents.`,
          isError: true,
        };
      }
      fs.rmSync(p, { recursive: true, force: true });
      return { content: `Deleted directory: ${input.path}`, isError: false };
    }
    fs.unlinkSync(p);
    return { content: `Deleted: ${input.path}`, isError: false };
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") {
      return { content: `File not found: ${input.path}`, isError: true };
    }
    return { content: `Error deleting: ${err instanceof Error ? err.message : err}`, isError: true };
  }
}
