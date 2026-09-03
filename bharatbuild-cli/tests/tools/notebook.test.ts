/**
 * Jupyter notebooks.
 *
 * A .ipynb is JSON, so read_file returned the raw document — metadata, base64
 * image outputs, execution counts, and source split into one-line strings. The
 * code was buried, and editing meant rewriting that JSON by hand, which
 * corrupts the file the first time a quote is mismatched.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  readNotebook, editNotebook, cellText, toSourceLines,
} from "../../src/tools/notebook/index.js";

let dir: string;
let file: string;

/** A notebook shaped like a real one: markdown, code, outputs, an image. */
function makeNotebook(): unknown {
  return {
    cells: [
      { cell_type: "markdown", source: ["# Sales analysis\n"], metadata: {} },
      {
        cell_type: "code", execution_count: 1, metadata: {},
        source: ["import pandas as pd\n", "df = pd.read_csv('sales.csv')\n"],
        outputs: [{ output_type: "stream", name: "stdout", text: ["loaded 1200 rows\n"] }],
      },
      {
        cell_type: "code", execution_count: 2, metadata: {},
        source: ["df.plot()\n"],
        outputs: [{
          output_type: "execute_result",
          data: { "text/plain": ["<Axes: >"], "image/png": "iVBORw0KGgoAAAANSUhEUg" + "A".repeat(4000) },
          metadata: {},
        }],
      },
    ],
    metadata: { kernelspec: { name: "python3", display_name: "Python 3" } },
    nbformat: 4,
    nbformat_minor: 5,
  };
}

const read = () => JSON.parse(fs.readFileSync(file, "utf8")) as any;

beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bb-nb-"));
  file = path.join(dir, "analysis.ipynb");
  fs.writeFileSync(file, JSON.stringify(makeNotebook(), null, 1));
});
afterEach(() => {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

describe("reading one", () => {
  it("shows cells with their index and type", async () => {
    const r = await readNotebook({ path: file });
    expect(r.isError).toBe(false);
    expect(r.content).toContain("[0] markdown");
    expect(r.content).toContain("[1] code (exec 1)");
  });

  it("shows the source as code, not as JSON string fragments", async () => {
    const r = await readNotebook({ path: file });
    expect(r.content).toContain("import pandas as pd");
    expect(r.content, "no JSON quoting").not.toContain('["import pandas');
  });

  it("shows stream output", async () => {
    expect((await readNotebook({ path: file })).content).toContain("loaded 1200 rows");
  });

  it("never returns the base64 of an image", async () => {
    // The whole reason this tool exists: one plot output was 4 KB of base64
    // that pushed the actual code out of view.
    const r = await readNotebook({ path: file });
    expect(r.content).not.toContain("iVBORw0KGgo");
    expect(r.content.length).toBeLessThan(1000);
  });

  it("prefers the text rendering of a result that has both", async () => {
    expect((await readNotebook({ path: file })).content).toContain("<Axes: >");
  });

  it("can leave outputs out entirely", async () => {
    const r = await readNotebook({ path: file, include_outputs: false });
    expect(r.content).not.toContain("loaded 1200 rows");
    expect(r.content).toContain("import pandas as pd");
  });

  it("reports a file that is not a notebook rather than throwing", async () => {
    const bad = path.join(dir, "notes.txt");
    fs.writeFileSync(bad, "just text");
    const r = await readNotebook({ path: bad });
    expect(r.isError).toBe(true);
    expect(r.content).toMatch(/could not read/i);
  });
});

describe("editing a cell", () => {
  it("replaces the source and leaves everything else alone", async () => {
    await editNotebook({ path: file, cell: 1, mode: "replace", source: "import polars as pl" });
    const nb = read();
    expect(cellText(nb.cells[1])).toBe("import polars as pl");
    expect(nb.cells).toHaveLength(3);
    expect(nb.metadata.kernelspec.name, "notebook metadata untouched").toBe("python3");
    expect(nb.nbformat).toBe(4);
  });

  it("clears outputs when the code they came from is replaced", async () => {
    // Stale outputs describe code that no longer exists, and a stale execution
    // count claims a run that never happened for this source.
    await editNotebook({ path: file, cell: 1, mode: "replace", source: "print('new')" });
    const cell = read().cells[1];
    expect(cell.outputs).toEqual([]);
    expect(cell.execution_count).toBeNull();
  });

  it("stores source the way Jupyter does, as lines keeping their newlines", async () => {
    // A different shape would show every line as changed in the next git diff.
    await editNotebook({ path: file, cell: 1, mode: "replace", source: "a = 1\nb = 2" });
    expect(read().cells[1].source).toEqual(["a = 1\n", "b = 2"]);
  });

  it("inserts a cell at an index", async () => {
    await editNotebook({ path: file, cell: 1, mode: "insert", cell_type: "markdown", source: "## Setup" });
    const nb = read();
    expect(nb.cells).toHaveLength(4);
    expect(nb.cells[1].cell_type).toBe("markdown");
    expect(cellText(nb.cells[1])).toBe("## Setup");
  });

  it("gives an inserted cell an id, which nbformat 4.5 requires", async () => {
    // Jupyter refuses to open a notebook with a cell that has no id.
    await editNotebook({ path: file, cell: 0, mode: "insert", source: "x = 1" });
    expect(typeof read().cells[0].id).toBe("string");
  });

  it("appends when the index is the cell count", async () => {
    await editNotebook({ path: file, cell: 3, mode: "insert", source: "done" });
    const nb = read();
    expect(nb.cells).toHaveLength(4);
    expect(cellText(nb.cells[3])).toBe("done");
  });

  it("deletes a cell", async () => {
    await editNotebook({ path: file, cell: 0, mode: "delete" });
    const nb = read();
    expect(nb.cells).toHaveLength(2);
    expect(nb.cells[0].cell_type).toBe("code");
  });
});

describe("when the request is wrong", () => {
  it("refuses an index past the end, naming the range", async () => {
    const r = await editNotebook({ path: file, cell: 99, mode: "delete" });
    expect(r.isError).toBe(true);
    expect(r.content).toContain("0-2");
  });

  it("refuses a negative index", async () => {
    expect((await editNotebook({ path: file, cell: -1, mode: "delete" })).isError).toBe(true);
  });

  it("allows insert at the count but not past it", async () => {
    expect((await editNotebook({ path: file, cell: 3, mode: "insert", source: "ok" })).isError).toBe(false);
    expect((await editNotebook({ path: file, cell: 99, mode: "insert", source: "no" })).isError).toBe(true);
  });

  it("says what is missing when replace has no source", async () => {
    const r = await editNotebook({ path: file, cell: 0, mode: "replace" });
    expect(r.isError).toBe(true);
    expect(r.content).toMatch(/source/);
  });

  it("leaves the notebook untouched when it refuses", async () => {
    const before = fs.readFileSync(file, "utf8");
    await editNotebook({ path: file, cell: 99, mode: "delete" });
    expect(fs.readFileSync(file, "utf8")).toBe(before);
  });

  it("keeps the file valid JSON through a run of edits", async () => {
    await editNotebook({ path: file, cell: 1, mode: "replace", source: 'x = "quoted \\" string"' });
    await editNotebook({ path: file, cell: 0, mode: "insert", source: "# top" });
    await editNotebook({ path: file, cell: 2, mode: "delete" });
    expect(() => read()).not.toThrow();
    expect(read().cells.length).toBeGreaterThan(0);
  });
});

describe("source conversion", () => {
  it("keeps newlines on every line but the last", () => {
    expect(toSourceLines("a\nb\nc")).toEqual(["a\n", "b\n", "c"]);
  });

  it("represents an empty cell as no lines", () => {
    expect(toSourceLines("")).toEqual([]);
  });

  it("reads back either storage form", () => {
    expect(cellText({ cell_type: "code", source: ["a\n", "b"] })).toBe("a\nb");
    expect(cellText({ cell_type: "code", source: "a\nb" })).toBe("a\nb");
  });
});
