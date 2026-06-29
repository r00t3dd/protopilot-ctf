SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help build up start down stop restart logs logs-web logs-grpc ps status \
	verify-web verify-grpc verify-proto verify-sqli verify-solve verify-flags \
	reset clean clean-all prune shell-web shell-grpc

help:
	@echo "ProtoPilot lifecycle targets"
	@echo ""
	@echo "Core"
	@echo "  make build        Build all services"
	@echo "  make up           Start services in detached mode"
	@echo "  make start        Alias for up"
	@echo "  make down         Stop and remove containers"
	@echo "  make stop         Alias for down"
	@echo "  make restart      Restart stack"
	@echo "  make logs         Follow logs for all services"
	@echo "  make ps           Show compose service status"
	@echo "  make status       Compose status + endpoint checks"
	@echo ""
	@echo "Diagnostics"
	@echo "  make logs-web     Follow web logs"
	@echo "  make logs-grpc    Follow grpc-api logs"
	@echo "  make shell-web    Open shell in web container"
	@echo "  make shell-grpc   Open shell in grpc-api container"
	@echo ""
	@echo "Verification (operator use)"
	@echo "  make verify-web   Check web route returns HTTP 200"
	@echo "  make verify-grpc  Check grpc-api port is reachable"
	@echo "  make verify-proto Check leaked proto is downloadable"
	@echo "  make verify-sqli  Smoke-test SQLi login bypass path"
	@echo "  make verify-solve Run private automated solver"
	@echo "  make verify-flags Verify mounted flag files are readable in containers"
	@echo ""
	@echo "Cleanup"
	@echo "  make clean        Down stack and remove orphans (keeps volumes)"
	@echo "  make reset        DESTRUCTIVE: run deploy/reset.sh (confirmation required)"
	@echo "  make clean-all    DESTRUCTIVE: down -v --rmi local (confirmation required)"
	@echo "  make prune        DESTRUCTIVE: docker system prune -f"

build:
	docker compose build

up:
	docker compose up --build -d

start: up

down:
	docker compose down --remove-orphans

stop: down

restart: down up

logs:
	docker compose logs -f

logs-web:
	docker compose logs -f web

logs-grpc:
	docker compose logs -f grpc-api

ps:
	docker compose ps

status: ps verify-web verify-grpc

verify-web:
	@code=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/team || true); \
	if [[ "$$code" == "200" ]]; then \
		echo "[+] Web reachable on :8081 (/team)"; \
	else \
		echo "[-] Web check failed, HTTP $$code"; \
		exit 1; \
	fi

verify-grpc:
	@python3 -c "import socket,sys; s=socket.socket(); s.settimeout(2); \
	try: s.connect(('127.0.0.1',50051)); print('[+] grpc-api reachable on :50051'); \
	except Exception as err: print(f'[-] grpc-api check failed: {err}'); sys.exit(1); \
	finally: s.close()"

verify-proto:
	@tmp_file=$$(mktemp); \
	if curl -fsS http://localhost:8081/static/protos/protopilot.proto -o "$$tmp_file" && grep -q 'syntax = "proto3";' "$$tmp_file"; then \
		echo "[+] Proto file is exposed and readable"; \
		rm -f "$$tmp_file"; \
	else \
		echo "[-] Proto check failed"; \
		rm -f "$$tmp_file"; \
		exit 1; \
	fi

verify-sqli:
	@tmp_cookie=$$(mktemp); \
	resp=$$(curl -s -i -c "$$tmp_cookie" -b "$$tmp_cookie" -X POST \
		--data-urlencode "email=admin@protopilot.local" \
		--data-urlencode "password=' OR '1'='1' --" \
		http://localhost:8081/login || true); \
	rm -f "$$tmp_cookie"; \
	if echo "$$resp" | grep -qi "Location: /dashboard"; then \
		echo "[+] SQLi login bypass path appears reachable"; \
	else \
		echo "[-] SQLi smoke check failed"; \
		exit 1; \
	fi

verify-solve:
	python3 private_solutions/solve_dast.py --base-url http://localhost:8081 --grpc-host localhost --grpc-port 50051

verify-flags:
	@docker exec protopilot-web sh -lc 'test -r /home/app/user.txt' && echo "[+] user flag mounted in web container"
	@docker exec protopilot-grpc-api sh -lc 'test -r /root/root.txt' && echo "[+] root flag mounted in grpc container"

reset:
	@echo "WARNING: reset destroys containers and volumes for this project."
	@read -r -p "Continue with reset? [y/N] " confirm; \
	if [[ "$$confirm" == "y" || "$$confirm" == "Y" ]]; then \
		bash deploy/reset.sh; \
	else \
		echo "Cancelled."; \
	fi

clean:
	docker compose down --remove-orphans

clean-all:
	@echo "WARNING: clean-all removes containers, volumes, and local images for this project."
	@read -r -p "Continue with clean-all? [y/N] " confirm; \
	if [[ "$$confirm" == "y" || "$$confirm" == "Y" ]]; then \
		docker compose down -v --remove-orphans --rmi local; \
	else \
		echo "Cancelled."; \
	fi

prune:
	@echo "WARNING: prune removes unused Docker objects globally on this machine."
	docker system prune -f

shell-web:
	docker exec -it protopilot-web sh

shell-grpc:
	docker exec -it protopilot-grpc-api sh