# PIN_TEMPLATES.md
> Step 7 of 8 — Static data file.
> Write the JSON below to: workspace/pinterest/pin_templates.json
> This file is loaded by pin_factory.py to drive pin graphic generation.
> Each template defines layout behavior, pin type, board target, and SEO properties.

---

## ACTION

Create this file at exactly this path:
`workspace/pinterest/pin_templates.json`

---

## pin_templates.json

```json
[
  {
    "id": "template_01",
    "name": "The Bold Statement",
    "pin_type": "quote",
    "background": "dark",
    "footer_accent": true,
    "headline_placeholder": "SNEAKER CULTURE",
    "keyword_categories": ["sneaker_culture"],
    "cta": "Save if you live by the lace code.",
    "board_env_key": "PINTEREST_BOARD_STREETWEAR",
    "why_it_works": "High-save rate — identity quotes get bookmarked and re-distributed by Pinterest algorithm"
  },
  {
    "id": "template_02",
    "name": "The Outfit Stack",
    "pin_type": "lifestyle",
    "background": "light",
    "footer_accent": false,
    "headline_placeholder": "OUTFIT IDEAS",
    "keyword_categories": ["outfits_style"],
    "cta": "Tag a friend who needs this fit.",
    "board_env_key": "PINTEREST_BOARD_OUTFIT_IDEAS",
    "why_it_works": "Multi-image outfit grids drive saves and profile visits from fashion-focused searchers"
  },
  {
    "id": "template_03",
    "name": "The Room Reveal",
    "pin_type": "lifestyle",
    "background": "light",
    "footer_accent": false,
    "headline_placeholder": "SNEAKER ROOM GOALS",
    "keyword_categories": ["room_decor"],
    "cta": "Get the wall art.",
    "board_env_key": "PINTEREST_BOARD_ROOM_DECOR",
    "why_it_works": "Room inspiration is Pinterest gold — drives massive saves from collectors planning their spaces"
  },
  {
    "id": "template_04",
    "name": "The Before After",
    "pin_type": "lifestyle",
    "background": "dark",
    "footer_accent": true,
    "headline_placeholder": "GLOW UP APPROVED",
    "keyword_categories": ["outfits_style", "sneaker_culture"],
    "cta": "Which look? Drop a comment.",
    "board_env_key": "PINTEREST_BOARD_OUTFIT_IDEAS",
    "why_it_works": "Contrast-based pins stop scroll immediately and drive engagement through comparison"
  },
  {
    "id": "template_05",
    "name": "The List Pin",
    "pin_type": "list",
    "background": "dark",
    "footer_accent": false,
    "headline_placeholder": "5 RULES EVERY SNEAKERHEAD LIVES BY",
    "keyword_categories": ["sneaker_culture"],
    "cta": "Save this for the culture.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "List pins are saved for reference and revisited — creates compounding long-term traffic"
  },
  {
    "id": "template_06",
    "name": "The Product Hero",
    "pin_type": "product",
    "background": "light",
    "footer_accent": false,
    "headline_placeholder": "NEW DROP",
    "keyword_categories": ["sneaker_culture", "gifts_shopping"],
    "cta": "Shop the drop.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Direct-response pin — works when keyword-targeted for buying intent in the sneaker niche"
  },
  {
    "id": "template_07",
    "name": "The Color Match",
    "pin_type": "product",
    "background": "light",
    "footer_accent": true,
    "headline_placeholder": "PERFECT COLOR MATCH",
    "keyword_categories": ["outfits_style"],
    "cta": "Which pair are you matching?",
    "board_env_key": "PINTEREST_BOARD_OUTFIT_IDEAS",
    "why_it_works": "Color-match content triggers saves from style-conscious sneakerheads planning outfits"
  },
  {
    "id": "template_08",
    "name": "The Countdown",
    "pin_type": "list",
    "background": "dark",
    "footer_accent": true,
    "headline_placeholder": "TOP SNEAKER GIFTS UNDER $40",
    "keyword_categories": ["gifts_shopping"],
    "cta": "Save before it sells out.",
    "board_env_key": "PINTEREST_BOARD_GIFTS",
    "why_it_works": "Gift list pins explode Nov–Dec — pin 60 days in advance for maximum holiday traffic"
  },
  {
    "id": "template_09",
    "name": "The Mockup Showcase",
    "pin_type": "product",
    "background": "dark",
    "footer_accent": false,
    "headline_placeholder": "SNEAKER MERCH",
    "keyword_categories": ["sneaker_culture", "outfits_style"],
    "cta": "Tag your sneaker crew.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Flat lay product shots perform 40% better than plain mockups on Pinterest"
  },
  {
    "id": "template_10",
    "name": "The Stat Drop",
    "pin_type": "quote",
    "background": "dark",
    "footer_accent": false,
    "headline_placeholder": "DID YOU KNOW?",
    "keyword_categories": ["sneaker_culture"],
    "cta": "Save if this is 100% you.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Surprising facts stop scroll and get shared in sneaker communities — free distribution"
  },
  {
    "id": "template_11",
    "name": "The Mood Board",
    "pin_type": "mood",
    "background": "light",
    "footer_accent": false,
    "headline_placeholder": "SNEAKERHEAD AESTHETIC",
    "keyword_categories": ["outfits_style", "sneaker_culture"],
    "cta": "Save for your next fit inspo.",
    "board_env_key": "PINTEREST_BOARD_OUTFIT_IDEAS",
    "why_it_works": "Mood boards drive profile follows — people save entire boards when they find a good one"
  },
  {
    "id": "template_12",
    "name": "The How To",
    "pin_type": "list",
    "background": "light",
    "footer_accent": false,
    "headline_placeholder": "HOW TO STYLE ANY SNEAKER IN 3 STEPS",
    "keyword_categories": ["outfits_style"],
    "cta": "Save this styling guide.",
    "board_env_key": "PINTEREST_BOARD_OUTFIT_IDEAS",
    "why_it_works": "Tutorial pins have 3x higher save rate — educational content wins on Pinterest"
  },
  {
    "id": "template_13",
    "name": "The Hype Comparison",
    "pin_type": "lifestyle",
    "background": "dark",
    "footer_accent": false,
    "headline_placeholder": "JORDAN VS DUNK — WHICH WINS?",
    "keyword_categories": ["sneaker_culture"],
    "cta": "Comment your pick.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Poll-style pins drive comments and engagement, boosting algorithm reach significantly"
  },
  {
    "id": "template_14",
    "name": "The Culture Story",
    "pin_type": "quote",
    "background": "dark",
    "footer_accent": true,
    "headline_placeholder": "BUILT FOR THE CULTURE",
    "keyword_categories": ["sneaker_culture"],
    "cta": "Follow for more culture content.",
    "board_env_key": "PINTEREST_BOARD_STREETWEAR",
    "why_it_works": "Brand story pins build trust and convert followers into long-term buyers"
  },
  {
    "id": "template_15",
    "name": "The Seasonal Capsule",
    "pin_type": "product",
    "background": "orange",
    "footer_accent": false,
    "headline_placeholder": "NEW DROP JUST LANDED",
    "keyword_categories": ["sneaker_culture", "gifts_shopping"],
    "cta": "Limited run — tap before it is gone.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "New drop plus urgency language spikes click-through to product page"
  },
  {
    "id": "template_16",
    "name": "The Review Card",
    "pin_type": "product",
    "background": "light",
    "footer_accent": false,
    "headline_placeholder": "5 STARS FROM THE CULTURE",
    "keyword_categories": ["sneaker_culture", "gifts_shopping"],
    "cta": "Join 1000 plus sneakerheads who grabbed theirs.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Reviews convert — bottom-of-funnel pin for buyers who are close to purchasing"
  },
  {
    "id": "template_17",
    "name": "The Macro Shot",
    "pin_type": "product",
    "background": "dark",
    "footer_accent": false,
    "headline_placeholder": "THE DETAILS HIT DIFFERENT",
    "keyword_categories": ["sneaker_culture"],
    "cta": "Shop the design.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Detail shots communicate quality and build premium brand perception without words"
  },
  {
    "id": "template_18",
    "name": "The Community Pin",
    "pin_type": "lifestyle",
    "background": "light",
    "footer_accent": false,
    "headline_placeholder": "REAL SNEAKERHEADS REAL FITS",
    "keyword_categories": ["sneaker_culture", "outfits_style"],
    "cta": "Tag us to get featured.",
    "board_env_key": "PINTEREST_BOARD_OUTFIT_IDEAS",
    "why_it_works": "Community pins feel authentic and drive follower loyalty and organic tagging"
  },
  {
    "id": "template_19",
    "name": "The Typography Art",
    "pin_type": "product",
    "background": "dark",
    "footer_accent": true,
    "headline_placeholder": "NEW DESIGN DROPPED",
    "keyword_categories": ["sneaker_culture"],
    "cta": "Grab yours before this design retires.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Clean design showcase builds desire — pins function as a digital lookbook for the brand"
  },
  {
    "id": "template_20",
    "name": "The Anniversary",
    "pin_type": "product",
    "background": "orange",
    "footer_accent": false,
    "headline_placeholder": "THANK YOU SNEAKERHEADS",
    "keyword_categories": ["sneaker_culture", "gifts_shopping"],
    "cta": "Exclusive discount for the culture this weekend only.",
    "board_env_key": "PINTEREST_BOARD_SNEAKER_CULTURE",
    "why_it_works": "Milestone pins create FOMO urgency and reward loyal followers with exclusive access"
  }
]
```
