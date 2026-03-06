# APP_PHASE.md
> Step 9 of 9 — Read after SCHEDULING.md.
> Covers the mobile app promotion system: phase switching, pin behavior per phase,
> the launch burst strategy, and the app_pin_templates.json data file to create.

---

## WHAT THIS FEATURE IS

A phase-controlled system for promoting a companion mobile app
(sneaker portfolio manager) through Pinterest, without creating a
separate account or harming the existing POD content strategy.

The system has two phases:

| Phase | Pinterest pins link to | CTA copy |
|---|---|---|
| `pre_launch` | App preview website + email capture page | "Join the waitlist" / "Be first to know" |
| `launched` | App Store / Google Play | "Download free" / "Track your collection" |

**The founder flips the switch once** — in the App Mode tab of the portal.
Everything else is automatic.

---

## HOW IT FITS INTO THE EXISTING PIN STRATEGY

App promo pins use `pin_type = app_promo`. They are governed by the same
80/20 content ratio rule as other pin types, counted as **inspiration** content
(not product pins) since they are not directly selling POD products.

App promo pins are distributed across the same boards as other sneaker culture content.
They do not need a separate Pinterest board. Sneaker collectors are the exact
audience for a sneaker portfolio app — there is no mismatch.

**Recommended frequency:** 1 app promo pin per day maximum during pre-launch.
After launch, increase to 2–3 per day for the first 30 days, then return to 1/day.
This is handled by the APP_LAUNCH_BURST_PINS burst release on launch day.

---

## THE LAUNCH BURST STRATEGY

### Why it matters

App Store ranking algorithms factor in download velocity in the first 72 hours.
Pinterest typically drives traffic 2–7 days after a pin is posted (as it indexes
and gets re-pinned). That means pins posted on launch day won't peak until day 3–7,
which is exactly when you need the download spike.

**Generate the burst before you launch. Release it the moment you flip to launched.**

### How to execute it

```
2 weeks before launch:
  → Go to App Mode tab in portal
  → Click "Generate 30 Burst Pins"
  → They sit as drafts — nothing is posted yet

Launch day:
  → Set APP_STORE_URL and PLAY_STORE_URL in workspace/.env
  → Restart the backend (so env vars reload)
  → Go to App Mode tab
  → Click "Activate Launch Mode"
  → All 30 draft app_promo pins are immediately released to the posting queue
  → Scheduler distributes them over the next 6 days (5/day standard + burst overflow)
  → Pinterest traffic peaks days 3–7 → download spike hits at peak App Store momentum
```

### Burst size recommendation

| Scenario | Burst size | Why |
|---|---|---|
| Soft launch, small audience | 20 pins | Conservative — 4 days at 5/day |
| Standard launch | 30 pins | 6 days of elevated posting |
| Full launch push | 50 pins | 10 days — combine with paid Pinterest ads |

Default is 30 (set via `APP_LAUNCH_BURST_PINS` in `.env`). Adjust before generating.

---

## APP_PIN_TEMPLATES.JSON

Create this file at: `workspace/pinterest/app_pin_templates.json`

These templates are separate from the main `pin_templates.json`.
They are app-specific and phase-aware — each template has both pre-launch and
launched variants of the title and CTA.

