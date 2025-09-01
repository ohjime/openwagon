RED="'\033[0;31m'"
NC="'\033[0m'"

env:
ifdef for
ifeq ($(for),macos)
	@reset
	@printf "\033[1;4;34m\nInstalling Project Enviornment for MacOS M1\033[0m\n"
	@printf "\033[1;4;34m\n1. Installing Homebrew...\n\033[0m\n"
	@/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || true
	@brew update || true
	@printf "\033[1;4;34m\n2. Adding Homebrew to PATH...\n\033[0m\n"
	@export PATH="/usr/local/bin:$PATH"
	@echo '/usr/local/bin added to PATH'
	@printf "\033[1;4;34m\n3. Installing npm...\n\033[0m\n"
	@brew install npm || true
	@printf "\033[1;4;34m\n4. Updating npm globally...\n\033[0m"
	@npm install -g npm@latest || true
	@printf "\033[1;4;34m\n5. Installing dotenv-cli globally with npm...\n\033[0m"
	@npm install -g dotenv-cli || true
	@printf "\033[1;4;34m\n6. Installing uv...\n\033[0m\n"
	@brew install uv || true
	@printf "\033[1;4;34m\n7. Installing PostgreSQL...\n\033[0m\n"
	@brew install postgresql || true
	@printf "\033[1;4;34m\n8. Starting PostgreSQL service...\n\033[0m\n"
	@brew services restart postgresql || true
	@printf "\033[1;4;34m\n9. Installing PostGIS...\n\033[0m\n"
	@brew install postgis || true
	@printf "\033[1;4;34m\n10. Installing GDAL, PROJ, and GEOS...\n\033[0m\n"
	@brew install gdal proj geos || true
	@printf "\033[1;4;34m\n11. Initializing Xcode...\n\033[0m\n"
	@sudo sh -c 'xcode-select -s /Applications/Xcode.app/Contents/Developer && xcodebuild -runFirstLaunch' || true
	@echo "Xcode Initialized"
	@printf "\033[1;4;34m\n12. Installing Xcode CLI Tools...\n\033[0m\n"
	@xcode-select --install || true
	@printf "\033[1;4;34m\n13. Accepting Xcode Agreements...\n\033[0m\n"
	@sudo xcodebuild -license accept || true
	@echo "Xcode Agreements have been Accepted"
	@printf "\033[1;4;34m\n14. Installing Firebase CLI...\n\033[0m"
	@npm install -g firebase-tools --loglevel=error || true
	@printf "\033[1;4;34m\n15. Logging into Firebase...\n\033[0m\n"
	@firebase login || true
	
	@printf "\033[1;4;34m\n16. Installing Flutter SDK to $HOME/flutter and updating PATH...\n\033[0m\n"
	@FLUTTER_DIR="$$HOME/flutter"; \
	if [ -d "$$FLUTTER_DIR/.git" ]; then \
	  echo "Flutter already installed at $$FLUTTER_DIR"; \
	else \
	  echo "Setting up Flutter in $$FLUTTER_DIR..."; \
	  rm -rf "$$FLUTTER_DIR"; \
	  git clone https://github.com/flutter/flutter.git -b stable "$$FLUTTER_DIR" || true; \
	fi
	@ZSHRC="$$HOME/.zshrc"; \
	LINE='export PATH="$$HOME/flutter/bin:$$PATH"'; \
	grep -qxF "$$LINE" "$$ZSHRC" 2>/dev/null || echo "$$LINE" >> "$$ZSHRC"; \
	echo "Ensured Flutter is on PATH in $$ZSHRC"; \
	/bin/zsh -lc 'flutter --version || $$HOME/flutter/bin/flutter --version' || true

	@printf "\033[1;4;34m\n17. Installing Flutter VSCode Extensions...\n\033[0m\n"
	@code --install-extension Dart-Code.flutter || true
	@printf "\033[1;4;34m\nMacOS Development Environment Setup Complete\n\033[0m\n"

else
	@printf "\033[1;4;34m\n'${for}' is not a recognized platform\n\033[0m\n"
	@printf "\033[1;4;34mSupported platforms are:\n1. macos\n2. linux\n3. windows\033[0m\n"
endif
else
	@printf "\033[1;4;34m\n No platform specified. Supported platforms are:\033[0m\n"
	@printf "\033[1;4;34m\n\t1. macos\n\t2. linux\n\t3. windows\033[0m\n"
	@printf "\033[1;4;34m\n Please re-run your command with an appropriate platform flag. For example:\n\033[0m\n"
	@printf "\033[1;4;34m>>> make env for=macos\n\033[0m\n"
endif

doc:
	@echo "Starting Documentation Server...\n"
	@cd docs \
		&& npm start

