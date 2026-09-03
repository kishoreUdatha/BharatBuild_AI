/**
 * Asking the user a question with actual options.
 *
 * The agent could only ask in prose and hope the reply came back in a shape it
 * could act on. So it either guessed — picking Python for a program with no
 * language named, and finding out three turns later that Java was wanted — or
 * it stopped and wrote a paragraph of alternatives that had to be answered in
 * prose and re-interpreted.
 *
 * This gives it a real choice: a question, two to four labelled options, and an
 * answer it does not have to parse.
 *
 * The UI is injected the same way the permission prompt is. The ink TUI holds
 * stdin in raw mode and repaints the screen, so anything that prompts through
 * readline is painted over before it can be answered.
 */

import type { ToolDefinition, ToolResult } from "../filesystem/index.js";

export interface QuestionOption {
  label: string;
  description?: string;
}

export interface PendingQuestion {
  question: string;
  /** Short chip shown beside the question, e.g. "Language" or "Approach". */
  header?: string;
  options: QuestionOption[];
  /** Whether more than one option may be chosen. */
  multiSelect?: boolean;
}

/** Resolves to the chosen labels, or null when the user declined to answer. */
export type QuestionAsker = (q: PendingQuestion) => Promise<string[] | null>;

let externalAsk: QuestionAsker | null = null;

export function setQuestionAsker(asker: QuestionAsker | null): void {
  externalAsk = asker;
}

export function getQuestionAsker(): QuestionAsker | null {
  return externalAsk;
}

export const askUserDefinition: ToolDefinition = {
  name: "ask_user",
  description:
    "Ask the user to choose between options, when the request genuinely left a " +
    "fork open that you cannot settle from the code — which language, which of " +
    "two designs, which file to change. Returns the option they picked. " +
    "Do not use it for something you can determine yourself, for permission to " +
    "run a tool, or to check in on work already agreed: those cost the user a " +
    "decision they should not have to make.",
  input_schema: {
    type: "object",
    properties: {
      question: {
        type: "string",
        description: "The question, phrased so the options are the answer to it.",
      },
      header: {
        type: "string",
        description: "Two or three words naming the decision, e.g. 'Language'.",
      },
      options: {
        type: "array",
        description: "Two to four distinct choices.",
        items: {
          type: "object",
          properties: {
            label: { type: "string", description: "Short name of the option" },
            description: { type: "string", description: "What choosing it means" },
          },
          required: ["label"],
        },
      },
      multiSelect: {
        type: "boolean",
        description: "Allow more than one option to be chosen (default: false)",
      },
    },
    required: ["question", "options"],
  },
};

export async function askUser(input: PendingQuestion): Promise<ToolResult> {
  const options = Array.isArray(input.options) ? input.options.filter((o) => o?.label) : [];

  if (options.length < 2) {
    return {
      content: "ask_user needs at least two options. With one answer there is no question to ask.",
      isError: true,
    };
  }

  const ask = externalAsk;
  if (!ask) {
    // Headless, or a surface that never installed a picker. Say so plainly and
    // tell the model to decide: blocking forever, or silently returning the
    // first option as though it had been chosen, are both worse.
    return {
      content:
        "There is nobody to ask — this session is not interactive. " +
        "Choose the option you judge best, say which you chose and why, and carry on.",
      isError: false,
    };
  }

  const chosen = await ask({ ...input, options });
  if (chosen === null || chosen.length === 0) {
    return {
      content: "The user dismissed the question without choosing. Proceed with your best judgement, and say which way you went.",
      isError: false,
    };
  }

  return {
    content: chosen.length === 1
      ? `The user chose: ${chosen[0]}`
      : `The user chose: ${chosen.join(", ")}`,
    isError: false,
  };
}
