# CompDataVault inbound email — Cloudflare Worker

Bypasses SendGrid/Postmark entirely for the inbound side. Cloudflare Email
Routing already terminates mail for compdatavault.com (it's what forwards
sebastian@ to your Gmail today) — this adds **one exact-match rule** for
`deals@compdatavault.com` that sends mail to a Worker, which relays it to
your FastAPI backend.

## The address scheme (this changed from an earlier draft)

Every broker forwards flyers to the exact same address:
**deals@compdatavault.com**. No per-user code, no "+slug", nothing to look
up or remember beyond one email address.

Whose vault a flyer lands in is decided by matching the **sender's** email
(the From address on the forwarded message) against that broker's account
email in the database — not anything about the recipient address. This
means:

- A broker must forward *from* the same email they signed up with. If they
  routinely forward from a different address (e.g. signed up personal,
  forwards from a brokerage inbox), it'll 404 until either they sign up
  with that address or you add support for multiple authorized sender
  addresses per account (straightforward addition later, not built yet).
- Because there's exactly one recipient address and no wildcard/catch-all
  needed, Cloudflare's routing rule can be a normal exact-match rule
  instead of a domain-wide catch-all — tighter, and it won't fire the
  Worker for spam or typos hitting random addresses at your domain.
- The backend does a lightweight SPF/DKIM sanity check (an
  `Authentication-Results` header, if present, checked for an explicit
  `fail`) before trusting the From address, since matching purely on an
  unauthenticated header is spoofable in principle. Absence of the header
  isn't treated as failure — only an explicit fail is — since Cloudflare
  doesn't guarantee it's always present.

## Files here

- `src/index.js` — the Worker. Confirms the recipient is exactly
  `deals@compdatavault.com`, reads the raw MIME email, and POSTs it to your
  backend as multipart/form-data. Rejects (bounces) only on transient
  failures so senders' mail servers retry; a 4xx from the backend (bad
  auth, unmatched sender, no attachment) is accepted-and-dropped rather
  than bounced, since retrying wouldn't fix any of those.
- `wrangler.jsonc` — Worker config. Set `INGEST_SHARED_SECRET` as a
  Wrangler secret (not in this file).
- `ingest_email_backend.patch` — a `git apply`-able diff against
  `dealarchive/api.py`, `dealarchive/config.py`, `dealarchive/models.py`,
  and a new Alembic migration, that replaces the old Postmark-shaped
  `/ingest/email` with one that accepts what this Worker sends and matches
  by sender email instead of a per-user routing code.

## What changed in the backend, and why

I pulled the live repo before writing this and found the existing
`/ingest/email` was still coded for **Postmark's** webhook JSON shape
(`ToFull[0].MailboxHash`, base64 `Attachments`) — not SendGrid, despite the
project notes saying it had been reverted to SendGrid's format — and it
depended on a `User.forwarding_slug` column (a 32-character random UUID
hex) to build each broker's unique forwarding address. That's what made
the earlier "deals+<slug>@compdatavault.com" addresses so unwieldy. Moving
inbound onto your own domain via this Worker was the right moment to drop
that scheme entirely rather than just shortening it.

The patch:
- Rewrites `/ingest/email` to accept multipart/form-data
  (`from_address`, `to_address`, `subject`, `raw_email` file) instead of a
  Postmark-shaped JSON body, and parses the raw `.eml` itself with
  Python's stdlib `email` module (`python-multipart` is already a
  dependency for file uploads — no new packages needed).
- Matches the sender's email (parsed out of the From header) against
  `User.email`, case-insensitively, instead of a forwarding slug.
- Does the SPF/DKIM sanity check described above before trusting the
  sender match.
- Double-checks the recipient address server-side too, in case the
  Cloudflare rule is ever loosened to a catch-all by mistake.
- Swaps the `?secret=` query-param auth for an `X-Ingest-Secret` header
  (matches what the Worker sends), still checked against the same
  `INBOUND_WEBHOOK_SECRET` setting you already have.
