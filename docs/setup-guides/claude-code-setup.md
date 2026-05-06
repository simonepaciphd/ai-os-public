# Claude Code setup guide

This guide walks you through downloading the AI Operating System public mirror and running its setup protocol with Claude Code.

Approximate time: 30–45 minutes, most of it spent answering interview questions.

## Prerequisites

1. **Claude Code installed.** Follow the official install instructions at https://docs.claude.com/claude-code. Verify it works by running `claude --version` in a terminal — you should see a version number.

2. **A Claude account with API access** (Claude Pro, Anthropic API key, or equivalent). The first `claude` invocation will walk you through authentication.

3. **About 200 MB of free disk space** (the library is small; this leaves headroom for the substitution manifest and setup artifacts).

You do *not* need prior terminal experience beyond following the steps below — but you do need to know how to open one. Where to find your terminal:

- **Windows.** Press the `Windows` key, type "Terminal" or "PowerShell", and open the result.
- **macOS.** Press `Cmd+Space`, type "Terminal", and press Enter.
- **Linux.** Most desktops have a Terminal app in the application menu; on GNOME, press `Ctrl+Alt+T`.

## Step 1 — Download the files

Two options. If you've never used `git` before, use Option A.

### Option A — Download as ZIP (no terminal required)

1. Open https://github.com/simonepaciphd/ai-os-public in your web browser.
2. Click the green **Code** button near the top right of the page.
3. In the dropdown, click **Download ZIP**.
4. Save the file to your computer.

### Option B — Clone with git (if you already have git installed)

In a terminal:

```
git clone https://github.com/simonepaciphd/ai-os-public.git
```

This creates a folder named `ai-os-public` in your current directory.

## Step 2 — Choose where to put the files

The library will live at this folder for the long term — the setup protocol will record the path in its manifest, and you'll point Claude Code at it from any project you open later. Pick a location you'll remember and have full write access to.

**Recommended locations:**

- **Windows.** `C:\Users\<your-name>\Documents\AI-OS\` or `C:\Users\<your-name>\AI-OS\`.
- **macOS.** `~/AI-OS/` (i.e., `/Users/<your-name>/AI-OS/`) or `~/Documents/AI-OS/`.
- **Linux.** `~/AI-OS/` or `~/projects/AI-OS/`.

**Where NOT to put it:**

- Inside `~/.claude/` (the Claude Code harness folder). The setup protocol creates a connection between the library and the harness — they need to be separate folders.
- Inside a temporary or downloads folder you periodically clean out.
- Inside a folder you don't have write access to (system folders, read-only network shares).

**If you used Option A (ZIP):** unzip the downloaded file. The unzipped folder will be named `ai-os-public-main` by default. Move and rename it to your chosen location — for example, on Windows the final path might be `C:\Users\<your-name>\AI-OS\public\` (after renaming `ai-os-public-main` to `public`).

**If you used Option B (git clone):** navigate to your chosen parent location in the terminal first, then clone:

```
cd ~/AI-OS/
git clone https://github.com/simonepaciphd/ai-os-public.git public
```

This creates `~/AI-OS/public/`.

## Step 3 — Open a terminal inside the folder

You need a terminal whose current directory is the folder you just placed the files in.

- **Windows.** Open File Explorer and navigate to your library folder (e.g., `C:\Users\<your-name>\AI-OS\public\`). Click once on the address bar at the top of the window to highlight the path, type `cmd` or `powershell`, and press Enter. A terminal will open already inside that folder.
- **macOS.** Open Finder and navigate to your library folder. Right-click the folder → **Services** → **New Terminal at Folder**. (If you don't see this option, enable it in System Settings → Keyboard → Keyboard Shortcuts → Services.)
- **Linux.** Most file managers offer "Open Terminal Here" via right-click. Otherwise, open a fresh terminal and run `cd /path/to/your/folder`.

Verify you're in the right place by running `ls` (macOS / Linux) or `dir` (Windows). You should see folders named `skills`, `personas`, `agents`, and files like `CLAUDE.md`, `README.md`, `LICENSE`.

## Step 4 — Start Claude Code

In that same terminal, run:

```
claude
```

If this is your first time using Claude Code, it will prompt you to log in. Follow the on-screen instructions.

## Step 5 — Paste the setup prompt

Once Claude Code is running and showing a prompt, paste this exact text and press Enter:

> Read `CLAUDE.md` and `skills/about-governing-principles.md`, then run `skills/ai-operating-system-setup-protocol.md` end-to-end with me. Ask me each placeholder value in turn; mark anything I don't have an answer for as `OPEN` rather than guessing.

Claude Code will read the files and start the interview.

## Step 6 — Answer the interview questions

The setup protocol runs in phases. You will be asked about:

- Where your library should live long-term (this can be the path you already chose).
- Whether you want multiple audience tiers (most users don't — say no).
- Where your active projects live (e.g., `~/Dropbox/`, `~/projects/`).
- Optional identity values (your name, affiliation, field).
- Whether you want to sync the library with a Git repo.

For any value you're not sure about, answer `OPEN`. Claude will record it in the substitution manifest and you can fill it in later.

The protocol will then:

1. Create a snapshot of the library (rollback insurance).
2. Substitute every `{{PLACEHOLDER}}` token with your answers.
3. Hand off to two companion skills that wire the library into the Claude Code harness (`~/.claude/`).
4. Optionally help you draft a personalized identity file.
5. Test that one skill invocation works.

## What if something fails?

- **`claude: command not found`.** Claude Code is not on your `PATH`. Reinstall via the official instructions, or close and reopen the terminal.
- **Authentication errors.** Inside Claude Code, run the `/login` command and follow the prompt.
- **The protocol stops mid-phase.** The substitution manifest at `<your-library-folder>/setup/substitution-manifest-<date>.md` records what was filled in. Restart Claude Code, point it at that manifest, and ask it to resume.
- **The library got corrupted during substitution.** The Phase 0 snapshot is your rollback. Replace the corrupted folder with the snapshot copy.
- **Anything else.** Open an issue at https://github.com/simonepaciphd/ai-os-public/issues with the exact error message and the phase you were in.
