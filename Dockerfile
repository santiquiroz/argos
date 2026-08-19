# Container image runs the CPU execution provider. The AMD-GPU/DirectML path is Windows-native
# (DirectML is not available inside Linux containers), so for GPU inference run Argos directly on
# Windows (see README) and use this image only for the CPU fallback or for the API/UI tier.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY argos ./argos
RUN pip install --no-cache-dir -e ".[cpu]"

ENV ARGOS_HOST=0.0.0.0 ARGOS_PORT=8080 ARGOS_DEVICE=cpu
EXPOSE 8080
CMD ["python", "-m", "argos"]
