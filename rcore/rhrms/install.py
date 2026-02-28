import click

from rcore.rhrms.setup import after_install as setup


def after_install():
    try:
        print("Setting up Rokct HRMS...")
        setup()

        click.secho("Thank you for setting up Rokct HRMS!", fg="green")

    except Exception as e:
        BUG_REPORT_URL = "https://github.com/frappe/hrms/issues/new"
        click.secho(
            "Installation for Rokct HRMS app failed due to an error."
            " Please try re-installing the app or"
            f" report the issue on {BUG_REPORT_URL} if not resolved.",
            fg="bright_red",
        )
        raise e
