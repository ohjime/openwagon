# Deploying Waygon (Docker + DigitalOcean)

Waygon ships as a Docker Compose stack (`docker/docker-compose.yml`): **Postgres +
PostGIS** (`db`); a one-shot **release** service that migrates, builds the cache
table, and bootstraps the first admin; the **Django app** (`web` — gunicorn); a
django-tasks **worker**; and **Caddy** (`caddy` — automatic HTTPS). The image is
built once (from the `web` service) and reused by `release` and `worker`. Local
development is unchanged: use `make server`.

## 1. Provision a droplet
- Create an Ubuntu 24.04 droplet on DigitalOcean (2 GB RAM is plenty to start).
- Point a DNS **A record** at the droplet's public IP for **every hostname you serve** —
  e.g. both `waygon.dev` and `admin.waygon.dev`. Caddy fetches a separate TLS cert per
  name, so each must resolve to the droplet before launch.
- Allow ports 22, 80, 443 through the firewall.

## 2. Install Docker
```bash
ssh root@YOUR_DROPLET_IP
curl -fsSL https://get.docker.com | sh
```
Docker Compose v2 ships with Docker Engine as `docker compose`.

## 3. Code + secrets
```bash
git clone <your-repo-url> waygon && cd waygon
cp env/.env.prod.example env/.env.prod
nano env/.env.prod        # fill in real values  (or run `make docker-env`)
```
`env/.env.prod` is git-ignored. Required values:

| Variable | Notes |
|---|---|
| `DEBUG` | `false` |
| `SECRET_KEY` | long random string |
| `SITE_ADDRESS` | every hostname Caddy serves, comma-separated, e.g. `waygon.dev, admin.waygon.dev` — one TLS cert per name |
| `PROD_HOSTS` | Django allowed hosts/CSRF. A leading dot is a wildcard: `.waygon.dev` matches the apex **and** every subdomain (covers `admin.` automatically) |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | DB credentials (container-internal) |
| `DATABASE_URL` | `postgis://USER:PASSWORD@db:5432/DB` — must match the `POSTGRES_*` values |
| `GOOGLE_MAPS_API_KEY` | your Maps key |
| `FIRST_ADMIN_USERNAME` / `FIRST_ADMIN_PASSWORD` | superuser created on first boot (`FIRST_ADMIN_EMAIL` optional) |
| `WEB_CONCURRENCY` | gunicorn workers, e.g. `2` |
| `AWS_*` / `DEFAULT_FROM_EMAIL` | optional — S3 media + SES email; see the **AWS** section below |

## 4. Launch
The Compose stack lives in `docker/` and is driven through the Makefile (which runs
it from the repo root via `--project-directory .`). Launch with:
```bash
make docker-deploy      # git pull + build + up -d + image prune
make docker-logs        # follow all services
```
On every `up` the one-shot `release` service runs first: it applies migrations (which
`CREATE EXTENSION postgis` and create the cache/task tables) and creates the admin
user from `FIRST_ADMIN_*`. Once it exits successfully, `web` (gunicorn) and `worker`
(django-tasks) start. Caddy fetches a Let's Encrypt certificate for every hostname in
`SITE_ADDRESS`.

Visit `https://waygon.dev` — the app loads over HTTPS. The admin is reachable two ways:
`https://waygon.dev/admin/` and, via host routing, at the root of the admin subdomain
`https://admin.waygon.dev/`. Both are the same Django app and database; the subdomain
is mapped to the admin urlconf by `config/middleware.py` (`SubdomainURLConf`), so no
extra Caddy block or service is needed.

> Adding another subdomain later (e.g. `api.waygon.dev`) is two steps: add it to
> `SITE_ADDRESS` (so Caddy gets a cert) and, if it should serve a different tree at its
> root, add a `"<prefix>.": "config.urls_<x>"` entry to `SUBDOMAIN_URLCONFS`. `PROD_HOSTS`
> already covers it via the `.waygon.dev` wildcard.

## AWS — S3 media + SES email (optional)

Both integrations are **dormant by default**: with no AWS vars set, media is stored
on the local Docker volume and email is printed to the container logs, so the stack
runs fine without an AWS account. They activate independently from the values in
`env/.env.prod`:

| Integration | Activates when | Otherwise |
|---|---|---|
| **S3 media** (`django-storages`) | `AWS_STORAGE_BUCKET_NAME` is set | local filesystem (`MEDIA_ROOT`) |
| **SES email** (`django-anymail`) | AWS keys set **and** `DEBUG=false` | console backend (logs) |

**1. IAM user.** Create an IAM user with programmatic access and a policy granting:
- S3: `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on `arn:aws:s3:::BUCKET/*`
  and `s3:ListBucket` on `arn:aws:s3:::BUCKET`.
- SES: `ses:SendEmail` and `ses:SendRawEmail`.

Put the key/secret in `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

**2. S3 bucket (media).** Create a bucket in your region; the name is globally
unique, e.g. `waygon-bucket`. Set `AWS_STORAGE_BUCKET_NAME` to it and
`AWS_S3_REGION_NAME` to its region. Media is served from
`https://<bucket>.s3.amazonaws.com/`, so allow public read on the objects you want
web-visible (or front the bucket with CloudFront). Note: waygon's models don't store
uploads yet, so the bucket only does anything once a `FileField`/`ImageField` is
added — setting it now is harmless and future-proofs the deploy.

**3. SES email.** Verify a sender domain (or a single address) in the SES console and
set `DEFAULT_FROM_EMAIL` to a verified address (e.g. `noreply@waygon.example.com`).
SES uses `AWS_S3_REGION_NAME` as its region, so keep the bucket and SES in the same
region (or verify SES accordingly). New SES accounts start in the **sandbox** (you
can only send to verified recipients) — request production access before emailing
real users.

**4. Apply.** Add the values to `env/.env.prod` — the `make docker-env` wizard prompts
for all of them — then redeploy with `make docker-deploy`. Confirm which backend is live:

```bash
make docker-shell   # then:
#   from django.core.files.storage import default_storage
#   print(type(default_storage).__name__)
# S3Storage when the bucket is set, FileSystemStorage otherwise
```

## Operations
All targets wrap `docker compose -f docker/docker-compose.yml --project-directory .`
— run them from the repo root.
- **Update / redeploy:** `make docker-deploy` (git pull + build + up + prune)
- **Migrations:** run automatically by the `release` service on every `up`
  (`make docker-migrate` to run by hand against the `web` container).
- **DB backup:**
  ```bash
  docker compose -f docker/docker-compose.yml --project-directory . \
    exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup_$(date +%F).sql
  ```
  Schedule it via cron and/or enable DigitalOcean volume snapshots.
- **Django shell:** `make docker-shell`
- **Tail one service:** `make docker-logs-web` (or `make docker-logs` for all services)

## Notes
- This is a single-droplet deployment: one host, self-managed backups. To scale
  later, swap the `db` service for **DigitalOcean Managed Postgres** (which supports
  PostGIS) and point `DATABASE_URL` at it — no application changes required.
- `env/fbsvc.json` (a Firebase service-account key, if the mobile app uses it) is
  git-ignored. Keep it — and `env/.env.prod` — out of version control.
