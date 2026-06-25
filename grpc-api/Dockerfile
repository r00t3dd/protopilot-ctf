FROM python:3.12-slim

WORKDIR /app

COPY grpc-api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY grpc-api /app

RUN python -m grpc_tools.protoc \
    -I /app \
    --python_out=/app/generated \
    --grpc_python_out=/app/generated \
    /app/protopilot.proto

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/generated

EXPOSE 50051

CMD ["python", "server.py"]
