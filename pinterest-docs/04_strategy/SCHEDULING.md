# SCHEDULING.md
> Step 8 of 8 — Strategy and operational rules for the scheduler.
> No code to write here. This is the business logic the scheduler enforces.
> Read this alongside BACKEND.md when implementing scheduler.py.

---

## HOW THE SCHEDULER WORKS IN THIS PROJECT

APScheduler runs inside the existing FastAPI process (no separate worker needed).
It is started in `main.py` at app startup alongside the existing application.
It does two things on a cron schedule:

1. **Post pins** — fires at each configured post time, picks the next pending job
2. **Sync analytics** — fires at 6 AM daily, pulls metrics for all posted pins

The scheduler reads its settings from environment variables in `workspace/.env`.
The portal's Schedule view shows the queue and lets the founder post manually if needed.

---

## DEFAULT POSTING SCHEDULE

```
Pins per day:  5
Post times:    08:00, 11:00, 14:00, 18:00, 21:00
Timezone:      America/New_York
```

Pinterest's algorithm rewards consistency above posting volume.
5 pins per day every day outperforms 35 pins dumped once a week.
Do not exceed 10 pins per day from a single account.

---

## CONTENT RATIO RULE (80/20)

The scheduler enforces this automatically when building the queue:

- 80% inspiration pins: `pin_type` in (`lifestyle`, `quote`, `list`, `mood`)
- 20% product pins: `pin_type` in (`product`)

Implementation: `_next_available_slot()` checks the last 10 posted pins.
If product pins make up more than 20% of recent posts, the next slot is
reserved for an inspiration pin type.

---

## HOLIDAY SCALING CALENDAR

For each holiday window below, increase `PINTEREST_PINS_PER_DAY` to the
recommended value and begin that many days before the event.
The Schedule page in the portal surfaces these as alert banners.

| Holiday | Date | Begin Pinning | Recommended pins/day | Content Focus |
|---|---|---|---|---|
| Halloween | Oct 31 | Sep 1 (60 days out) | 7 | Sneaker costume outfits, spooky streetwear |
| Black Friday | Nov 29 | Oct 15 (45 days out) | 10 | Gift guides, sneakerhead approved lists |
| Cyber Monday | Dec 2 | Nov 1 (31 days out) | 10 | Urgency pins, countdown language |
| Christmas | Dec 25 | Nov 1 (54 days out) | 10 | Gifts for sneakerheads, collector presents |
| New Year | Jan 1 | Dec 1 (31 days out) | 7 | New rotation, sneaker goals, fresh start |
| Valentine's Day | Feb 14 | Jan 1 (44 days out) | 7 | Gifts for him/her sneakerhead |
| NBA All-Star Weekend | Feb (varies) | Jan 15 | 7 | Basketball sneaker culture, Jordan heritage |
| Air Max Day | Mar 26 | Mar 1 (25 days out) | 8 | Nike culture celebration, air max aesthetic |
| Back to School | Aug (varies) | Jul 1 | 7 | Outfit ideas for school, fresh kicks content |
| Jordan Brand events | varies | 2 weeks before | 8 | Collector culture, heritage drops |

Store this calendar in `workspace/pinterest/holidays.json` (optional — the Schedule
page can hardcode it or load it dynamically).

---

## THE 300 PINS/MONTH TARGET

How to hit it with this system:

```
Week 1:  10 designs × 10 templates each   = 100 pins generated, 35 scheduled
Week 2:  5 new + 5 refresh designs        = 75 pins generated, 35 scheduled
Week 3:  5 new designs                    = 50 pins generated, 35 scheduled
Week 4:  Scale top 3 performers (×5 each) = 15 pins generated, 35 scheduled (+ holdover)
─────────────────────────────────────────────────────────────────────────────
Monthly total scheduled:                    140 pins posted (at 5/day × 28 days)
Monthly total generated:                    240 pins in the system
```

At 5 pins/day the scheduler posts ~150 pins/month automatically.
The surplus stays in draft status as buffer — useful when scaling up or during holidays.

---

## SCALING RULE (from Analytics)

When `PinAnalytics.jsx` shows a pin in the Scaling Candidates section
(CTR >= 3× account average), the correct action is:

1. Go to Pin Factory
2. Select the same design
3. Generate pins using only the templates that match the successful pin's type
4. Schedule immediately — these go to the front of the queue
5. Track for 7 days — if CTR holds, generate 5 more variations

This is the growth loop that compounds Pinterest traffic over months 6–12.

---

## PINTEREST OAUTH — ONE-TIME SETUP

Pinterest requires OAuth 2.0. The access token does not auto-generate.
This is a one-time manual step before the scheduler can post anything.

Steps:
1. Go to https://developers.pinterest.com — create an app
2. Set redirect URI to `http://localhost:8000/auth/pinterest/callback`
3. Get your App ID and App Secret — add to `workspace/.env`
4. Visit the Pinterest OAuth URL manually in browser:
   ```
   https://www.pinterest.com/oauth/?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=boards:read,pins:read,pins:write,user_accounts:read
   ```
5. After approving, Pinterest redirects with `?code=...`
6. Exchange that code for tokens using the Pinterest token endpoint
7. Store `access_token` and `refresh_token` in `workspace/.env`

The `pinterest_client.py` `refresh_access_token()` function handles token renewal
automatically — access tokens expire every 30 days, refresh tokens last 1 year.

---

## WHAT THE PORTAL DOES NOT AUTOMATE (manual steps)

These remain manual, by design:

| Step | Why it stays manual |
|---|---|
| Design approval | Already handled by existing workspace/approval flow |
| Printify listing | Already handled by existing printify_upload.py |
| Pinterest OAuth setup | One-time, security-sensitive |
| Pinterest board creation | Done once in Pinterest UI — board IDs go into .env |
| Holiday schedule boost | Founder decides when to scale — portal surfaces the suggestion |
