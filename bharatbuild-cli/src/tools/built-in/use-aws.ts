/**
 * BharatBuild CLI — Built-in Tool: use_aws
 * Make an AWS CLI API call with the specified service, operation, and parameters.
 * All arguments MUST conform to the AWS CLI specification.
 */

import { execFile } from "child_process";
import { promisify } from "util";
import type { BuiltInTool, ToolResult } from "./types.js";

const execFileAsync = promisify(execFile);

const AWS_TIMEOUT_MS = 60_000;
const MAX_OUTPUT = 100_000;

export const useAwsTool: BuiltInTool = {
  definition: {
    name: "use_aws",
    source: "built-in",
    status: "approval_required",
    description: "Make an AWS CLI api call with the specified service, operation, and parameters. All arguments MUST conform to the AWS CLI specification.",
    parameters: {
      type: "object",
      properties: {
        service_name: {
          type: "string",
          description: "The name of the AWS service. If you want to query s3, you should use s3api if possible. Must not start with a dash.",
        },
        operation_name: {
          type: "string",
          description: "The name of the operation to perform.",
        },
        parameters: {
          type: "object",
          description: "The parameters for the operation. Keys MUST conform to AWS CLI specification. Prefer JSON syntax over shorthand.",
        },
        positional_args: {
          type: "array",
          items: { type: "string" },
          description: "Positional arguments for high-level commands (e.g., s3 cp, s3 mv). Passed without -- prefix.",
        },
        region: {
          type: "string",
          description: "Region name for calling the operation on AWS.",
        },
        profile_name: {
          type: "string",
          description: "AWS profile name to use from ~/.aws/credentials. Defaults to default profile.",
        },
        label: {
          type: "string",
          description: "Human readable description of the API call being made.",
        },
      },
      required: ["region", "service_name", "operation_name", "label"],
    },
  },

  async execute(params: Record<string, unknown>, signal?: AbortSignal): Promise<ToolResult> {
    const serviceName = params["service_name"] as string;
    const operationName = params["operation_name"] as string;
    const region = params["region"] as string;
    const label = params["label"] as string;
    const awsParams = params["parameters"] as Record<string, unknown> | undefined;
    const positionalArgs = params["positional_args"] as string[] | undefined;
    const profileName = params["profile_name"] as string | undefined;

    if (!serviceName) return { content: "Error: 'service_name' is required.", isError: true };
    if (!operationName) return { content: "Error: 'operation_name' is required.", isError: true };
    if (!region) return { content: "Error: 'region' is required.", isError: true };
    if (!label) return { content: "Error: 'label' is required.", isError: true };

    if (serviceName.startsWith("-")) {
      return { content: "Error: service_name must not start with a dash.", isError: true };
    }

    // Build the AWS CLI command
    const args: string[] = [serviceName, operationName];

    // Add positional args first (for s3 commands)
    if (positionalArgs) {
      args.push(...positionalArgs);
    }

    // Add region
    args.push("--region", region);

    // Add profile if specified
    if (profileName) {
      args.push("--profile", profileName);
    }

    // Add parameters
    if (awsParams) {
      for (const [key, value] of Object.entries(awsParams)) {
        const flag = `--${key}`;
        if (value === "" || value === true) {
          // Boolean flag
          args.push(flag);
        } else if (typeof value === "object") {
          args.push(flag, JSON.stringify(value));
        } else {
          args.push(flag, String(value));
        }
      }
    }

    // Add output format
    args.push("--output", "json");

    try {
      const { stdout, stderr } = await execFileAsync("aws", args, {
        timeout: AWS_TIMEOUT_MS,
        maxBuffer: MAX_OUTPUT * 2,
        signal,
        env: process.env,
      });

      const out = (stdout || "").slice(0, MAX_OUTPUT);
      const err = (stderr || "").slice(0, MAX_OUTPUT);

      let result = "";
      if (label) result += `[${label}]\n\n`;
      if (out) {
        // Try to parse and pretty-print JSON
        try {
          const parsed = JSON.parse(out);
          result += JSON.stringify(parsed, null, 2);
        } catch {
          result += out;
        }
      }
      if (err && !out) result += err;
      if (!out && !err) result += "(command completed with no output)";

      return { content: result, isError: false };
    } catch (err: unknown) {
      const e = err as NodeJS.ErrnoException & { stdout?: string; stderr?: string; code?: string | number };

      if (signal?.aborted) {
        return { content: "AWS command was cancelled.", isError: false };
      }

      // Check if AWS CLI is not installed
      if (e.code === "ENOENT") {
        return {
          content: "Error: AWS CLI is not installed or not in PATH. Install it from: https://aws.amazon.com/cli/",
          isError: true,
        };
      }

      const errMsg = (e.stderr || e.message || "Unknown error").slice(0, MAX_OUTPUT);
      return { content: `AWS CLI error:\n${errMsg}`, isError: true };
    }
  },
};
