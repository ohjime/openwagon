# Deploying Wagon (Docker + DigitalOcean)

Wagon ships as a Docker Compose stack: **Postgres + PostGIS** (`db`), the **Django
app** (`web` — gunicorn + a django-tasks worker, run under honcho), and **Caddy**
(`caddy` — automatic HTTPS). Local development is unchanged: use `make server`.

## 1. Provision a droplet
- Create an Ubuntu 24.04 droplet on DigitalOcean (2 GB RAM is plenty to start).
- Point a DNS **A record** for your domain at the droplet's public IP.
- Allow ports 22, 80, 443 through the firewall.

## 2. Install Docker
```bash
ssh root@YOUR_DROPLET_IP
curl -fsSL https://get.docker.com | sh
```
Docker Compose v2 ships with Docker Engine as `docker compose`.

## 3. Code + secrets
```bash
git clone <your-repo-url> wagon && cd wagon
cp env/.env.example env/.env.prod
nano env/.env.prod        # fill in real values
```
`env/.env.prod` is git-ignored. Required values:

| Variable | Notes |
|---|---|
| `DEBUG` | `false` |
| `SECRET_KEY` | long random string |
| `DOMAIN` | e.g. `wagon.example.com` — used by Caddy for the TLS cert |
| `PROD_HOSTS` | your domain (and droplet IP), comma-separated |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | DB credentials (container-internal) |
| `DATABASE_URL` | `postgis://USER:PASSWORD@db:5432/DB` — must match the `POSTGRES_*` values |
| `GOOGLE_MAPS_API_KEY` | your Maps key |
| `FIRST_ADMIN_USERNAME` / `FIRST_ADMIN_PASSWORD` | superuser created on first boot (`FIRST_ADMIN_EMAIL` optional) |
| `WEB_CONCURRENCY` | gunicorn workers, e.g. `2` |
| `AWS_*` | optional — only if you wire up S3 storage / SES email |

## 4. Launch
```bash
docker compose up -d --build      # or: make deploy
docker compose logs -f            # or: make logs
```
On first boot the `web` container runs migrations (which `CREATE EXTENSION postgis`
and create the cache/task tables), creates the admin user from `FIRST_ADMIN_*`, then
starts gunicorn + the worker. Caddy fetches a Let's Encrypt certificate for `$DOMAIN`.

Visit `https://YOUR_DOMAIN` — the app and `/admin/` should load over HTTPS.

## Operations
- **Update / redeploy:** `git pull && docker compose up -d --build`
- **Migrations:** run automatically on container start.
- **DB backup:**
  ```bash
  docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup_$(date +%F).sql
  ```
  Schedule it via cron and/or enable DigitalOcean volume snapshots.
- **Django shell:** `docker compose exec web uv run --no-sync src/main.py shell`
- **Tail one service:** `docker compose logs -f web`

## Notes
- This is a single-droplet deployment: one host, self-managed backups. To scale
  later, swap the `db` service for **DigitalOcean Managed Postgres** (which supports
  PostGIS) and point `DATABASE_URL` at it — no application changes required.
- `env/fbsvc.json` (a Firebase service-account key, if the mobile app uses it) is
  git-ignored. Keep it — and `env/.env.prod` — out of version control.
