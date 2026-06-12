FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY templates ./templates
COPY static ./static

# Editable install keeps /app/app authoritative so templates/ and static/
# resolve relative to the project root.
RUN pip install --no-cache-dir -e .

# Pretrained ONNX models for transfer learning and detection; the app
# degrades to pixel features / face detection if this step is skipped.
RUN python scripts/download_pretrained.py || echo "pretrained models skipped"

ENV LDS_EDITION=all
EXPOSE 8000
VOLUME ["/app/workspace"]

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