mobile:
ifdef for
ifeq ($(for),ios)
	@printf "\033[1;4;34m\nBuilding Mobile Application for iOS\033[0m\n"
	@printf "\033[1;4;34m\n1. Cleaning Previous Builds...\033[0m\n\n"
	@cd src/mobile/ios \
		&& flutter clean
	@printf "\033[1;4;34m\n2. Fetching Flutter and Dart Packages...\033[0m\n\n"
	@cd src/mobile/ \
		&& flutter pub get \
		&& dart pub get
	@printf "\033[1;4;34m\n3. Configuring Flutter for iOS...\033[0m\n\n"
	@cd src/mobile/ \
		&& flutter config --no-enable-android \
		&& flutter config --enable-ios
	@printf "\033[1;4;34m\n4. Updating CocoaPods repo and installing pods...\033[0m\n\n"
	@cd src/mobile/ios \
		&& pod repo update \
		&& pod install
	@printf "\033[1;4;34m\n5. Activating FlutterFire...\033[0m\n\n"
	@cd src/mobile/ \
		&& dart pub global activate flutterfire_cli
	@printf "\033[1;4;34m\n6. Starting FlutterFire Configuration Setup...\033[0m\n\n"
	@cd src/mobile/ \
		&& flutterfire configure
	@printf "\033[1;4;34m\n7. Building Mobile for iOS (Grab a Coffee this will take a while)...\033[0m\n\n"
	@cd src/mobile/ \
		&& flutter run
else
	@printf "\033[1;4;34m\n'${for}' is not a recognized platform\n\033[0m\n"
	@printf "\033[1;4;34mSupported platforms are:\n1. ios\n2. android\n"
endif
else
	@printf "\033[1;4;34m\n No platform specified. Supported platforms are:\033[0m\n"
	@printf "\033[1;4;34m\n\t1. ios\n\t2. android\n"
	@printf "\033[1;4;34m\n Please re-run your command with an appropriate platform flag. For example:\n\033[0m\n"
	@printf "\033[1;4;34m>>> make mobile for=ios\n\033[0m\n"
endif

server:
ifdef run
	@echo "Running command in Server Environment..."
	@cd src/server \
		&& $(run)
else
	@reset
	@echo "${RED}Killing Orphaned Django Processes...${NC}"
	@./bin/kill_honcho.sh
	@echo "\nInstalling dependencies...\n"
	@cd src/server \
		&& uv sync
	@echo "\nBuilding Vite Assets..."
	@cd src/server/vite \
		&& npm install \
		&& npm run build
	@echo "\nMaking Migrations...\n"
	@cd src/server \
		&& uv run lib/main.py makemigrations \
		&& uv run lib/main.py migrate
	@echo "\nRunning tests...\n"
	@echo "All tests passed!\n"
	@echo "Central Development Server is ready to run 🏃!\n"
	@echo "Starting Server...\n"
	@cd src/server \
		&& uv run lib/main.py vite runserver
endif

superuser:
	@echo "Creating superuser for Central Backend...\n"
	@echo "Installing dependencies...\n"
	@cd src/server \
		&& uv sync
	@cd src/server \
		&& uv run lib/main.py createsuperuser

db:
	@echo "\nSetting up Database from src/server/env/.env ...\n"
	@npx -y -p dotenv-cli dotenv -e src/server/env/.env -- sh -c 'psql -h localhost -p 5432 -U $$USER -d postgres -c \
		"CREATE USER $$DB_USER WITH PASSWORD '\''$$DB_PASSWORD'\'';" || \
		echo "Skipping User Creation..." && \
		psql -h localhost -p 5432 -U $$USER -d postgres -c \
		"ALTER USER $$DB_USER WITH PASSWORD '\''$$DB_PASSWORD'\'';"'
	@npx -y -p dotenv-cli dotenv -e src/server/env/.env -- sh -c 'psql -h localhost -p 5432 -U $$USER -d postgres -c \
		"ALTER USER $$DB_USER WITH SUPERUSER;"'
	@npx -y -p dotenv-cli dotenv -e src/server/env/.env -- sh -c 'psql -h localhost -p 5432 -U $$USER -d postgres -c \
		"CREATE DATABASE $$DB_NAME OWNER $$DB_USER;" || \
		echo "Skipping Database Creation..." && \
		psql -h localhost -p 5432 -U $$USER -d postgres -c \
		"ALTER USER $$DB_USER WITH PASSWORD '\''$$DB_PASSWORD'\'';"'
	@npx -y -p dotenv-cli dotenv -e src/server/env/.env -- sh -c 'psql -h localhost -p 5432 -U $$USER -d postgres -c \
		"ALTER DATABASE $$DB_NAME OWNER TO $$DB_USER;"'
	@echo "\nDatabase setup complete.\n"

data:
	@echo "Generating mock server data...\n"
	@cd src/server \
		&& WAGON_SKIP_GOOGLE=1 printf "from trip.fake import TripFactory\nTripFactory.bulk(10)\n" | uv run lib/main.py shell

clean:
	@echo "${RED}Cleaning Server${NC}..."
	@echo "Deleting __pycache__ directories"
	@cd src/server/lib \
		&& find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Deleting old migration files"
	@cd src/server/lib \
		&& find . -type f -path "*/migrations/*.py" ! -name "__init__.py" -exec rm -f {} +
	@echo "Deleting default SQLite databases"
	@cd src/server \
		&& find . -type f -name "db.sqlite3" -exec rm -f {} +
	@echo "Wiping PostgreSQL  and dropping all tables..."
	@cd src/server \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c "DROP DATABASE IF EXISTS wagon_db;" \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c 'DROP OWNED BY admin CASCADE;' || true \
		&& psql -h localhost -p 5432 -U $(USER) -d postgres -c 'DROP USER IF EXISTS admin;' || true