```json
[
  {
    "id": "app_template_01",
    "name": "The Collection Reveal",
    "headline": "YOUR SNEAKER COLLECTION DESERVES BETTER",
    "feature_text": "Track every pair. Know every value.",
    "description": "Stop using spreadsheets to manage your sneaker collection. There is a better way.",
    "cta_visual": "JOIN THE WAITLIST",
    "title_pre_launch": "Sneaker Collection App — Join the Waitlist | Coming Soon",
    "title_launched": "Track Your Sneaker Collection App | Download Free",
    "cta_pre_launch": "Be first to know when it drops. Link in bio.",
    "cta_launched": "Download free on App Store and Google Play.",
    "keyword_categories": ["sneaker_culture"],
    "background": "dark"
  },
  {
    "id": "app_template_02",
    "name": "The Value Tracker",
    "headline": "KNOW WHAT YOUR ROTATION IS WORTH",
    "feature_text": "Real-time resell value. Always updated.",
    "description": "Every sneakerhead needs to know what their collection is worth. Finally there is an app for that.",
    "cta_visual": "JOIN THE WAITLIST",
    "title_pre_launch": "Sneaker Value Tracker App — Coming Soon | Get Early Access",
    "title_launched": "Sneaker Resell Value Tracker App | Download Now",
    "cta_pre_launch": "Sign up for early access. Link in bio.",
    "cta_launched": "Track your rotation value. Free download.",
    "keyword_categories": ["sneaker_culture"],
    "background": "dark"
  },
  {
    "id": "app_template_03",
    "name": "The Catalog Shot",
    "headline": "CATALOG YOUR KICKS",
    "feature_text": "Photo. Details. Value. All in one place.",
    "description": "Built for collectors who take their rotation seriously.",
    "cta_visual": "COMING SOON",
    "title_pre_launch": "Sneaker Catalog App for Collectors | Waitlist Now Open",
    "title_launched": "Best Sneaker Catalog App | Download Free Today",
    "cta_pre_launch": "Save your spot on the waitlist. Link in bio.",
    "cta_launched": "The sneaker app collectors have been waiting for.",
    "keyword_categories": ["sneaker_culture", "outfits_style"],
    "background": "dark"
  },
  {
    "id": "app_template_04",
    "name": "The Community Tease",
    "headline": "BUILT FOR THE CULTURE",
    "feature_text": "Sneakerhead portfolio manager — coming soon.",
    "description": "A sneaker portfolio app designed by collectors, for collectors. Built around the culture.",
    "cta_visual": "GET EARLY ACCESS",
    "title_pre_launch": "Sneakerhead App Built for Collectors | Early Access Open",
    "title_launched": "Sneakerhead Portfolio Manager App | Free Download",
    "cta_pre_launch": "Join the waitlist. Be part of the culture.",
    "cta_launched": "Download. Track. Flex. Free on iOS and Android.",
    "keyword_categories": ["sneaker_culture"],
    "background": "dark"
  },
  {
    "id": "app_template_05",
    "name": "The POD Crossover",
    "headline": "APP + MERCH. COLLECTOR ECOSYSTEM.",
    "feature_text": "App members get exclusive POD discounts.",
    "description": "Track your collection in the app. Wear the culture with our merch. Built together.",
    "cta_visual": "JOIN THE WAITLIST",
    "title_pre_launch": "Sneaker App with Exclusive Merch Discounts | Coming Soon",
    "title_launched": "Sneaker Portfolio App | Members Get Merch Discounts",
    "cta_pre_launch": "Sign up — app members get exclusive merch deals.",
    "cta_launched": "Download the app. Unlock collector discounts on our store.",
    "keyword_categories": ["sneaker_culture", "gifts_shopping"],
    "background": "orange"
  }
]
```

> These 5 templates cycle through when generating the burst.
> 30 burst pins = 6 passes through the 5 templates with keyword variation each time.
> Add more templates here to increase visual variety in the burst.

---

## PHASE BEHAVIOR SUMMARY FOR THE LLM

When implementing `app_phase.py` and `pin_factory.py`, these are the rules:

1. `get_app_link()` returns a different URL based on `get_current_phase()`
2. `get_app_cta()` returns the pre or post launch CTA string from the template
3. Pin `title` and `description` are built from the phase-appropriate template fields
4. All app promo pins are created with `status = draft` — the scheduler never auto-posts them until `_release_launch_burst()` is called
5. `_release_launch_burst()` is called exactly once, triggered by `set_phase(AppPhase.LAUNCHED)`
6. After launch, new app promo pins generated via Pin Factory use the launched copy automatically — no manual step needed

---

## WHAT STAYS MANUAL (by design)

| Step | Why |
|---|---|
| Setting APP_STORE_URL / PLAY_STORE_URL in .env | Security — store URLs are not editable in the portal |
| Generating the burst pin set | Intentional — founder controls timing (ideally 1–2 weeks before launch) |
| Flipping to launched mode | Single deliberate action — has irreversible side effects (burst release) |
