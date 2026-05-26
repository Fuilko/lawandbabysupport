# LegalShield-jp Deployment Guide

This is the **operator runbook**. Every command shown here must be run by a human
(or by GH Actions on their behalf via SSM).

## 0. Pre-requisites checklist

The human operator needs to confirm these BEFORE running anything:

- [ ] AWS account ID = the same one hosting `Fuilko/SaaSDocker` (hiiforest)
- [ ] EC2 instance `57.182.145.90` is reachable and Docker is running
- [ ] `Fuilko/LegalShield-jp` repo created on GitHub
- [ ] AWS Systems Manager (SSM) Agent is enabled on that EC2 (already true since
      hiiforest already deploys via SSM)
- [ ] DNS for `legalshield.jp` is purchased (registrar TBD)
- [ ] (optional) ACM cert OR Let's Encrypt certbot is ready to issue for the new domain

## 1. GitHub repo secrets

Set these in `https://github.com/Fuilko/LegalShield-jp/settings/secrets/actions`:

| Secret | Value | Notes |
|---|---|---|
| `AWS_ACCESS_KEY_ID`     | `AKIA...`            | same IAM user as hiiforest is fine |
| `AWS_SECRET_ACCESS_KEY` | `...`                | |
| `EC2_INSTANCE_ID`       | `i-0xxxxxxxxxxxxxxxx`| ask the AWS console / human |

Optional repo variables (`Variables` tab, NOT secrets):

| Variable | Default | Notes |
|---|---|---|
| `LEGALSHIELD_BASE_URL` | `https://legalshield.jp` | used by the post-deploy smoke test; switch temporarily to `http://57.182.145.90:8092` while DNS is pending |

## 2. First-time bootstrap on EC2 (one-shot, manual)

SSH OR via SSM Session Manager (the latter avoids opening port 22). One time only:

```bash
# create the second postgres database in hiiforest's container
sudo -u ubuntu docker exec -it sylvanexus_postgres \
  psql -U postgres -c "CREATE DATABASE legalshield;"

# clone the repo
sudo -u ubuntu git clone https://github.com/Fuilko/LegalShield-jp.git \
  /home/ubuntu/LegalShield_jp

# create production env file
sudo -u ubuntu tee /home/ubuntu/LegalShield_jp/.env > /dev/null <<'EOF'
APP_ENV=ec2
DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/legalshield
CORS_ORIGINS=https://legalshield.jp,https://www.legalshield.jp
SITE_BASE_URL=https://legalshield.jp
INCIDENT_OBFUSCATE_MIN_M=100
INCIDENT_OBFUSCATE_MAX_M=300
EOF

# initialise the schema (idempotent)
sudo -u ubuntu docker exec -i sylvanexus_postgres \
  psql -U postgres -d legalshield < /home/ubuntu/LegalShield_jp/db/001_init_schema.sql

# install nginx vhost
sudo cp /home/ubuntu/LegalShield_jp/nginx/legalshield.jp.conf \
        /etc/nginx/sites-available/legalshield.jp.conf
sudo ln -sf /etc/nginx/sites-available/legalshield.jp.conf \
            /etc/nginx/sites-enabled/legalshield.jp.conf

# (option A) Let's Encrypt
sudo certbot --nginx -d legalshield.jp -d www.legalshield.jp \
  --non-interactive --agree-tos -m kenji@hiiforest.com

# (option B) skip TLS for now: comment out the SSL block in legalshield.jp.conf,
#           keep listen 80; then sudo nginx -t && sudo systemctl reload nginx

# bring up the stack
cd /home/ubuntu/LegalShield_jp
sudo -u ubuntu docker compose up -d --build
sudo -u ubuntu docker compose ps
```

## 3. Subsequent deploys

Just `git push origin research`. GH Actions will:

1. **Preflight** — `python -c "from app import main"` to catch import errors cheaply
2. **SSM Run Command** — `git fetch && reset --hard && docker compose up -d --build`
3. **Smoke test** — curl `/health` and `/api/v1/legalshield/region-stats/13`

Rollback = revert the commit, push again. The SSM job is idempotent.

## 4. Loading data

After the stack is up, drop raw files on the EC2 under
`/home/ubuntu/LegalShield_jp/data/raw/` and run:

```bash
sudo -u ubuntu docker compose exec legalshield-api \
  python -m ingest.run_all --datasets n03,houterasu,crime
```

Folder layout expected by `ingest/run_all.py`:

```
data/raw/
├── N03/                       国土数値情報 N03 行政区域 (.shp + sidecars)
├── houterasu/houterasu.csv    法テラス全国事務所 CSV
└── crime/estat_crime.csv      警察庁 / e-Stat 犯罪統計 (prefecture×ym×type×count)
```

NPO and NGO loaders are stubs for now — easy follow-up tasks.

## 5. Multi-project layout invariants (do NOT break)

| Resource | Owner | Rule |
|---|---|---|
| EC2 host | hiiforest first, LegalShield co-tenant | both stacks bind to **127.0.0.1** ports only; host nginx is the public surface |
| postgres container | hiiforest | LegalShield connects via `host.docker.internal:5432`, separate DB `legalshield` |
| postgres data volume | hiiforest | LegalShield never touches it directly |
| nginx | host (Ubuntu nginx, NOT a docker service) | each project ships its own vhost in `nginx/` |
| Route 53 | each project owns its zone | hiiforest.com vs legalshield.jp |
| S3 prefixes | shared bucket OK | `s3://hiiforest-*` vs `s3://legalshield-*` |
| GH Actions IAM user | shared OK | scope by S3 prefix policy if needed |

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `legalshield_api` keeps restarting | top-level import crash | `docker compose logs --tail=80 legalshield-api` |
| API `/health` 200 but `/health/db` 503 | DB connection wrong | check `DATABASE_URL`; from inside the container `pg_isready -h host.docker.internal -p 5432` |
| `ST_AsMVT` errors | PostGIS < 3.0 | hiiforest postgres is 15-3.3 — fine; if you switch to a newer image confirm 3.0+ |
| `nearest-support` returns empty | data not ingested | run `python -m ingest.run_all` |
| `risk-score` 404 | grid not covering point | run N03 + crime ingest, then `REFRESH MATERIALIZED VIEW CONCURRENTLY legalshield.crime_grid_12m` |
| Frontend can't call API across origins | CORS | edit `CORS_ORIGINS` env, `docker compose up -d` |
