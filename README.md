# Pathfinder CLI

**A small terminal playground for an imagined security dashboard.**

I made Pathfinder CLI to play with the feel of a command-driven interface: an orange-on-dark dashboard, a few browsable modules, and a little login animation. It is a personal UI prototype with mock data, not a security product or a connected AI service.

## Take a look

| Preview | Video |
| --- | --- |
| Terminal walkthrough | [▶ Watch preview 1](https://cdn.sanity.io/files/dtulk3bl/production/8c27646eca577c1f5ee1c4e895b5b76a482051c4.mp4) |
| More of the interface | [▶ Watch preview 2](https://cdn.sanity.io/files/dtulk3bl/production/eefcc6b19f8a0858a964f5f0f09b967cbb2d6891.mp4) |

## What you can try

- Explore a Textual dashboard with an orange theme and sample security data.
- Switch between modules from the command bar with `/module`.
- Try a simulated login flow, or jump straight into the dashboard.
- Use a simpler text-only mode if the full interface does not work in your terminal.

## Run it locally

Requires **Python 3.11+**.

```bash
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
pathfinder --start
```

Try `pathfinder --login` for the animated demo login, or `pathfinder --simple` for the fallback interface. The login is only a visual simulation; it does not verify credentials. In the dashboard, type `/help` for commands and press `Ctrl+Q` to quit.

Built with [Textual](https://textual.textualize.io/) and [Rich](https://rich.readthedocs.io/).

<sub>Personal, unofficial prototype inspired by public product concepts. All dashboard data is mock data.</sub>
