# Carbon_Footprint_est — change log

## Current update
- Retained the original green visual identity and React/Flask architecture.
- Kept the profile and daily questionnaire separate; added optional car occupancy to the personal profile.
- Applied the CEA FY 2023-24 all-India grid electricity CO2 factor (0.727 kg CO2/kWh) and documented its year and scope. Other categories remain illustrative and are labelled accordingly.
- Corrected India-local date handling for daily check-ins and insights, stricter numeric validation, profile validation and password minimum length.
- Added persistent community challenges with qualifying check-in progress and one-time XP awards.
- Added QR generation for challenge links, city-based map search links, and an Eco Coach with optional OpenAI Responses API support plus a local rule-based fallback.
- Added optional daily reminder and weekly email summary preferences with scheduler-ready SMTP scripts.
- Fixed mission state to load from saved activity and corrected the cookie settings page so it no longer suggests analytics are being tracked.
- Added responsive community layouts, setup and methodology documentation.

- Improved tab navigation with synchronized hash/back-forward handling and a short flying-bee transition between pages.
- Added a page-level React error boundary so a rendering exception shows a recovery screen instead of leaving the content area blank.
- Added cleanup for the navigation animation timer and a reduced-motion fallback.

## Known limitations
- Transport, food, shopping, waste and cooking factors are illustrative, not fully India-specific or independently validated.
- AI Eco Coach responses require a valid server-side OpenAI API key and may incur API usage charges; without a key the app uses the local rule-based fallback.
- Map results are live map searches and are not curated or verified by the project.
- Weekly digests require SMTP and an external weekly scheduler. Email verification/password reset also require SMTP.
- Challenge participation is self-reported and inferred from daily check-in answers; it is not independently verified.
- Authentication remains localStorage bearer-token based and in-process rate limiting is not suitable as the sole production defence.
- A full frontend dependency install/build and live Flask integration test could not be run in this environment because dependencies were unavailable / installation timed out. Run the verification steps in README on the target machine before deployment.
