/**
 * A minimal virtual terminal.
 *
 * Counting occurrences in the raw output stream cannot tell a repaint from a
 * duplicate: Ink rewrites the whole frame on every render, so a healthy UI and
 * a broken one both show N copies in the bytes. The only way to know what the
 * user sees is to apply the escape codes to a screen buffer the way a terminal
 * does, then read the buffer.
 *
 * Supports the subset Ink emits: cursor movement, line/display erase, and
 * newline scrolling. SGR colour codes are consumed and dropped — this models
 * layout, not appearance.
 */

const ESC = String.fromCharCode(27);

export class VirtualTerminal {
  private rows: string[][];
  private cursorRow = 0;
  private cursorCol = 0;

  constructor(private readonly cols: number, private readonly height: number) {
    this.rows = Array.from({ length: height }, () => new Array(cols).fill(" "));
  }

  private scroll(): void {
    this.rows.shift();
    this.rows.push(new Array(this.cols).fill(" "));
    this.cursorRow = this.height - 1;
  }

  private put(ch: string): void {
    if (this.cursorCol >= this.cols) {
      this.cursorCol = 0;
      this.cursorRow++;
    }
    while (this.cursorRow >= this.height) this.scroll();
    this.rows[this.cursorRow]![this.cursorCol] = ch;
    this.cursorCol++;
  }

  write(data: string): void {
    let i = 0;
    while (i < data.length) {
      const ch = data[i]!;

      if (ch === ESC && data[i + 1] === "[") {
        const m = /^\x1b\[([0-9;?]*)([A-Za-z])/.exec(data.slice(i));
        if (!m) { i++; continue; }
        const params = m[1]!.split(";").filter(Boolean).map(Number);
        const n = params[0] ?? 1;
        switch (m[2]) {
          case "A": this.cursorRow = Math.max(0, this.cursorRow - n); break;
          case "B": this.cursorRow = Math.min(this.height - 1, this.cursorRow + n); break;
          case "C": this.cursorCol = Math.min(this.cols - 1, this.cursorCol + n); break;
          case "D": this.cursorCol = Math.max(0, this.cursorCol - n); break;
          case "G": this.cursorCol = Math.max(0, (params[0] ?? 1) - 1); break;
          case "H": {
            this.cursorRow = Math.max(0, (params[0] ?? 1) - 1);
            this.cursorCol = Math.max(0, (params[1] ?? 1) - 1);
            break;
          }
          case "J": {
            const mode = params[0] ?? 0;
            if (mode === 2 || mode === 3) {
              this.rows = Array.from({ length: this.height }, () => new Array(this.cols).fill(" "));
              this.cursorRow = 0; this.cursorCol = 0;
            } else if (mode === 0) {
              for (let c = this.cursorCol; c < this.cols; c++) this.rows[this.cursorRow]![c] = " ";
              for (let r = this.cursorRow + 1; r < this.height; r++) {
                this.rows[r] = new Array(this.cols).fill(" ");
              }
            }
            break;
          }
          case "K": {
            const mode = params[0] ?? 0;
            const row = this.rows[this.cursorRow]!;
            if (mode === 0) for (let c = this.cursorCol; c < this.cols; c++) row[c] = " ";
            else if (mode === 1) for (let c = 0; c <= this.cursorCol; c++) row[c] = " ";
            else row.fill(" ");
            break;
          }
          default: break; // SGR and cursor visibility: no layout effect.
        }
        i += m[0].length;
        continue;
      }

      if (ch === "\n") { this.cursorRow++; this.cursorCol = 0; while (this.cursorRow >= this.height) this.scroll(); i++; continue; }
      if (ch === "\r") { this.cursorCol = 0; i++; continue; }
      if (ch === ESC) { i += 2; continue; }

      this.put(ch);
      i++;
    }
  }

  /** What is actually on screen, trailing blanks trimmed. */
  screen(): string {
    return this.rows.map((r) => r.join("").replace(/\s+$/, "")).join("\n");
  }

  /** How many times `needle` is visible on screen right now. */
  countVisible(needle: string): number {
    return this.screen().split(needle).length - 1;
  }

  /** 1-indexed row of the last line containing `needle`, or 0. */
  lastRowOf(needle: string): number {
    const lines = this.rows.map((r) => r.join(""));
    for (let i = lines.length - 1; i >= 0; i--) {
      if (lines[i]!.includes(needle)) return i + 1;
    }
    return 0;
  }
}
