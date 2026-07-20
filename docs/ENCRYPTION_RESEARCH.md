# Encryption at Rest — Research Note

**HD-PHASE8-004 — Research Artefact**
**Date:** 2026-07-20
**Status:** Decision recorded in `docs/PRODUCTION_DEPLOYMENT.md` §3.

This document records the encryption-at-rest options considered for the Techno
Service AI Intelligence System production database (PostgreSQL 15.18 on
Windows 11). It is research, not implementation. The chosen approach is
recorded in `docs/PRODUCTION_DEPLOYMENT.md` §3.

---

## 1. Threat Model (Scope of "At Rest")

"At rest" means: data that resides on durable storage. Threats in scope:

- Theft of the physical disk (laptop stolen, drive pulled, data centre drive
  decommissioned without sanitisation).
- Unauthorised access by an OS-level actor (another user on the same host,
  backup operator with raw file access).
- Backup file leak (`pg_dump` output or `pg_basebackup` taken off-host).

Out of scope (handled elsewhere):

- Data in motion (TLS at the application layer; not part of this gate).
- Application-layer access control (RBAC, 2FA — covered in Phase 1/8).
- Memory scraping (mitigated by short-lived sessions + secrets env).

The audit log is **already** immutable (HD-PHASE8-003 — UPDATE/DELETE blocked
at the data layer with `Constitution Article XX` triggers). This gate covers
**confidentiality**, not integrity.

---

## 2. Options Considered

### Option A — BitLocker Full-Drive Encryption (Windows native)

**Description:** Windows BitLocker encrypts the entire drive on which PostgreSQL
data files reside. Performed at the OS layer, completely transparent to
PostgreSQL.

**Pros:**

- Full coverage — every file on the drive is encrypted (data, WAL, temp
  files, swap, logs).
- Transparent to PostgreSQL — no schema change, no app change, no performance
  overhead.
- Native Windows tooling (`manage-bde`, Active Directory key escrow).
- FIPS 140-2 compliant with TPM 2.0.

**Cons:**

- **Requires Windows Pro/Enterprise/Education.** Not available on Windows
  Home editions.
- Single key tied to the host. Key recovery is the OS's responsibility.
- If the host is online and the user is signed in, BitLocker is transparent —
  it does **not** protect against an attacker who has user credentials.

**Effort:** Low (enable via Settings or `manage-bde -on C:`).

**Applicability to this host:** **NOT APPLICABLE.** The production build host
runs **Windows 11 Home (Core) edition**, where BitLocker is unavailable.
Verified: `Get-ComputerInfo` returns `WindowsEditionId = Core`; `manage-bde
-status` returns *"An attempt to access a required resource was denied"*,
indicating the BitLocker Device Encryption (the limited Home edition variant)
is also not active on this device.

### Option B — pgcrypto Column-Level Encryption (PostgreSQL extension)

**Description:** Install the `pgcrypto` PostgreSQL extension. Use
`pgp_sym_encrypt(plaintext, key)` / `pgp_sym_decrypt(ciphertext, key)` to
encrypt specific sensitive columns at write time, decrypt at read time.
Encryption happens inside the database; key supplied per session (typically
via an env var read in the application layer and passed in the connection).

**Pros:**

- Available on the current host. Verified: `SELECT * FROM
  pg_available_extensions WHERE name='pgcrypto'` returns
  `pgcrypto | 1.3`.
- Portable across OS / cloud / host. No Windows-Pro dependency.
- Granular — only the columns that need it are encrypted (e.g.
  `audit_log.payload_json`, future PII columns).
- Mature, widely used, included in the standard PostgreSQL contrib.
- Constitutional-friendly: the schema (column types, names, triggers) does
  **not** change. The data stored in the columns is encrypted; the column
  shape is identical.

**Cons:**

- Only the columns explicitly encrypted are protected. Anything written
  unencrypted (other tables, other columns) remains plaintext on disk.
- Application must decrypt on every read of an encrypted column. Small
  per-call overhead.
