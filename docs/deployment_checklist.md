Cloud Run ↔ Cloud SQL PostgreSQL Deployment Checklist

## Objective

Deploy FastAPI on **Cloud Run** and connect it securely to **Cloud SQL for PostgreSQL**.

Cloud SQL for PostgreSQL is Google’s managed PostgreSQL service. Google documents Cloud Run connectivity to Cloud SQL, including the use of private IP and matching VPC egress configuration. ([Google Cloud Documentation][9])

## A. Cloud SQL setup checklist

### Instance creation

* create a **Cloud SQL for PostgreSQL** instance
* choose startup-sized machine/resources
* create the application database
* create a non-admin application DB user
* keep a separate admin user for maintenance/migrations

Cloud SQL instance creation starts with a PostgreSQL instance that includes a default `postgres` database, and Google provides dedicated instance creation flows for PostgreSQL. ([Google Cloud Documentation][10])

### Backups and recovery

* enable **automated daily backups**
* set backup retention to meet your internal policy
* enable point-in-time recovery if required
* verify restore procedure at least once

### Network

* enable **private IP**
* attach the instance to the intended VPC
* do not expose the database publicly unless there is a hard requirement

Google’s Cloud Run-to-Cloud SQL guidance states that for direct private connectivity, the Cloud SQL instance must have a private IP and Cloud Run egress must use the same VPC. ([Google Cloud Documentation][11])

## B. IAM and secrets checklist

### Service account

* create a dedicated service account for the Cloud Run API service
* assign the **Cloud SQL Client** role to that service account

Google’s Cloud SQL docs for Cloud Run connectivity call out the required service account role for connecting from Cloud Run to Cloud SQL. ([Google Cloud Documentation][11])

### Secret storage

Store these in Secret Manager or equivalent:

* DB name
* DB user
* DB password
* instance connection name
* any app secrets such as JWT signing key

Do not hardcode credentials in source code or images.

## C. Cloud Run networking checklist

### Runtime

* deploy on **Cloud Run 2nd gen**
* configure the service to use the dedicated service account
* set region to match the Cloud SQL instance region where possible

### VPC

* configure **Direct VPC egress**
* ensure the Cloud Run service can egress into the same VPC used by Cloud SQL private IP

Google’s Cloud Run / Cloud SQL docs describe using Direct VPC egress or connectors for private-IP communication into the VPC. ([Google Cloud Documentation][11])

## D. Application connection checklist

### Python stack

Recommended app stack:

* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL driver: `psycopg`
* optionally Cloud SQL Python Connector if that is the pattern you use

SQLAlchemy supports PostgreSQL through dialects and DBAPI drivers, and Psycopg is the standard PostgreSQL adapter for Python. ([SQLAlchemy][12])

### Engine and pooling

Configure:

* one shared SQLAlchemy engine per process
* connection pooling enabled
* conservative pool size
* `pool_pre_ping=True`
* bounded overflow
* sensible recycle timeout if needed

SQLAlchemy engines use a connection pool, and the engine does not create the first actual DBAPI connection until first use. ([SQLAlchemy][4])

### Environment variables

Typical set:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME
INSTANCE_CONNECTION_NAME=project:region:instance
DB_NAME=appdb
DB_USER=appuser
DB_PASSWORD=***
```

## E. FastAPI deployment checklist

### Container

* Dockerize the FastAPI service
* expose the port expected by Cloud Run
* use production ASGI startup command
* keep container stateless

### Startup behavior

* do not open a new DB connection per request
* initialize engine/sessionmaker once
* run schema migrations separately from normal request handling

## F. Scaling and connection safety checklist

This is the main operational risk area for Cloud Run + PostgreSQL.

### Control Cloud Run scale

Set carefully:

* min instances = 0 initially
* max instances = conservative cap
* concurrency = moderate, not extreme

### Control DB connections

Set carefully:

* pool size per instance
* max overflow
* request timeout and retry policy in app

Why this matters:
`max Cloud Run instances × per-instance DB pool` determines your worst-case connection pressure.

## G. Release checklist

Before first production cutover:

* Cloud SQL instance created
* private IP configured
* backups enabled
* application DB user created
* service account created
* Cloud SQL Client role assigned
* secrets stored securely
* Cloud Run service deployed
* VPC egress configured
* Alembic migrations applied
* application health check passes
* CRUD smoke tests pass
* rollback plan documented

## H. Day-2 operations checklist

After go-live:

* monitor DB CPU, memory, storage, and connection count
* monitor Cloud Run error rate and latency
* verify daily backups are succeeding
* perform one restore drill
* review slow queries
* scale DB and Cloud Run separately based on actual usage
