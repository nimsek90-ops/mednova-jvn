# MedNova healthcare design update

The supplied references show three distinct compositions: a spacious booking workspace with date/slot selection, a compact clinical operations dashboard, and a patient workspace with contextual summaries. The repeated booking screenshots are one reference, not separate screens. This update adapts their hierarchy, white cards, rounded controls, summary panels and explicit selection states to the requested medical-blue (#155EEF), cyan-accent and neutral palette. It does not reproduce reference fixture names, old dates, invented statistics or unsupported home visits.

`static/css/healthcare.css` is the shared theme after existing structural CSS. It centralizes tokens and styles existing navigation, dashboard, directory, booking, forms, tables, records, payment and status components across all five roles. Existing layouts and template actions remain in place. The shared vector brand mark replaces the heavyweight raster mark in navigation/login; the source hospital SVG uses the same palette. Chat and review focus styles are aligned. One duplicated role-link CSS block was removed.

Template changes retain CSRF, form field names, upload encoding, URLs, role checks and database-backed content. Dashboard regions have explicit accessible labels. Payment status is distinguished visually and the staff-verification warning is emphasized. Backend payment/video eligibility and review rules are unchanged.

Local verification: 229 MySQL Django tests, 2 frontend build tests, frontend production routing build, JS syntax check, pip consistency, migration drift/pending checks and Django checks pass. The deployment settings check used production security flags with isolated local settings, not live provider credentials. Six-role rendered crawl: 261 checks, 0 failures. HTTP acceptance: 8 groups; payment: 8 groups; clinical/reviews: 7 groups, all pass. Browser log inspection found no warnings/errors on the inspected local tab.

Browser overflow checks: all five dashboards and public home/directory/login at 390, 768, 1024 and 1440 requested viewport widths (32 combinations), plus booking selection at those four widths. All measured document scroll widths equal client widths. Mobile admin navigation and user management were exercised; booking radio selection updates the displayed summary. This is representative coverage, not a claim to have manually inspected every page at every size.

Measured theme contrast: white/blue 5.41:1, muted/white 6.23:1, heading/white 17.85:1, selected text/tint 6.58:1. These pairs pass WCAG AA normal-text contrast; this is not a full accessibility certification. Existing focus, labels, keyboard navigation and reduced-motion support are retained.

External SMTP inbox delivery, fresh cloud writes, real provider capture/refund, two-device WebRTC/TURN and PDF antivirus remain unverified in this update. No production record or secret changes are needed. Docker is unavailable locally; the configured provider container build must be checked during deployment. No lint or type-check command is configured. No new dependencies or migrations are introduced.

Evidence is in `verification/redesign-20261024-*`. Deployment evidence will be recorded separately after the source commit reaches the live service.