- Key management: the application must supply the key on each session.
  The key is held in process memory; a memory-scraping attacker can
  recover it.
- Test surface: code that reads encrypted columns must know to decrypt
  first.

**Effort:** Medium (install extension + modify audit write/read path + add
tests).

**Applicability to this host:** **YES.**

### Option C — Application-Layer Encryption (encrypt before storing)

**Description:** Encrypt sensitive fields in the FastAPI code before passing
to the database; decrypt on read. The column is still `text`/`varchar`, but
the value is ciphertext. No PostgreSQL extension is needed (use Python
`cryptography` library or similar).

**Pros:**

- No database extension dependency.
- Works against any database engine, not just PostgreSQL.
- Granular per-field.
- Key never enters the database engine.

**Cons:**

- Re-implements what pgcrypto already does well, but in a different
  language binding.
- Two codebases to keep key-compatible (encryption format must match what
  the database would have used, if pgcrypto is later added).
- The `pgp_sym_encrypt` output format is the de-facto interop standard;
  inventing a custom format reduces future flexibility.

**Effort:** Medium (similar to B but with more code to maintain).

**Applicability to this host:** **YES.** Used as a sub-pattern **inside**
Option B for the actual cipher call (the key is supplied by the
application, the cipher call is `pgp_sym_encrypt` via SQLAlchemy).

### Option D — Backup Encryption (encrypt at-rest for off-host backups)

**Description:** Encrypt `pg_dump` / `pg_basebackup` output before it leaves
the host. Standard pattern: `pg_dump | gpg --symmetric --cipher-algo AES256 >
backup.sql.gpg`.

**Pros:**

- Independent of the database engine. Works even if the live database is
  not encrypted.
- Protects the most-likely exfiltration vector (backup tapes, off-site
  backup drives).
- Standard tooling, well-understood threat model.

**Cons:**

- Does not protect the live database. If the host disk is stolen, the
  attacker reads the live database directly.
- Key management for backups is its own problem (rotation, retention).

**Effort:** Low (a `cron` or scheduled task + a documented restore procedure).

**Applicability to this host:** **YES.** Recommended as a **companion** to
the primary approach, not a replacement.

### Option E — Commercial TDE Add-on (e.g., pg_tde, Cybertec TDE)

**Description:** Third-party transparent data encryption extension for
PostgreSQL. Encrypts data files at the storage layer inside the database
engine, transparent to SQL.

**Pros:**

- True TDE — application sees plaintext, files on disk are encrypted.
- Covers everything (data, WAL, temp) without per-column decisions.

**Cons:**

- **Not available in standard PostgreSQL.** Requires building a custom
  PostgreSQL or paying for a commercial build.
- Windows builds are rare / unsupported.
- Adds an external dependency not on the constitutional surface.

**Effort:** High (build/test/deploy custom PostgreSQL).

**Applicability to this host:** **NO** (not realistic on Windows Home).

### Option F — Host Filesystem Encryption (VeraCrypt / LUKS)

**Description:** Create an encrypted volume (VeraCrypt) or use Linux LUKS,
place the PostgreSQL data directory inside it.

**Pros:**

- Full coverage of all data files.
- Cross-platform.

**Cons:**

- VeraCrypt on Windows Home: requires manual mount at boot, interacts
  poorly with Windows services (service start may happen before mount).
- LUKS is Linux-only; not applicable here.
- Operational complexity (key on USB, auto-mount scripts).

**Effort:** High (operational change to service start order).

**Applicability to this host:** **NOT RECOMMENDED** for a Windows Home
production database.

---

## 3. Decision Matrix

| Option | Viable? | Coverage | Effort | Constitutional impact |
|---|---|---|---|---|
| A. BitLocker | NO (Home) | Full disk | Low | None |
| B. pgcrypto column-level | **YES** | Sensitive columns | Medium | Schema unchanged |
| C. App-layer encryption | YES | Per-field | Medium | Schema unchanged |
| D. Backup encryption | YES (companion) | Backups only | Low | None |
| E. Commercial TDE | NO | Full | High | External dep |
| F. VeraCrypt / LUKS | NO (Windows svc) | Volume | High | Operational |

