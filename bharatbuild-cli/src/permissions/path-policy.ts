import path from "path";

/**
 * Paths the agent must never write to or delete.
 *
 * The previous list was `["/etc","/sys","/proc","/boot","C:\\Windows","C:\\System32"]`
 * compared with a plain `startsWith` against `path.resolve()`, which had three
 * holes:
 *   - On Windows, `path.resolve("/etc/passwd")` yields `D:\etc\passwd`, so the
 *     POSIX entries never matched anything.
 *   - Windows paths are case-insensitive, so `c:\windows\...` slipped past the
 *     capitalised literal.
 *   - `C:\System32` is not a real location (it lives under `C:\Windows`), and
 *     system dirs on any drive other than C: were unguarded.
 *
 * `startsWith` on its own also treated `/etcetera` as inside `/etc`, so
 * matching is done on path segments.
 */

const POSIX_PROTECTED = ["/etc", "/sys", "/proc", "/boot", "/dev", "/usr/bin", "/usr/sbin", "/sbin", "/bin"];

/** Windows system directories, matched relative to whatever drive they are on. */
const WINDOWS_PROTECTED = ["windows", "program files", "program files (x86)", "programdata"];

const isWindows = process.platform === "win32";

/** Split a resolved path into comparable segments. */
function segments(p: string): string[] {
  return p.split(/[\\/]+/).filter(Boolean);
}

export function isProtectedPath(filePath: string): boolean {
  if (!filePath || !filePath.trim()) return false;

  const resolved = path.resolve(filePath);

  if (isWindows) {
    const segs = segments(resolved).map((s) => s.toLowerCase());
    // segs[0] is the drive ("c:"); the system directory is the next segment.
    const top = segs[1];
    if (top && WINDOWS_PROTECTED.includes(top)) return true;

    // A POSIX-style path typed on Windows resolves onto the current drive and
    // would otherwise look ordinary. Treat the literal intent as protected.
    const raw = filePath.replace(/\\/g, "/").toLowerCase();
    if (POSIX_PROTECTED.some((p) => raw === p || raw.startsWith(`${p}/`))) return true;

    return false;
  }

  // POSIX: compare segment-wise so "/etcetera" is not inside "/etc".
  const segs = segments(resolved);
  return POSIX_PROTECTED.some((p) => {
    const target = segments(p);
    return target.every((t, i) => segs[i] === t) && segs.length >= target.length;
  });
}

export function isOutsideProject(filePath: string, projectDir: string): boolean {
  const rel = path.relative(path.resolve(projectDir), path.resolve(filePath));
  // `path.relative` gives a "..\" prefix when the target escapes the root, and
  // an absolute path when the two are on different drives.
  return rel.startsWith("..") || path.isAbsolute(rel);
}
