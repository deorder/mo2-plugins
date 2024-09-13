import click
import shutil
import os
import os.path as path
import subprocess


@click.command()
@click.option(
    "--target",
    type=click.Choice(["merge-plugins-hide", "sync-mod-order", "link-deploy", "all"]),
    help="The target plugin to build",
    default="merge-plugins-hide",
    prompt="Select the plugin to build",
)
@click.option(
    "--zip",
    is_flag=True,
    help="Zip the built plugin",
)
def cli(target: str, zip: bool):
    paths = {
        "src": path.join(path.dirname(__file__), "src"),
        "out": path.join(path.dirname(__file__), "target", target),
        "build": path.join(path.dirname(__file__), "build"),
    }
    plugin = target.replace("-", "_")
    # Separate all to use the old code for now while i work out the per-plugin code
    if target == "all":
        return build_all(zip)

    click.echo("Copying source files to the build folder...")
    if path.exists(paths["out"]):
        shutil.rmtree(paths["out"])
    os.makedirs(paths["out"])

    for file in ["common.py", f"{plugin}.py"]:
        shutil.copy2(path.join(paths["src"], file), paths["out"])

    with open(path.join(paths["src"], "plugin.__init__.py"), "r") as file:
        with open(path.join(paths["out"], "__init__.py"), "w") as out_file:
            out_file.write(file.read().replace("PLUGIN", plugin))
    shutil.copy2("LICENSE", paths["out"])
    click.echo("Source files copied successfully")

    # Run scour on all svg files
    click.echo("Setting up resources...")
    if path.exists(paths["build"]):
        shutil.rmtree(paths["build"])
    os.makedirs(paths["build"])

    # Remove unused files from resources.qrc and write it to the build folder
    with open(path.join(paths["src"], "resources.qrc"), "r") as in_file:
        with open(path.join(paths["build"], "resources.qrc"), "w") as out_file:
            out_file.writelines(
                [line for line in in_file if "<file>" not in line or plugin in line]
            )

    svg_files = [
        path.join(dirpath, filename)
        for dirpath, _, filenames in os.walk(paths["src"])
        for filename in filenames
        if filename.endswith(".svg")
    ]
    for file in svg_files:
        scour_file(file, path.join(paths["build"], path.basename(file)))

    click.echo("Resources ready for packaging")

    # Run rcc and write the output to resources.py
    click.echo("Running rcc...")
    rcc_data = compile_rcc(path.join(paths["build"], "resources.qrc"))
    with open(path.join(paths["out"], "resources.py"), "w") as file:
        file.write(rcc_data)

    shutil.rmtree(paths["build"])
    click.echo("rcc executed successfully")

    if zip:
        click.echo("Zipping the plugin...")
        shutil.make_archive(
            paths["out"], "zip", path.dirname(paths["out"]), path.basename(paths["out"])
        )
        click.echo("Plugin zipped successfully")

    click.echo("Script completed successfully")


def build_all(zip: bool):
    target = "deorder-plugins"
    paths = {
        "src": path.join(path.dirname(__file__), "src"),
        "out": path.join(path.dirname(__file__), "target", target),
        "build": path.join(path.dirname(__file__), "build"),
    }
    # Set up output folder
    click.echo("Copying source files to the build folder...")
    if path.exists(paths["out"]):
        shutil.rmtree(paths["out"])
    os.makedirs(paths["out"])

    # Copy all .py files and LICENSE to the build folder
    excluded_files = ["resources.py", "plugin.__init__.py"]
    for file in os.listdir(paths["src"]):
        if file.endswith(".py") and file not in excluded_files:
            shutil.copy2(path.join(paths["src"], file), paths["out"])
    shutil.copy2("LICENSE", paths["out"])
    click.echo("Source files copied successfully")

    # Run scour on all svg files
    click.echo("Setting up resources...")
    if path.exists(paths["build"]):
        shutil.rmtree(paths["build"])
    os.makedirs(paths["build"])

    shutil.copy2(path.join(paths["src"], "resources.qrc"), paths["build"])
    svg_files = [
        path.join(dirpath, filename)
        for dirpath, _, filenames in os.walk(paths["src"])
        for filename in filenames
        if filename.endswith(".svg")
    ]
    for file in svg_files:
        scour_file(file, path.join(paths["build"], path.basename(file)))

    click.echo("Resources ready for packaging")

    # Run rcc.exe with the specified parameters
    click.echo("Running rcc...")
    rcc_data = compile_rcc(path.join(paths["build"], "resources.qrc"))
    with open(path.join(paths["out"], "resources.py"), "w") as file:
        file.write(rcc_data)

    shutil.rmtree(paths["build"])
    click.echo("rcc executed successfully")

    if zip:
        click.echo("Zipping the plugin...")
        shutil.make_archive(
            paths["out"], "zip", path.dirname(paths["out"]), path.basename(paths["out"])
        )
        click.echo("Plugin zipped successfully")

    click.echo("Script completed successfully")


def scour_file(input: str, output: str):
    return subprocess.run(
        f"scour -i {input} -o {output} --quiet --enable-id-stripping --remove-descriptive-elements --enable-comment-stripping --indent=none --no-line-breaks".split(),
        check=True,
    )


def compile_rcc(resources_qrc: str):
    try:
        rcc = subprocess.run(
            f"pyside6-rcc -g python -compress 2 -threshold 30 {resources_qrc}".split(),
            check=True,
            capture_output=True,
            text=True,
        )
        rcc_output = rcc.stdout
        return rcc_output.replace("from PySide6", "from PyQt6")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error occurred while running rcc: {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    cli()
