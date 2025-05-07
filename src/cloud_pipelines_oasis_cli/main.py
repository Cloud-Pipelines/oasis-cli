import dataclasses
import datetime
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import types
import typing

import tomli
import typer
import yaml

from cloud_pipelines import components

from . import git


CONTAINER_INFO_FILE_NAME = "oasis.pipeline_component_root.yaml"
CONTAINER_IMAGE_NAME_KEY = "container_image_name"
COMPONENT_YAML_FILE_NAME = "component.yaml"
COMPONENT_YAML_TEMPLATE_FILE_NAME = "template.component.yaml"


app = typer.Typer(no_args_is_help=True)

containers_app = typer.Typer()
app.add_typer(containers_app, name="containers", no_args_is_help=True)

containers_new_app = typer.Typer()
containers_app.add_typer(containers_new_app, name="new", no_args_is_help=True)

components_app = typer.Typer()
app.add_typer(components_app, name="components", no_args_is_help=True)

components_new_app = typer.Typer()
components_app.add_typer(components_new_app, name="new", no_args_is_help=True)

components_regenerate_app = typer.Typer()
components_app.add_typer(
    components_regenerate_app, name="regenerate", no_args_is_help=True
)


@containers_new_app.command(name="python-uv-container-root")
def containers_new_python_uv_container_root(
    container_image_name: typing.Annotated[str, typer.Option()],
    # python_version: str | None = None,
    directory: str | None = None,
    force: bool = False,
) -> None:
    """Creates a new root for components that use Python-based containers."""
    # Create pyproject.toml, uv.lock, .python-version, .dockerignore (for .venv)
    # Create uv-based Dockerfile
    # ? Create build script
    template_name = "containers/python-uv-container-root"
    _apply_template(template_name=template_name, directory=directory, force=force)
    _write_container_image_name(
        container_image_name=container_image_name, directory=directory
    )


@containers_new_app.command(name="generic-container-root")
def containers_new_generic_container_root(
    container_image_name: typing.Annotated[str, typer.Option()],
    directory: str | None = None,
    force: bool = False,
) -> None:
    """Creates a new root for components that use custom containers."""
    # Create generic Dockerfile and .dockerignore
    template_name = "containers/generic-container-root"
    _apply_template(template_name=template_name, directory=directory, force=force)
    _write_container_image_name(
        container_image_name=container_image_name, directory=directory
    )


@containers_app.command(name="build")
def containers_build(
    repository: str | None = None,
    tag: str | None = None,
    directory: str | None = None,
) -> None:
    """Builds the container, pushes it into repository and updates the container_info.yaml file."""
    # get tag
    # docker/podman build -f Dockerfile
    # docker/podman push --digest-file
    # update the container_info.yaml file
    import podman

    directory = directory or os.path.curdir
    context_path = directory
    dockerfile_path = "Dockerfile"
    if not repository:
        image_name = _read_container_image_name(directory=directory)
        if not image_name:
            raise ValueError(
                f"Must specify the `repository` parameter or have {CONTAINER_IMAGE_NAME_KEY} specified in {CONTAINER_INFO_FILE_NAME} file"
            )
        if "@" in image_name:
            image_name = image_name[: image_name.index("@")]
        repository, _, new_tag = image_name.partition(":")
        tag = tag or new_tag
    image_name = f"{repository}:{tag}" if tag else repository
    # # podman machine inspect --format '{{ .ConnectionInfo.PodmanSocket.Path }}'
    # base_url = "http+unix:///var/folders/_9/.../T/podman/podman-machine-default-api.sock"
    # with podman.PodmanClient(base_url=base_url) as client:
    #     image, logs = client.images.build(
    #         path=context_path,
    #         dockerfile=dockerfile_path,
    #         tag=image_name,
    #     )
    #     for log_chunk in logs:
    #         print(log_chunk, end="")
    #     result = client.images.push(repository=repository, tag=tag)
    #     # TODO: Get SHA256 digest
    #     print(f"Debug: {image=}, {result=}")
    #     digest = image.id

    # Run and stream logs: podman build -f $dockerfile_path -t $image_name $context_path
    subprocess.check_call(
        [
            "podman",
            "build",
            "-f",
            dockerfile_path,
            "-t",
            image_name,
            "--platform",
            "linux/amd64",
            context_path,
        ],
    )
    with tempfile.NamedTemporaryFile() as digest_file:
        subprocess.check_call(
            ["podman", "push", "--digestfile", digest_file.name, image_name]
        )
        digest = digest_file.read().decode("utf-8")
    pushed_image_name = f"{repository}@{digest}"
    _write_container_image_name(
        container_image_name=pushed_image_name, directory=directory
    )


@components_new_app.command(name="python-function-component")
def components_new_python_function_component(
    directory: str | None = None,
    force: bool = False,
) -> None:
    """Create a new function-based Lightweight Python Component.

    Args:
        name: Name of the component
    """
    template_name = "components/python-function-component"
    _apply_template(template_name=template_name, directory=directory, force=force)


@components_new_app.command(name="shell-script-component")
def components_new_shell_script_component(
    # name: str = "do_something",
    directory: str | None = None,
    force: bool = False,
) -> None:
    """Create a new shell script component."""
    template_name = "components/shell-script-component"
    _apply_template(template_name=template_name, directory=directory, force=force)


