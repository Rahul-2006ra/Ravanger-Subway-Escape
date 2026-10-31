# Your submission folder

This is the only folder you hand in. Everything the organisers need from you lives here.

## What goes in this folder

| File | What it is |
|------|------------|
| `team_info.json` | Your team details (`rahulrkudlur`, Rahul.R) and how to start your bot. |
| `rahulrkudlur.py` | **Main source code file of the bot.** Contains full autonomous strategy and protocol loop. |
| `report.pdf` | Comprehensive strategy and technical report explaining the mathematical formulation. |

## Step by step

1. **Main Bot Source File:**

   The primary Python file is:
   ```
   submission/rahulrkudlur.py
   ```

2. **Team Configuration in `team_info.json`:**

   ```json
   "language": "python",
   "entry_file": "rahulrkudlur.py",
   "build_command": "",
   "run_command": "python rahulrkudlur.py"
   ```


   C++ team:
   ```json
   "language": "cpp",
   "entry_file": "my_bot.cpp",
   "build_command": "g++ -std=c++17 -O2 -I ../third_party my_bot.cpp -o my_bot",
   "run_command": "./my_bot"
   ```
   (On Windows the run command is `my_bot.exe`.)

   For solo participant leave member 2 as it is.

3. **Write your strategy** in the `strategy` function (Python) or `strategy`
   function (C++). Everything else in the file is already done for you.

4. **Test it** (always from the `participant_kit` folder):

   ```
   python tools/check_bot.py --team-info submission/team_info.json
   python practice_arena/run_practice.py --bot "{python} submission/my_bot.py" --bot "{python} sample_bot/python/basic_bot.py" --runs 10
   ```

5. **Submit** this folder the way the organisers announce (WhatsApp group / form).
   Do not rename `team_info.json`. Do not include compiled binaries unless asked.

## Before you submit - checklist

- [ ] `team_info.json` is fully filled in
- [ ] `tools/check_bot.py` says "all checks passed"
- [ ] Your bot beats (or at least matches) the sample bot in the practice arena over 10+ maps
- [ ] Your bot answers well under 1 second on every tick (look at the `MaxMs` column)
- [ ] Your bot prints **only** the JSON answer to stdout (debug text goes to stderr)
- [ ] The program uses no internet, no files outside this folder, no manual input

Good luck!
