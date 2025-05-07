# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,relabel=shared \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,relabel=shared \
    # Installs in ./.venv
    # uv sync --frozen --no-install-project --no-dev
    # Still installs in ./.venv
    # uv sync --frozen --no-install-project --no-dev --python $(which python3)
    # Install to system environment instead of venv in a pip-compatible way.
    uv export | uv pip install --system --requirements -

# Uncomment to add extra files to the container
# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
# ADD . /app
# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
