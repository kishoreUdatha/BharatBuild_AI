import { execSync, spawnSync } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import chalk from "chalk";

export interface ClipboardContent {
  type: "text" | "image" | "empty";
  text?: string;
  imagePath?: string;
  imageBase64?: string;
  mimeType?: string;
}

/**
 * Read text from clipboard using clipboardy or OS-native fallback.
 */
export async function readClipboardText(): Promise<string | null> {
  try {
    const { default: clipboardy } = await import("clipboardy");
    return await clipboardy.read();
  } catch {
    // fallback per platform
    try {
      if (process.platform === "win32") {
        return execSync("powershell -command Get-Clipboard", { encoding: "utf8" }).trim();
      } else if (process.platform === "darwin") {
        return execSync("pbpaste", { encoding: "utf8" });
      } else {
        return execSync("xclip -selection clipboard -o 2>/dev/null || xsel --clipboard --output 2>/dev/null", { encoding: "utf8" });
      }
    } catch { return null; }
  }
}

/**
 * Read image from clipboard (saves to a temp PNG file).
 * Returns the temp file path or null if no image in clipboard.
 */
export async function readClipboardImage(): Promise<string | null> {
  const tmpFile = path.join(os.tmpdir(), `bharatbuild-paste-${Date.now()}.png`);

  try {
    if (process.platform === "win32") {
      // PowerShell can read image from clipboard
      const script = `
Add-Type -AssemblyName System.Windows.Forms;
$img = [System.Windows.Forms.Clipboard]::GetImage();
if ($img -ne $null) {
  $img.Save('${tmpFile.replace(/\\/g, "\\\\")}');
  Write-Output 'saved';
} else {
  Write-Output 'empty';
}`;
      const result = spawnSync("powershell", ["-Command", script], { encoding: "utf8" });
      if (result.stdout.trim() === "saved" && fs.existsSync(tmpFile)) return tmpFile;
      return null;
    } else if (process.platform === "darwin") {
      // macOS: use osascript to check + pngpaste if available, else screencapture
      try {
        execSync(`pngpaste "${tmpFile}" 2>/dev/null`);
        if (fs.existsSync(tmpFile)) return tmpFile;
      } catch {}
      try {
        const hasImg = execSync(`osascript -e 'clipboard info' 2>/dev/null`).toString();
        if (hasImg.includes("«class PNGf»") || hasImg.includes("TIFF")) {
          execSync(`osascript -e 'set the clipboard to (the clipboard as JPEG picture)' 2>/dev/null`);
        }
      } catch {}
      return null;
    } else {
      // Linux: xclip
      try {
        spawnSync("xclip", ["-selection", "clipboard", "-t", "image/png", "-o"], {
          encoding: "buffer",
          stdio: ["ignore", fs.openSync(tmpFile, "w"), "ignore"],
        });
        if (fs.existsSync(tmpFile) && fs.statSync(tmpFile).size > 0) return tmpFile;
      } catch {}
      return null;
    }
  } catch { return null; }
}

/**
 * Read whatever is in the clipboard — image first, then text.
 */
export async function readClipboard(): Promise<ClipboardContent> {
  // Try image first
  const imgPath = await readClipboardImage();
  if (imgPath) {
    const imageBase64 = fs.readFileSync(imgPath).toString("base64");
    return { type: "image", imagePath: imgPath, imageBase64, mimeType: "image/png" };
  }

  // Try text
  const text = await readClipboardText();
  if (text && text.trim()) return { type: "text", text };

  return { type: "empty" };
}

/**
 * Write text to clipboard.
 */
export async function writeClipboard(text: string): Promise<boolean> {
  try {
    const { default: clipboardy } = await import("clipboardy");
    await clipboardy.write(text);
    return true;
  } catch {
    try {
      if (process.platform === "win32") {
        spawnSync("powershell", ["-command", `Set-Clipboard -Value '${text.replace(/'/g, "''")}'`]);
      } else if (process.platform === "darwin") {
        const child = spawnSync("pbcopy", { input: text });
        return child.status === 0;
      } else {
        const child = spawnSync("xclip", ["-selection", "clipboard"], { input: text });
        return child.status === 0;
      }
      return true;
    } catch { return false; }
  }
}

/**
 * Handle the /paste slash command in TUI.
 */
export async function handlePasteCommand(): Promise<{ type: "text" | "image" | "empty"; content?: string; imagePath?: string }> {
  console.log(chalk.dim("\n  📋 Reading clipboard..."));
  const clip = await readClipboard();

  if (clip.type === "empty") {
    console.log(chalk.yellow("\n  ⚠  Clipboard is empty.\n"));
    return { type: "empty" };
  }

  if (clip.type === "image" && clip.imagePath) {
    const size = fs.statSync(clip.imagePath).size;
    console.log(chalk.green(`\n  ✓ Image pasted from clipboard`));
    console.log(chalk.dim(`    Path: ${clip.imagePath}`));
    console.log(chalk.dim(`    Size: ${(size / 1024).toFixed(1)} KB\n`));
    return { type: "image", imagePath: clip.imagePath };
  }

  if (clip.type === "text" && clip.text) {
    const lines = clip.text.split("\n");
    const preview = lines.slice(0, 3).join("\n");
    const isLong = lines.length > 3 || clip.text.length > 200;

    if (isLong) {
      console.log(chalk.green(`\n  ✓ Long text pasted (${lines.length} lines, ${clip.text.length} chars)`));
      console.log(chalk.dim("  ┌─ Preview ─────────────────────────────"));
      preview.split("\n").forEach((l) => console.log(chalk.dim(`  │ ${l.slice(0, 70)}`)));
      console.log(chalk.dim("  └───────────────────────────────────────\n"));
    } else {
      console.log(chalk.green(`\n  ✓ Text pasted from clipboard\n`));
    }
    return { type: "text", content: clip.text };
  }

  return { type: "empty" };
}

/**
 * Handle /copy — copy last assistant response to clipboard.
 */
export async function copyToClipboard(text: string): Promise<void> {
  const ok = await writeClipboard(text);
  if (ok) console.log(chalk.green("\n  ✓ Copied to clipboard\n"));
  else console.log(chalk.red("\n  ✗ Failed to copy to clipboard\n"));
}
