RED="'\033[0;31m'"
NC="'\033[0m'"

wiki:
	@echo "Starting Documentation Server...\n"
	@cd docs \
		&& npm start

wiki-build:
	@echo "Building Documentation Server...\n"
	@cd docs \
		&& npm install @docusaurus/eslint-plugin@latest --save-dev \
		&& npm install \
		&& npm dedupe \
		&& npm run build

server:
ifeq ($(run),clean)
	@echo "${RED}Cleaning Server${NC}..."
	@echo "Deleting Python Cache..."
	@cd src/server/src \
		&& find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Deleting Django Migrations (preserving core/0001_initial.py)..."
	@cd src/server/src \
		&& find . -type f -path "*/migrations/*.py" ! -name "__init__.py" ! -path "*/core/migrations/0001_initial.py" -exec rm -f {} +
	@echo "Deleting Database (dev PostGIS container + volume)..."
	@-$(DC_DB) down -v
	@echo "Deleting Node Modules..."
	@cd src/server/vite \
		&& find . -type d -name "node_modules" -exec rm -rf {} +
	@echo "Deleting Vite Builds..."
	@rm -rf src/server/vite/static
	@echo "Deleting Virtual Environments..."
	@find . -type d -name ".venv" -exec rm -rf {} +
else ifdef run
	@echo "Running command in Server Environment..."
	@cd src/server \
		&& $(run)
else
	@reset
	@echo "GeoDjango requires PostGIS: run 'make db' first, or point DATABASE_URL in env/.env elsewhere."
	@chmod +x bin/clean_honcho.sh
	@echo "${RED}Killing Orphaned Django Processes...${NC}"
	@./bin/clean_honcho.sh
	@echo "\nInstalling dependencies...\n"
	@cd src/server \
		&& uv sync
	@echo "\nBuilding Vite Assets..."
	@cd src/server/vite \
		&& npm install \
		&& npm run build
	@echo "\nMaking Migrations...\n"
	@cd src/server \
		&& uv run src/main.py makemigrations \
		&& uv run src/main.py migrate
	@echo "\nCreating cache table...\n"
	@cd src/server \
		&& uv run src/main.py createcachetable
	@echo "\nCentral Development Server is ready to run 🏃!\n"
	@echo "Starting Server...\n"
	@cd src/server \
		&& uv run src/main.py proc runserver --procfile procfile.dev
endif

# Standalone Postgres + PostGIS for a native development server; requires Docker Compose.
DC_DB = docker compose -f docker/docker-compose.db.yml --project-directory . --project-name waygon-db-dev

.PHONY: db db-down db-logs db-shell

db:
	$(DC_DB) up -d --wait

db-down:
	$(DC_DB) down

db-logs:
	$(DC_DB) logs -f db

db-shell:
	$(DC_DB) exec db psql -U admin -d waygon_db

superuser:
	@echo "Creating superuser for Central Backend...\n"
	@echo "Installing dependencies...\n"
	@cd src/server \
		&& uv sync
	@cd src/server \
		&& uv run src/main.py createsuperuser

# GeoDjango native libraries (GDAL/GEOS/PROJ) for the native development server.
macos-env:
	@echo "Setting up macOS development environment...\n"
	@brew install gdal proj geos

linux-env:
	@echo "Setting up Linux (Debian/Ubuntu) development environment...\n"
	@sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev proj-bin

fake-data:
	@echo "Setting up mock data...\n"
	@cd src/server \
		&& WAYGON_SKIP_GOOGLE=1 printf "from core.fake import generate\ngenerate(40)\n" | uv run src/main.py shell

# --- Mobile (Flutter) ---
# Build a release build and install/launch it on the iPhone 12 mini (connected
# over Wi-Fi or USB). Override the target with DEVICE=<id> (see `flutter devices`).
IPHONE12MINI = 00008101-000A0CE02202001E

.PHONY: mobile-release

mobile-release:
	@echo "Building mobile release for iPhone 12 mini...\n"
	@cd src/mobile \
		&& flutter pub get \
		&& flutter run --release -d $(or $(DEVICE),$(IPHONE12MINI))

# --- Docker / production ---
# Compose lives in docker/; run it from the repo root so the relative paths inside
# (build context, env/.env, docker/Caddyfile) resolve correctly.
DC = docker compose -f docker/docker-compose.yml --project-directory . --env-file env/.env

# Branch that docker-deploy checks out. Defaults to whatever this host is on.
BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)

.PHONY: docker-env docker-build docker-up docker-down docker-restart docker-logs docker-logs-web docker-ps docker-shell docker-migrate docker-prune docker-deploy

docker-env:
	@chmod +x bin/setup_env.sh
	@bin/setup_env.sh

# Build the web image (tags waygon-web:latest, which release/worker reuse).
docker-build:
	$(DC) build web

docker-up:
	$(DC) up -d

docker-down:
	$(DC) down

docker-restart:
	$(DC) restart

docker-logs:
	$(DC) logs -f

# Follow the Django app server (gunicorn): print() output, tracebacks, and access
# logs. Override line count with TAIL=N (default 100).
docker-logs-web:
	$(DC) logs -f --tail=$(or $(TAIL),100) web

docker-ps:
	$(DC) ps

docker-shell:
	$(DC) exec web python src/main.py shell

docker-migrate:
	$(DC) exec web python src/main.py migrate

docker-prune:
	docker image prune -f

# Deploy a branch: fetch, switch to it, fast-forward, rebuild, restart.
# Override the branch with BRANCH=name (default: current checkout).
#   make docker-deploy
#   make docker-deploy BRANCH=feature/x
# Build first, then up: release/worker only reference waygon-web:latest (no
# build: section), so a single `up --build` makes compose try to PULL that
# local-only tag before web builds it, which fails.
docker-deploy:
	@echo "Deploying $(BRANCH)..."
	git fetch origin --prune
	git checkout $(BRANCH)
	git merge --ff-only origin/$(BRANCH)
	$(DC) build web
	$(DC) up -d
	docker image prune -f
