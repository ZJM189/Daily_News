import typer

app = typer.Typer(help="Daily News backend management commands.")


@app.command("create-admin")
def create_admin() -> None:
    """Create the first administrator account.

    The database-backed implementation will be added with the identity context.
    """
    typer.echo("create-admin command scaffolded; implementation pending database models.")


if __name__ == "__main__":
    app()
