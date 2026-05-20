"""Rich-based CLI runner.

Lets you run the simulation in a terminal, no Qt required. This is how you
should exercise the sim while developing — it's much faster to iterate on
the deterministic core when the UI isn't in the way.

Run with:  python -m cli.runner
"""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from controller import GameController
from core.content.names import COUNTRIES, NAMES, TALENTS

console = Console()


def _print_stats(snap: dict) -> None:
    if snap.get("mode") == "CREATION":
        return
    ch = snap["character"]
    st = snap["stats"]
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Name", f"{ch['name']}  ({ch['gender']}, {ch['country']})")
    table.add_row("Age", str(ch["age"]))
    table.add_row("Money", f"£{snap['money']:,}")
    table.add_row("Happiness", f"{st['happiness']}")
    table.add_row("Health", f"{st['health']}")
    table.add_row("Smarts", f"{st['smarts']}")
    table.add_row("Looks", f"{st['looks']}")
    if snap.get("career"):
        table.add_row("Job", snap["career"]["title"])
    table.add_row("Education", snap["education"]["level"])
    console.print(Panel(table, title="[bold]Status[/bold]", border_style="cyan"))


def _print_recent_feed(snap: dict, n: int = 6) -> None:
    feed = snap.get("feed", [])[-n:]
    for entry in feed:
        colour = {
            "good": "green", "bad": "red", "special": "cyan", "neutral": "white",
        }.get(entry["kind"], "white")
        console.print(f"[{colour}]Age {entry['age']}:[/{colour}] {entry['text']}")


def _resolve_pending(controller: GameController, snap: dict) -> dict:
    ev = snap.get("pending_event")
    if not ev:
        return snap
    console.print()
    console.print(Panel(ev["text"], title="[yellow]Decision[/yellow]", border_style="yellow"))
    for i, choice in enumerate(ev["choices"]):
        console.print(f"  [{i + 1}] {choice['text']}")
    pick = IntPrompt.ask("Choose", choices=[str(i + 1) for i in range(len(ev["choices"]))])
    return controller.choose(pick - 1)


def _create_character(controller: GameController) -> dict:
    console.print(Panel.fit("[bold]Start a new life[/bold]", border_style="cyan"))
    gender = Prompt.ask("Gender", choices=list(NAMES.keys()), default="Male")
    default_name = NAMES[gender][0]
    name = Prompt.ask("Name", default=default_name)
    country = Prompt.ask("Country", choices=COUNTRIES, default=COUNTRIES[0])
    talent = Prompt.ask("Talent", choices=TALENTS, default=TALENTS[0])
    return controller.new_game(name=name, gender=gender, country=country, talent=talent)


def main() -> None:
    controller = GameController()
    snap = _create_character(controller)

    while snap.get("mode") == "PLAYING":
        console.clear()
        _print_stats(snap)
        _print_recent_feed(snap)
        if snap.get("pending_event"):
            snap = _resolve_pending(controller, snap)
            continue
        console.print()
        console.print("[bold]Actions:[/bold] [a]ge up  [j]obs  [s]tudy  [g]ym  [d]octor  [f]amily  [q]uit")
        action = Prompt.ask("Action", default="a").lower()
        if action in ("a", ""):
            snap = controller.age_up()
        elif action == "j":
            jobs = snap["jobs"]
            for i, j in enumerate(jobs):
                console.print(f"  [{i + 1}] {j['title']:<30} £{j['salary']:>8,}  (age {j['min_age']}, smarts {j['min_smarts']})")
            pick = IntPrompt.ask("Pick", choices=[str(i + 1) for i in range(len(jobs))])
            snap = controller.apply_for_job(jobs[pick - 1]["job_id"])
        elif action == "s":
            snap = controller.activity("study")
        elif action == "g":
            snap = controller.activity("gym")
        elif action == "d":
            snap = controller.activity("doctor")
        elif action == "f":
            snap = controller.activity("spend_time")
        elif action == "q":
            return

    if snap.get("mode") == "DEATH":
        console.clear()
        _print_stats(snap)
        _print_recent_feed(snap, n=15)
        console.print(Panel.fit("[bold red]You have died.[/bold red]", border_style="red"))


if __name__ == "__main__":
    main()