**Recommended primary:** **B + C (combined).** pgcrypto's `pgp_sym_*`
functions called from the application layer, with the key supplied by the
application per session. This is the pattern the PostgreSQL community
recommends for at-rest column encryption.

**Recommended companion:** **D (backup encryption).** Independent
protection for off-host backups.

---

## 4. Scope of "Sensitive Columns" in the Constitutional Schema

Reviewed the constitutional entities. Sensitive fields that warrant
encryption at rest:

| Table | Column | Reason |
|---|---|---|
| `audit_log` | `payload_json` | May contain actor IP, user agent, request details, occasional PII |
| `users` | (future) | PII (email, phone) — out of HD-PHASE8-004 scope; encryption helper available when needed |
| `session_token` | (future) | Hashed already, not encryption-target |

**For HD-PHASE8-004:** encrypt `audit_log.payload_json`. Other columns
remain as-is (no constitutional schema change). The encryption helper is
generic and reusable.

---

## 5. Key Management

- **Source:** `TSAI_ENCRYPTION_KEY` environment variable, set outside the
  codebase (deployment-time secret, not in `.env` committed to git).
- **Default in dev/test:** a known dev key with a clear `dev-` prefix so it
  cannot be mistaken for a production key.
- **Rotation:** a future gap (key rotation requires re-encrypting the
  column; out of HD-PHASE8-004 scope).
- **Storage:** never logged, never written to the audit log, never
  returned by any API.

---

## 6. Constitutional Constraints Respected

- Constitution v2.3: **unchanged** (no Article amended).
- Constitution v2.4: **unchanged** (no Article amended).
- Schema: **unchanged** (no columns added, dropped, or retyped; no
  triggers added or modified).
- Entities: 98 constitutional entities remain 98; 4 IMPL implementation
  entities (Phase 9) remain 4.
- Audit log immutability: **preserved** (HD-PHASE8-003 triggers unchanged;
  encryption is a confidentiality mechanism, not an integrity one).
- New TTAs: **zero** added. The cipher algorithm choice
  (`pgp_sym_encrypt` with AES-256) is the PostgreSQL community default and
  is recorded as **ASS-PHASE8-004-001** (cipher choice) and
  **ASS-PHASE8-004-002** (key-in-env-var delivery) in the Decision and
  Assumption Register.

---

## 7. Test Strategy

A new test file `tests/test_encryption_at_rest.py`:

1. Insert an audit record with a known sensitive payload (e.g.
   `{"ssn": "123-45-6789"}` or a marker string).
2. Read the raw `audit_log.payload_json` column from PostgreSQL via
   `psql`-equivalent direct SQL (bypassing the application).
3. Assert the raw value is **not** the plaintext marker.
4. Read the same record through the application (`audit.query(...)`).
5. Assert the application returns the **decrypted** payload containing the
   original marker.

This is the AC pattern: "raw bytes on disk ≠ plaintext; application
view = plaintext".

---

## 8. References

- PostgreSQL pgcrypto documentation:
  https://www.postgresql.org/docs/15/pgcrypto.html
- BitLocker requirements: Windows Pro/Enterprise/Education editions only.
- PostgreSQL community recommendation for at-rest column encryption:
  `pgp_sym_encrypt` with a key supplied by the application.
- NIST SP 800-111 — Guide to Storage Encryption Technologies for End User
  Devices.
- Constitution v2.3, Article XX (Audit and Evidence).
- Constitution v2.4, Article XX (additive — Proactive Discovery).
- HD-PHASE8-003 (production audit log initialisation; immutability
  triggers).
- HD-PHASE8-002 (PostgreSQL 15+ production migration).

---

**End of research note. Decision recorded in PRODUCTION_DEPLOYMENT.md §3.**
