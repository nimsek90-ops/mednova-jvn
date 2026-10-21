# Login / preview diagnosis — 21 October 2026

Checkpoint before this repair: Git commit `1196fba`. The folder originally had no Git repository; a local repository and source checkpoint were created, excluding secrets, databases, uploads and .venv. No production data was changed.

| Priority | Confirmed cause / gap | Evidence | Repair / result |
|---|---|---|---|
| P1 | Middleware suppressed origin metadata for native browser forms | care/middleware.py set Referrer-Policy: no-referrer. Browser POST to /login/ and /language/ received CSRF 403 with Origin: null. | Use same-origin policy. Actual browser login and language POST now succeed with CSRF enabled; hostile/null-origin requests remain rejected in tests. |
| P2 | Root URL was the login view | mednova/urls.py mapped the empty path to sign_in. It was functioning as coded, not a public hospital homepage. | Added database-backed public home, department list, individual doctor profiles and booking entry links. |
| P2 | Public navigation was sparse | Unauthenticated base template offered brand/help/language; department information existed only inside directory/admin pages. | Added Home, Departments, Doctors & booking, Contact, Sign in and Register navigation. |
| P2 | Authentication discarded the requested workflow | roles redirected to login without next; sign_in always redirected to dashboard. | Preserve a validated same-origin destination. Restart/relogin returned the browser to its saved receipt. External next URLs are rejected. |
| P2 | Changing language discarded the current page | language always redirected to dashboard/login. | Carry validated current path and query in the language form. Browser Hindi/English changes retained the receipt page. |
| P2 | Clinical buttons did not reflect time/issued state | Future confirmed visits displayed prescription/completion actions; issued prescriptions still displayed Issue. Server correctly rejected invalid actions. | Show these actions only after start, and hide issuance once a prescription exists. Regression tested. |
| P2 | Pagination controls appeared twice | Prior templates included pagination and base.html included it again. | Keep the shared base inclusion only. |
| P2 | Permission denial produced an unstyled dead end | roles returned a bare HttpResponseForbidden. | Raise PermissionDenied for the existing branded 403 handler and home navigation. |
| P1 deployment | Private uploads used local filesystem | FileSystemStorage + checkout MEDIA_ROOT are incompatible with durable Vercel storage. | Configurable private S3 storage, authorized 60-second signed downloads, explicit Vercel upload cap and fail-closed configuration. Real bucket remains UNVERIFIED. |
| External blocker | Vercel project creation forbidden | Connected team listed no projects. POST /v11/projects returned 403 forbidden: You don't have permission to create the project. | No project/deployment was created. Owner must grant project-creation access or supply an accessible existing project. No authenticated CLI fallback was found. |

Dashboard routes and templates already existed for all five roles. The inspected server is Django served by Waitress on port 8000. Its isolated database has all migrations applied, and new sessions can read records created before restart. There is no evidence that missing dashboards or failed migrations caused the observed login-only screen in this local environment. Production MySQL was not configured or contacted.

The earlier report attributed Origin: null to a browser limitation. That conclusion was incorrect: changing the application's own response header resolved the failure in the same browser. Previous browser-blocker statements are superseded by this diagnosis and the new browser evidence.

Static-only Go Live cannot execute Django templates, sessions or ORM operations. Open the running Django/Waitress URL for local review. On Vercel select the Django framework and the folder containing manage.py; do not publish templates/ as a static website.

Route inventory: docs/verification/repair-route-map.json (48 routes). Server-side permissions remain the authority; the public site does not grant access to private workspaces.
