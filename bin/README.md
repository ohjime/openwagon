# bin/ — helper scripts

Small shell helpers used by the Makefile and the production container.

- **clean_honcho.sh** — kill orphaned dev processes (`runserver` / `db_worker` /
  gunicorn) left by a previous `make server`, so a restart doesn't hit
  "address already in use". Invoked automatically by `make server`.

  Production no longer uses a single entrypoint script: `docker/docker-compose.yml`
  splits the work into separate services — `release` (migrate + `createcachetable`
  + `bootstrap_admin`), `web` (gunicorn), and `worker` (django-tasks). The image's
  default `CMD` is gunicorn (the `web` role).

- **setup_env.sh** — interactively build `env/.env.prod` for the docker-compose
  stack (Django, Postgres/PostGIS, Google Maps, AWS S3 + SES, first admin). Run it
  via `make docker-env`. Writes the file at mode 600; `env/.env.prod` is git-ignored —
  never commit it.
