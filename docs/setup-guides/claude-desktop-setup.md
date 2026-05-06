# Claude desktop setup guide

This guide walks you through installing the AI Operating System public mirror inside the Claude desktop app's **Code** tab. The Code tab runs the same Claude Code engine as the terminal CLI, so the setup protocol works the same way it does in [Claude Code setup guide](claude-code-setup.md) — what differs is how you launch the session and point it at the library folder.

Approximate time: 30–45 minutes, most of it spent answering interview questions.

> **Guide version: 2026-05-06.** Written against the Claude desktop app and the `code.claude.com` docs on that date. Anthropic ships UI changes frequently. If the screens or button labels you see don't match this guide, see [If this guide looks out of date](#if-this-guide-looks-out-of-date) at the bottom for a one-paragraph fix.

## Prerequisites

1. **A paid Claude subscription.** The Code tab requires a Pro, Max, Team, or Enterprise plan. The desktop app itself is free across all tiers, but clicking the Code tab on a free plan triggers an upgrade prompt.

2. **Supported OS.** macOS or Windows (x64 or ARM64). The desktop app is **not available on Linux** — Linux users should follow [Claude Code setup guide](claude-code-setup.md) instead.

3. **Git on Windows.** On Windows, local sessions in the Code tab require Git. Download from https://git-scm.com/downloads/win. macOS includes Git by default.

4. **About 200 MB of free disk space** for the library and setup artifacts.

## The three tabs in the Claude desktop app

The desktop app has three top-level tabs. Only one is the right place to set up the AI Operating System:

- **Chat** — General conversation, similar to claude.ai. **No file access.** Cannot run the setup protocol.
- **Cowork** — Autonomous background agent that runs on a cloud VM with its own environment. The AI OS lives on your local machine, so this is the wrong surface.
- **Code** — Interactive coding assistant with direct access to your local files. **This is the right tab.** It runs the same Claude Code engine as the terminal CLI and shares its configuration: CLAUDE.md files, MCP servers, hooks, skills, and settings.

Everything below assumes the Code tab.

## Step 1 — Download and install the Claude desktop app

Download the installer from https://claude.com/download:

- **macOS:** universal `.dmg` (Intel and Apple Silicon).
- **Windows x64:** `.setup` installer.
- **Windows ARM64:** dedicated ARM64 installer.

Run the installer, then launch Claude from your Applications folder (macOS) or Start menu (Windows), and sign in with your Anthropic account.

## Step 2 — Choose where to put the library files

Same as the CLI guide. The library will live in this folder long-term — the setup protocol records the path in its manifest, and the Code tab will point at it from any session.

**Recommended locations:**

- **Windows.** `C:\Users\<your-name>\Documents\AI-OS\` or `C:\Users\<your-name>\AI-OS\`.
- **macOS.** `~/AI-OS/` (i.e., `/Users/<your-name>/AI-OS/`) or `~/Documents/AI-OS/`.

**Where NOT to put it:**

- Inside `~/.claude/` (the Claude Code engine's config folder). The setup protocol creates a connection between the library and the engine — they need to be separate folders.
- Inside a temporary or downloads folder you periodically clean out.
- Inside a folder you don't have write access to.

**To get the files:**

### Option A — Download as ZIP (no terminal required)

1. Open https://github.com/simonepaciphd/ai-os-public in your web browser.
2. Click the green **Code** button near the top right of the page.
3. In the dropdown, click **Download ZIP**.
4. Unzip the file. The unzipped folder will be named `ai-os-public-main` by default. Move and rename it to your chosen location — for example, on Windows the final path might be `C:\Users\<your-name>\AI-OS\public\` (after renaming `ai-os-public-main` to `public`).

### Option B — Clone with git

If you have Git installed (you do on Windows by way of Prerequisite 3), open a file manager, navigate to your chosen parent folder, then in a terminal run:

```
git clone https://github.com/simonepaciphd/ai-os-public.git public
```

This creates the library at e.g. `~/AI-OS/public/` (or `C:\Users\<your-name>\AI-OS\public\` on Windows).

## Step 3 — Open the Code tab and select your folder

1. Launch the Claude desktop app if it isn't already running.
2. **Click the Code tab** at the top center of the window.
   - If you see an "upgrade" prompt, your account is on a free plan — see Prerequisites.
   - If you see a 403 or authentication error, sign out and back in, then restart the app.
3. Select **Local** as the environment. (Remote and SSH would run setup on a different machine; you want it on your local files.)
4. Click **Select folder** and choose the library folder from Step 2 (e.g., `~/AI-OS/public/`).
5. Choose a model from the dropdown next to the send button. Opus or Sonnet is recommended for the setup interview; you can change later.

You should now see the library files listed in a side pane and an empty prompt box.

## Step 4 — Paste the setup prompt

In the prompt box, paste this exact text and press Enter:

> Read `CLAUDE.md` and `skills/about-governing-principles.md`, then run `skills/ai-operating-system-setup-protocol.md` end-to-end with me. Ask me each placeholder value in turn; mark anything I don't have an answer for as `OPEN` rather than guessing.

Claude will read the files and start the interview. By default the Code tab runs in **Ask permissions** mode — it proposes every file change and waits for your **Accept** before applying. Leave this default on for setup; you'll want to see each change.

## Step 5 — Answer the interview questions

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
3. Hand off to two companion skills that wire the library into the Claude Code engine (`~/.claude/`).
4. Optionally help you draft a personalized identity file.
5. Test that one skill invocation works.

Because the Code tab shares its configuration with the terminal CLI, any wiring done in this session is also live the next time you run `claude` from a terminal — and vice versa.

## What if something fails?

- **Clicking Code prompts you to upgrade.** Your account is on a free plan. Subscribe to Pro, Max, Team, or Enterprise, restart the app, and retry.
- **Clicking Code returns a 403 or authentication error.** Sign out and sign in again, then restart the app.
- **The Chat tab can't see your files.** By design — Chat has no file access. Switch to the Code tab.
- **Local sessions don't start on Windows.** Git for Windows is missing or not on the PATH. Install it from https://git-scm.com/downloads/win and restart the app.
- **The protocol stops mid-phase.** The substitution manifest at `<your-library-folder>/setup/substitution-manifest-<date>.md` records what was filled in. Restart the session in the Code tab, point at the same folder, and ask Claude to resume from the manifest.
- **The library got corrupted during substitution.** The Phase 0 snapshot is your rollback. Replace the corrupted folder with the snapshot copy.
- **Anything else.** Open an issue at https://github.com/simonepaciphd/ai-os-public/issues with the exact error message and the phase you were in.

## If this guide looks out of date

This guide was written against the Claude desktop app's UI as of **2026-05-06**. The desktop UI ships changes frequently, so the screens, button labels, or tab arrangement you see may have evolved.

If something obvious doesn't match — a tab is missing, a button is renamed, the install steps look different — paste the contents of this guide into a Claude session (the Chat tab on desktop, or any Claude.ai conversation) and ask:

> Please rewrite this setup guide so it matches the current Claude desktop UI.

Claude will produce an updated version against whatever it currently sees. The setup protocol the guide invokes — `skills/ai-operating-system-setup-protocol.md` in this repo — is the load-bearing artifact and changes more slowly than the surrounding UI.
