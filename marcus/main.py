from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from marcus.config.settings import DB_PATH
from marcus.core.models import Database
from marcus.core.scraper import MarcusScraper
from marcus.utils.export import export_opportunities_csv, export_opportunities_excel

console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


async def cmd_search(args):
    scraper = MarcusScraper(headless=not args.visible)
    await scraper.start()

    try:
        opportunities = await scraper.run_search(
            marketplace=args.marketplace,
            min_price=args.min_price,
            max_price=args.max_price,
            min_revenue=args.min_revenue,
            max_reviews=args.max_reviews,
            min_sales=args.min_sales,
            category=args.category,
            enrich_with_keepa=not args.no_keepa,
            min_score=args.min_score,
        )
        _display_opportunities(opportunities)
    finally:
        await scraper.close()


async def cmd_export(args):
    db = Database(DB_PATH)
    try:
        if args.format == "excel":
            path = export_opportunities_excel(db, min_score=args.min_score)
        else:
            path = export_opportunities_csv(db, min_score=args.min_score)
        console.print(f"[green]Export terminé :[/green] {path}")
    finally:
        db.close()


async def cmd_dashboard(_args):
    console.print("[bold]Lancement du dashboard Marcus...[/bold]")
    import subprocess
    dashboard_path = str(DB_PATH.parent.parent / "dashboard" / "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])


def _display_opportunities(opportunities: list):
    if not opportunities:
        console.print("[yellow]Aucune opportunité trouvée.[/yellow]")
        return

    table = Table(title="Marcus - Opportunités", show_lines=True)
    table.add_column("ASIN", style="cyan", width=12)
    table.add_column("Titre", width=35)
    table.add_column("Prix", justify="right")
    table.add_column("BSR", justify="right")
    table.add_column("Ventes/mois", justify="right")
    table.add_column("Score", justify="right", style="bold green")

    for opp in opportunities[:20]:
        p = opp.product
        table.add_row(
            p.asin,
            p.title[:35],
            f"{p.price:.2f} {p.currency}",
            str(p.bsr or "-"),
            str(p.monthly_sales or "-"),
            f"{opp.score:.1f}/100",
        )

    console.print(table)
    console.print(f"\n[bold]{len(opportunities)}[/bold] opportunités au total")


def main():
    parser = argparse.ArgumentParser(description="Marcus - Recherche de produits Marketplace")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command")

    search = sub.add_parser("search", help="Rechercher des produits")
    search.add_argument("--marketplace", default="amazon_fr", help="Marketplace cible")
    search.add_argument("--min-price", type=float, default=10)
    search.add_argument("--max-price", type=float, default=100)
    search.add_argument("--min-revenue", type=int, default=1000)
    search.add_argument("--max-reviews", type=int, default=200)
    search.add_argument("--min-sales", type=int, default=100)
    search.add_argument("--category", default="")
    search.add_argument("--min-score", type=float, default=40)
    search.add_argument("--no-keepa", action="store_true", help="Skip Keepa enrichment")
    search.add_argument("--visible", action="store_true", help="Show browser window")

    export = sub.add_parser("export", help="Exporter les résultats")
    export.add_argument("--format", choices=["csv", "excel"], default="csv")
    export.add_argument("--min-score", type=float, default=0)

    sub.add_parser("dashboard", help="Lancer le dashboard Streamlit")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "search":
        asyncio.run(cmd_search(args))
    elif args.command == "export":
        asyncio.run(cmd_export(args))
    elif args.command == "dashboard":
        asyncio.run(cmd_dashboard(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
