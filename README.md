# ProtoPilot gRPC Exploit Chain CTF

ProtoPilot helps teams automate workflows through fast, internal gRPC-powered rule testing. What could go wrong?

## Challenge Story

ProtoPilot is an internal workflow automation platform. Users authenticate through a web dashboard to review workflow health and operational notes. Under the hood, admin teams are migrating rule testing to a gRPC service.

This challenge simulates a realistic exploit chain across auth, service discovery, authorization design, and unsafe Python rule evaluation.

## Services and Ports

- web: <http://localhost:8081>
- grpc-api: localhost:50051

## Project Layout

- docker-compose.yml
- web/: Flask application, templates, static files, leaked proto
- grpc-api/: gRPC server and proto source
- flags/: challenge data mounted into containers

## Setup

1. Ensure Docker Desktop (or Docker Engine with Compose) is installed.
1. From the project root, run:

```bash
docker compose up --build -d
```

1. Open <http://localhost:8081>.

## Participant Rules

- This is a local, intentionally vulnerable CTF target.
- Attack only this local challenge instance.
- Do not attempt host escape, persistence, or destructive activity.
- Keep all exploitation inside the containers.

## Hints

1. Team contact details are visible in-app and can help with login testing.
2. A client-side artifact references the internal rule validation migration.
3. Metadata values can influence server-side authorization decisions.

## Canonical Flag Location

- /root/root.txt

## Safety and Compliance Notes

- Environment is self-contained via Docker Compose.
- No internet access is required during solving.
- No destructive or host-targeting payloads are included in source.
- Exploit utility is intentionally constrained to in-container behavior.