def _load_python_module(module_path: str) -> types.ModuleType | None:
    import importlib.util

    module_name = pathlib.Path(module_path).stem
    spec = importlib.util.spec_from_file_location(module_name, location=module_path)
    if not spec or not spec.loader:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_dependencies_from_pyproject_toml(pyproject_toml_path: str) -> list[str] | None:
    """Read dependencies from pyproject.toml"""
    with open(pyproject_toml_path, "rb") as file:
        pyproject = tomli.load(file)
        project_section = pyproject.get("project")
        if not project_section:
            return None
        dependencies = project_section.get("dependencies")
        return dependencies


@components_regenerate_app.command(name="python-function-component")
def components_regenerate_python_function_component(
    *,
    container_image: str | None = None,  # python:3.12
    # YAML file that has `container_image_name: ...`
    container_image_from: str | None = None,
    module_path: str = "component.py",
    function_name: str | None = None,
    # packages_to_install: list[str] | None = None,  # pandas==6.4.0
    # package_manager: str | None = None,  # uv
    dependencies_from: str | None = None,
    directory: str | None = None,
    output_component_yaml_path: str = "component.yaml",
) -> None:
    """Generate component.yaml from a Python function."""
    directory = directory or os.path.curdir
    if container_image_from:
        container_image_from = os.path.join(directory, container_image_from)
    if module_path:
        module_path = os.path.join(directory, module_path)
    if output_component_yaml_path:
        output_component_yaml_path = os.path.join(
            directory, output_component_yaml_path
        )
    if dependencies_from:
        dependencies_from = os.path.join(directory, dependencies_from)

    if container_image_from:
        if container_image:
            raise ValueError(
                "--container-image and --container-image-from cannot be specified at the same time."
            )
        with open(container_image_from, "r") as file:
            container_info: dict = yaml.safe_load(file)
        container_image = container_info.get(CONTAINER_IMAGE_NAME_KEY)

    if not container_image:
        container_image = f"python:{sys.version_info.major}.{sys.version_info.minor}"

    module_code = pathlib.Path(module_path).read_text()
    module = _load_python_module(module_path)
    if not module:
        raise ValueError(f"Unable to find or load module {module_path}.")
    if function_name:
        function = getattr(module, function_name)
    else:
        functions = []
        for name in dir(module):
            if not name.startswith("_"):
                obj = getattr(module, name)
                if callable(obj) and not isinstance(obj, type):
                    functions.append(obj)
        if not functions:
            raise ValueError(
                f"Could not find any functions in module {module}. Please specify --function-name <name>."
            )

        if len(functions) > 1:
            raise ValueError(
                f"Found multiple functions in module {module}. Please specify --function-name <name>. Functions: {functions}"
            )
        function = functions[0]

    dependencies = None
    # TODO: Support locked dependencies via `uv export --no-hashes --no-annotate --no-header
    if not dependencies_from:
        maybe_dependencies_from = os.path.join(directory, "pyproject.toml")
        if os.path.exists(maybe_dependencies_from):
            dependencies_from = maybe_dependencies_from
    if dependencies_from:
        dependencies = _get_dependencies_from_pyproject_toml(dependencies_from)

    annotations = {
        # "generated_at": _get_current_time_string(),
        "cloud_pipelines.net": "true",
        "components new regenerate python-function-component": "true",
        "python_original_code": module_code,
    }

    if dependencies:
        annotations["python_dependencies"] = json.dumps(dependencies)

    try:
        git_info = git.get_git_info(path=directory)
        if git_info:
            git_info_dict = dataclasses.asdict(git_info)
            annotations |= git_info_dict
    except:
        # TODO: Log
        pass

    op = components.create_component_from_func(
        func=function,
        base_image=container_image,
        packages_to_install=dependencies,
        annotations=annotations,
        output_component_file=output_component_yaml_path,
    )
    # return op.component_spec


def _apply_template(
    template_name: str,
    directory: str | None = None,
    force: bool = False,
):
    directory_path = pathlib.Path(directory) if directory else pathlib.Path.cwd()
    templates_dir = pathlib.Path(__file__).parent / "templates"
    template_dir = templates_dir / template_name
    import shutil

    child_paths = list(template_dir.iterdir())
    conflicting_files = [
        path.name for path in child_paths if (directory_path / path.name).exists()
    ]
    if conflicting_files and not force:
        raise ValueError(
            f"Files {conflicting_files} already exist in target directory {directory_path}. Specify the `--force` parameter to force overwrite."
        )

    for src_path in child_paths:
        dst_path = directory_path / src_path.name
        shutil.copyfile(src=src_path, dst=dst_path)


def _read_container_image_name(directory: str | None = None) -> str | None:
    directory = directory or os.path.curdir
    container_info_path = os.path.join(directory, CONTAINER_INFO_FILE_NAME)
    container_info_dict = {}
    if not os.path.exists(container_info_path):
        return None
    with open(container_info_path, "r") as file:
        container_info_dict = yaml.safe_load(file)
    return container_info_dict.get(CONTAINER_IMAGE_NAME_KEY)


def _write_container_image_name(
    container_image_name: str, directory: str | None = None
):
    directory = directory or os.path.curdir
    container_info_path = os.path.join(directory, CONTAINER_INFO_FILE_NAME)
    container_info_dict = {}
    if os.path.exists(container_info_path):
        with open(container_info_path, "r") as file:
            container_info_dict = yaml.safe_load(file)
    container_info_dict[CONTAINER_IMAGE_NAME_KEY] = container_image_name
    with open(container_info_path, "w") as writer:
        yaml.safe_dump(data=container_info_dict, stream=writer)


def _get_current_time_string() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(sep=" ")
        .replace("+00:00", "Z")
    )


if __name__ == "__main__":
    app()
