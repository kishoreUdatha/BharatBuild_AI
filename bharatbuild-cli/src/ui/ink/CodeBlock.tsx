/**
 * A fenced code block from an assistant reply.
 *
 * Split out so it can own a hook: the highlighter resolves asynchronously and
 * the block has to re-render when its grammar arrives.
 */

import React from "react";
import { Box } from "ink";
import { TokenLine, useHighlightedBlock, detectLanguage } from "./syntax.js";

export function CodeBlock({ code, lang }: { code: string; lang?: string }): React.ReactElement {
  const lines = code.split("\n");
  const tokens = useHighlightedBlock(lines, detectLanguage(undefined, lang));
  return (
    <Box flexDirection="column">
      {lines.map((line, i) => (
        <TokenLine key={i} tokens={tokens[i] ?? [{ text: line }]} />
      ))}
    </Box>
  );
}
