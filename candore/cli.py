import asyncio
from pprint import pprint

import click

from candore import Candore
from candore.config import candore_settings

# Click Interactive for Cloud Resources Cleanup


@click.group(
    help="A data integrity validation CLI tool for upgradable products",
    invoke_without_command=True,
)
@click.option("--version", is_flag=True, help="Installed version of candore")
@click.option("--settings-file", "-s", default=None, help="Settings file path")
@click.option("--components-file", "-c", default=None, help="Components file path")
@click.option("--conf-dir", default=None, help="Conf directory contain configuration files")
@click.pass_context
def candore(ctx, version, settings_file, components_file, conf_dir):
    if version:
        import pkg_resources

        ver = pkg_resources.get_distribution("candore").version
        click.echo(f"Version: {ver}")
    candore_obj = Candore(
        settings=candore_settings(
            option_settings_file=settings_file,
            option_components_file=components_file,
            conf_dir=conf_dir,
        )
    )
    ctx.__dict__["candore"] = candore_obj


@candore.command(help="List API lister endpoints from Product")
@click.pass_context
def apis(ctx):
    """List API lister endpoints from Product"""
    print("List of API lister endpoints from Product")
    candore_obj = ctx.parent.candore
    pprint(candore_obj.list_endpoints())


@candore.command(help="Extract and save data using API lister endpoints")
@click.option("--mode", type=str, help="The mode must be 'pre' or 'post'")
@click.option("-o", "--output", type=str, help="The output file name")
@click.option("--full", is_flag=True, help="Extract data from all the pages of a component")
@click.option("--max-pages", type=int, help="The maximum number of pages to extract per entity")
@click.option("--skip-percent", type=int, help="The percentage of pages to skip per entity")
@click.option("--resume", is_flag=True, help="Resume the extraction from the last completed entity")
@click.pass_context
def extract(ctx, mode, output, full, max_pages, skip_percent, resume):
    loop = asyncio.get_event_loop()
    candore_obj = ctx.parent.candore
    loop.run_until_complete(
        candore_obj.save_all_entities(
            mode=mode,
            output_file=output,
            full=full,
            max_pages=max_pages,
            skip_percent=skip_percent,
            resume=resume,
        )
    )


@candore.command(help="Compare pre and post upgrade data")
@click.option("--pre", type=str, help="The pre upgrade json file")
@click.option("--post", type=str, help="The post upgrade json file")
@click.option("-i", "--inverse", is_flag=True, help="Inverse comparison, shows whats not changed")
@click.option("-o", "--output", type=str, help="The output file name")
@click.option(
    "-t",
    "--report-type",
    type=str,
    default="json",
    help="The type of report GSheet, JSON, or webpage",
)
@click.option("--record-evs", is_flag=True, help="Record Expected Variations in reporting")
@click.pass_context
def compare(ctx, pre, post, inverse, output, report_type, record_evs):
    candore_obj = ctx.parent.candore
    candore_obj.compare_entities(
        pre_file=pre,
        post_file=post,
        inverse=inverse,
        output=output,
        report_type=report_type,
        record_evs=record_evs,
    )


@candore.command(help="JSON Reader for reading the specific path data from entities data file")
@click.option(
    "--path",
    type=str,
    help="The path to search the data from.\n"
    "Path contents could divided by some delimiter.\n"
    "e.g entity/5/description",
)
@click.option(
    "--data-file",
    type=str,
    help="The data file from which to search the data on a given path",
)
@click.option("--delimiter", type=str, default="/", help="Settings file path. Default is '/'")
@click.pass_context
def reader(ctx, path, data_file, delimiter):
    candore_obj = ctx.parent.candore
    candore_obj.find_path(path=path, json_file=data_file, delimiter=delimiter)


if __name__ == "__main__":
    candore()
