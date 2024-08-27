FROM python:3.12-slim AS builder

# Install curl and other necessary packages
RUN apt-get update \
    && apt-get install -y curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Verify Poetry installation
RUN poetry --version

# Set working directory inside the builder
WORKDIR /code

# Copy project files
COPY pyproject.toml poetry.lock* README.md /code/

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry config virtualenvs.in-project true \
    && poetry install --no-root --no-interaction 
# Copy the rest of the application code
COPY . /code

# Build the package wheel and install it
RUN poetry build \
    && pip install /code/build/models/dist/pygaello_models-0.1.0-py3-none-any.whl \
    && pip install /code/build/ops/dist/pygaello_ops-0.1.0-py3-none-any.whl \
    && pip install /code/dist/pygaello_inferences-0.1.0-py3-none-any.whl

# Final image
FROM python:3.12-slim AS final

# Set the working directory inside the final image
WORKDIR /code

# Copy only necessary files from the build stage
COPY --from=builder /code /code

# Expose application port
EXPOSE 54201

# Specify the command to run your app
CMD ["python", "src/main.py"]
