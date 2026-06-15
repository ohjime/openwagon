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
ifdef run
	@echo "Running command in Server Environment..."
	@cd src/server \
		&& $(run)
else
	@reset
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

server-clean:
	@echo "${RED}Cleaning Server${NC}..."
	@echo "Deleting __pycache__ directories"
	@cd src/server/src \
		&& find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Deleting old migration files (preserving core/0001_initial.py)"
	@cd src/server/src \
		&& find . -type f -path "*/migrations/*.py" ! -name "__init__.py" ! -path "*/core/migrations/0001_initial.py" -exec rm -f {} +
	@echo "Deleting default SQLite databases"
	@cd src/server \
		&& find . -type f -name "db.sqlite3" -exec rm -f {} +
	@echo "Wiping PostgreSQL database wagon_db and dropping all tables..."
	@cd src/server \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='wagon_db' AND pid <> pg_backend_pid();" \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c "DROP DATABASE IF EXISTS wagon_db;" \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c 'DROP OWNED BY admin CASCADE;' || true \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c 'DROP USER IF EXISTS admin;' || true

superuser:
	@echo "Creating superuser for Central Backend...\n"
	@echo "Installing dependencies...\n"
	@cd src/server \
		&& uv sync
	@cd src/server \
		&& uv run src/main.py createsuperuser

# TODO: Make names dev-specific so on server clean production isn't affected
dev-db:
	@echo "Setting up PostgreSQL database...\n"
	@cd src/server \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c "CREATE USER admin WITH PASSWORD 'changeme';" \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c "ALTER USER admin WITH SUPERUSER;" \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c "CREATE DATABASE wagon_db OWNER admin;" \
		&& psql -h localhost -p 5432 -U $(USER) -d wagon_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"

macos-env:
	@echo "Setting up macOS development environment...\n"
	@cd src/server \
		&& brew install gdal \
		&& brew install proj \
		&& brew install geos

fake-data:
	@echo "Setting up mock data...\n"
	@cd src/server \
		&& WAGON_SKIP_GOOGLE=1 printf "from core.fake import generate\ngenerate(40)\n" | uv run src/main.py shell

# --- Production (Docker on a DigitalOcean droplet) ---
deploy:
	@echo "Building and starting the production stack (docker compose)...\n"
	@docker compose up -d --build

logs:
	@docker compose logs -f