- Drops `User.forwarding_slug` from the model and adds
  `alembic/versions/0002_drop_forwarding_slug.py` to drop the column. I
  checked: only one prior migration exists (`0001_initial_schema.py`), so
  this is very likely safe pre-launch, but glance at your Neon `users`
  table row count before running it just in case real accounts exist.
- `/me` now returns the same static `deals@compdatavault.com` for every
  user — the Settings page needs no changes, since it already just
  displays whatever string `/me` returns.

I verified this patch applies cleanly to a fresh clone of your repo
(`git apply --check` passed).

## Confirmation replies

The Worker now replies to the sender after processing, using Cloudflare's
built-in `message.reply()` (no third-party outbound provider needed — this
rides the same Email Routing setup already handling inbound):

- **Success**: one line per attachment ("Sale comp added to your vault" /
  "...needs review" / "Couldn't parse this one: <error>"), plus a direct
  link to each new comp (`{FRONTEND_URL}/comps?type=sale&id=...`).
- **Sender not matched / no attachment (400 / 404)**: a plain-language
  explanation, including a nudge to forward from the account's signup
  email if that's the issue.
- **Bad shared secret (401) / failed SPF-DKIM (403)**: silent, logged
  only. Neither is something the sender did that they can fix, and for a
  possible spoofing attempt (403), confirming back to whoever sent it that
  their spoof was detected is just handing them free reconnaissance.

One real constraint worth knowing: `message.reply()` throws if the
incoming email doesn't have a **valid DMARC result**. Most real mail
providers (Gmail, Outlook/M365, most corporate mail) publish DMARC and
this passes fine, but it's not guaranteed for every sender's setup. When
it fails, the Worker logs the error and moves on -- the flyer is still
ingested either way, the sender just doesn't get the confirmation email
for that one message. Worth watching Worker logs after launch to see how
often this actually happens in practice; if it turns out to be common,
switching from reply() to Cloudflare's separate Email Service send API
(no DMARC requirement, more setup) would be the fix.

`mimetext` is now a runtime dependency (used to build the MIME reply) --
already added to `package.json`, `npm install` picks it up.

## Deploy steps

1. **Apply the backend patch** (from the repo root):
   ```
   git checkout -b cloudflare-inbound-email
   git apply ingest_email_backend.patch
   ```
   Review the diff, run `alembic upgrade head` against your Neon DB, then
   commit and push to Render as usual.

2. **Set backend env vars on Render**: `INBOUND_BASE_ADDRESS=deals@compdatavault.com`
   and pick a strong random value for `INBOUND_WEBHOOK_SECRET` (e.g.
   `openssl rand -hex 32`).

3. **Install wrangler and deploy the Worker** (from this directory):
   ```
   npm install
   npx wrangler login
   npx wrangler secret put INGEST_SHARED_SECRET   # paste the SAME value as INBOUND_WEBHOOK_SECRET above
   npx wrangler deploy
   ```

4. **Wire it up in the Cloudflare dashboard** (compdatavault.com zone →
   Email → Email Routing):
   - Confirm your existing `sebastian@` → forward-to-Gmail rule is still
     there, untouched.
   - Add a custom address rule for `deals@compdatavault.com` with the
     action "Send to a Worker," pointing at `compdatavault-inbound-email`.
     (No catch-all needed with this scheme.)

5. **Test end-to-end**: from the email address a test account actually
   signed up with, send a flyer PDF to `deals@compdatavault.com`. Check
   Render logs for the `/ingest/email` request, and confirm a `Flyer` row
   shows up for that user.

## A note on scale

Cloudflare Email Routing has no documented cap on inbound message rate —
its limits are 25 MiB per message and 200 routing rules per domain (this
setup uses exactly one). Worker invocations count against the
100k-requests/day free tier, which is roughly 65x more than a genuinely
successful outcome for this product would need before you'd have to pay
Cloudflare's $5/mo Workers Paid plan.
