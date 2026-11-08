import { spawnSync } from "node:child_process";
import { writeSync } from "node:fs";

function git(args: string[], cwd?: string): { status: number; out: string } {
  const run = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (run.error) throw run.error;
  return { status: run.status ?? 1, out: run.stdout.trim() };
}

function fail(message: string): never {
  writeSync(2, message + "\n");
  process.exit(1);
}

// Run from the checkout (a script node's working directory). The messages below are the design's, verbatim
// (gauntlet-intake-design.md, ".shared/working-folder.ts").
export function requireIgnored(options?: { committed?: boolean }): void {
  const top = git(["rev-parse", "--show-toplevel"]);
  if (top.status !== 0) fail("Gauntlet failed because the working directory is not inside a git repository.");
  const root = top.out;

  const tracked = git(["ls-files", "--", "gauntlet"], root).out.split("\n")[0];
  if (tracked) {
    fail(
      `Gauntlet failed because git tracks ${root}/${tracked} under its working folder. Run \`git rm --cached ${tracked}\` (and add gauntlet/ to .gitignore if it is not ignored), commit, and restart the run.`,
    );
  }

  // -v names the file, line and pattern of the rule that decides; a "!" pattern means the last match un-ignores.
  const check = git(["check-ignore", "-v", "gauntlet/"], root);
  const [rule] = check.out.split("\t");
  const [source, , ...pattern] = rule.split(":");
  if (check.status !== 0 || pattern.join(":").startsWith("!")) {
    fail(
      `Gauntlet failed because its working folder, ${root}/gauntlet/, sits in the main repo. Add it to .gitignore and restart the run.`,
    );
  }

  // A tree shares .git/info/exclude and the global excludes file; it holds a .gitignore only as HEAD commits it.
  if (options?.committed && source.split("/").pop() === ".gitignore") {
    const head = git(["show", `HEAD:${source}`], root);
    if (head.status !== 0 || !head.out.split("\n").includes(pattern.join(":"))) {
      fail(
        `Gauntlet failed because the rule keeping ${root}/gauntlet/ out of git sits in ${root}/${source}, which is not committed, and the run's tree holds only committed files. Commit ${source} and restart the run.`,
      );
    }
  }
}
