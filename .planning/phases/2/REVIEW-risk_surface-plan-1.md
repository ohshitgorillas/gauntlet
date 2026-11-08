{ "findings": [
    { "file": ".shared/working-folder.ts",
      "line": 40,
      "severity": "medium",
      "claim": "The committed branch decides whether a rule comes from a repo .gitignore only by checking that the source's basename is \".gitignore\". So a global excludes file named .gitignore (core.excludesFile=~/.gitignore) is treated as an uncommitted repo .gitignore, and the run fails. The design says the global excludes file must pass with committed.",
      "failure_scenario": "Set core.excludesFile to /home/u/.gitignore holding 'gauntlet/', with no repo rule. `git check-ignore -v gauntlet/` then prints '/home/u/.gitignore:1:gauntlet/\\tgauntlet/' with exit 0 (reproduced with a temp repo). source.split('/').pop() is '.gitignore', so the code runs `git show HEAD:/home/u/.gitignore`, which exits non-zero. requireIgnored({committed:true}) then exits 1 with 'Gauntlet failed because the rule keeping <root>/gauntlet/ out of git sits in <root>//home/u/.gitignore, which is not committed'. gauntlet-run's guard stops even though the run's tree shares that excludes file (gauntlet-intake-design.md lines 59-61)." }
  ]
}
