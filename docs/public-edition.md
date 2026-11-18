# Ticketing Demo: Public Edition Boundaries

This repository is a deliberately scoped portfolio edition of a private product. It is designed to remain executable and technically representative without publishing production credentials, customer data, deployment details, or third-party payment integration code.

## Included

- The complete Next.js user interface and responsive layouts.
- Strict TypeScript types generated from the FastAPI OpenAPI contract.
- Authentication, role-based navigation, and guest checkout access.
- Event, session, sale group, and ticket type management.
- Review, approval, publishing, and unpublishing workflows.
- Temporary reservations and stock conversion.
- PDF ticket generation, email delivery, and QR-based validation.
- PostgreSQL persistence, Alembic migrations, Redis integration, and S3-compatible object storage.
- Automated backend, frontend, contract, type, lint, and build checks.

## Simulated Locally

- Payments use an internal demo provider. It creates no external payment intent and requests no card details.
- Email is delivered to Mailpit instead of a real mailbox.
- Object storage uses MinIO instead of a production bucket.
- Seeded events, images, credentials, and contact addresses are fictional and intended only for local evaluation.

## Intentionally Excluded

- Live payment provider SDKs, webhooks, signatures, and reconciliation rules.
- Production domains, cloud resources, infrastructure-as-code, and deployment credentials.
- Customer, order, analytics, or operational data from the private product.
- Monitoring destinations, alerting integrations, and private support processes.
- The private repository history and internal delivery workflow.

## Usage Constraint

The repository is licensed for portfolio review and technical evaluation only. Public visibility does not grant permission to commercialize, redistribute, deploy, or create derivative products from the source code. See `LICENSE` for the applicable terms.
