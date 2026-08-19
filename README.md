# seguros-arqsoft

Management system for an insurance brokerage: policies, claims, billing and the
alerts that keep any of it from being missed.

## What it does

**Policies.** Full lifecycle with duplicate detection, coverage and insured
sums, and the relationships to insurers and brokers. Renewal alerts fire thirty
days before expiry, because a policy that lapses unnoticed is the expensive
failure in this business.

**Claims.** Each claim carries its documents and its state. The alert engine
watches two clocks independently: paperwork pending for more than thirty days,
and an insurer that has not responded in eight.

**Billing.** The Ecuadorian arithmetic is encoded rather than done by hand —
Superintendencia contribution at 3.5%, Seguro Campesino at 0.5%, and the 5%
early-payment discount inside twenty days. Invoice states and balances follow
from it.

**Reporting.** Excel and PDF generated on demand or on a schedule, with the
generation itself pushed onto Celery so a large report never blocks a request.

## Stack

Django 5 · Celery and Celery beat on Redis · PostgreSQL · Docker Compose ·
Gunicorn. Every row that matters keeps an audit trail through
django-simple-history, and the admin runs on django-unfold.

## Running it

```bash
docker compose up
```

The compose file brings up five services: web, database, Redis, Celery worker
and Celery beat. Without Docker, you need PostgreSQL and Redis reachable, then
the usual `migrate` and `runserver` plus a worker.

## Credits

Built by a team of three. I wrote the application layer — models, views, forms,
services and business rules — and led the project; a teammate built the Docker
setup and the CI pipeline. It won the insurance systems contest at Universidad
Técnica Particular de Loja.
