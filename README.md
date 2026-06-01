# Pathfinder CLI (Balanced Minimal Textual UX)

> Migration status: completed to `pathfinder-cli`.  
> Primary installed launch: `pathfinder --login`.  
> Simplest dev launch: `dev` in `cmd`, `.\dev` in PowerShell.

This project provides a **minimal Textual terminal interface** with a fallback simple mode:

- Top banner showing the current module
- Command-driven module switching with `/module`
- Main content area for dashboard + conversation transcript
- Bottom command area (fixed) separated by one horizontal line
- Orange-first theme with spinner + orange loading bar

## Dev Run

No activation is required for the normal local workflow. The launcher scripts create `.venv`, install dependencies when needed, and start the CLI.

Command Prompt (`cmd`):

```bash
pathfinder --login
dev
```

PowerShell:

```bash
.\pathfinder --login
.\dev
```

Pass any launcher flag through the script:

```bash
pathfinder --start
dev --simple
.\dev --simple
dev --start
```

## Manual Install

If you want the console scripts installed into a virtual environment:

```bash
python -m venv .venv
```

PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

Command Prompt (`cmd`):

```bash
.venv\Scripts\activate.bat
```

Then install:

```bash
python -m pip install -e .
```

## Installed Run

After editable install, both console script names are available:

```bash
pathfinder --login
pathfinder-cli --login
```

Direct dashboard start without the login flow:

```bash
pathfinder --start
pathfinder-cli --start
```

Fallback simple CLI:

```bash
pathfinder --simple
pathfinder-cli --simple
```

Module alternative:

```bash
python -m pathfinder_cli --login
python -m pathfinder_cli --start
python -m pathfinder_cli --simple
```

## Migration Summary

Applied naming targets:

- Repo folder: `pathfinder-cli`
- Python package folder: `pathfinder_cli`
- Distribution name: `pathfinder-cli`
- Script entrypoints: `pathfinder` and `pathfinder-cli`
- Primary dashboard flow: `--login`

## Controls

- `Enter`: submit command from input
- `Up` / `Down`: move through the `/module` picker
- `Ctrl+Q`: quit

Utility commands in the command bar:

- `/help`: show command reference
- `/module`: open the module picker, then use `Up` / `Down` and `Enter`
- `/module <name|number>`: switch directly to a module
- `/clear`: clear conversation history for all modules
- `/reset`: clear conversation history for current module only

## Modules

Available modules are curated from public BeyondTrust product areas (mock data only):

- Platform: Pathfinder Platform
- Privileged Access: Privileged Remote Access, Password Safe
- Endpoint & Identity: Endpoint Privilege Management, Identity Security Insights, Entitle, Active Director
- Support: Remote Support

## Styling and Colors

Active Textual styling is in `pathfinder_cli/styles.tcss`.

Key tokens:

- `$bg-deep`, `$bg-panel`, `$bg-soft`, `$bg-input`: orange-based backgrounds
- `$orange-primary`, `$orange-soft`, `$orange-pale`: highlight colors
- `$text-main`, `$text-muted`: text contrast
- `$line`: separator lines

Only two layout separators are intentionally used:

- top module divider
- `#command-bar { border-top: ... }`

No nested rounded panel borders are used in the default interface.

## Font Guidance (Terminal Setting)

The app **cannot force terminal font face/size**. Set this in your terminal profile.

Recommended (Windows Terminal):

1. Open `Settings` -> profile you use for PowerShell/cmd.
2. Go to `Appearance`.
3. Set `Font face` (example: `Cascadia Code`, `JetBrains Mono`, `Fira Code`).
4. Set `Font size` (example: `12` or `14`).

JSON example:

```json
{
  "profiles": {
    "defaults": {
      "font": {
        "face": "Cascadia Code",
        "size": 13
      }
    }
  }
}
```

## Notes

- Data is intentionally mock/curated for UX prototyping.
- Copy is inspired by public product descriptions and not an official BeyondTrust UI.

Prompts:
investigate suspicious lateral movement tied to a service account

show me where privileged activity has been spiking this week across identity, policy, connector, and response signals

break down today’s privileged access review queue by correlated risk, watch items, and stale approvals

map the full reachable privilege path for svc-backup-ops into production admin access, including the live session and approval mismatch