# GitDock — Telegram UI/UX Specification

Status: authoritative v1 interaction contract, verified through P4.2 branch/commit implementation.

## 1. Experience goal

GitDock should feel like a compact professional GitHub control panel inside Telegram. The user should always know:

- where they are;
- which repository/ref/resource/account context is selected;
- whether an action is read-only, local-state changing, or will change GitHub;
- what will happen before a risky action is confirmed;
- how to return Home/Back without starting over.

Arabic is the primary UI language. Technical values such as repository names, branches, paths, workflow names, SHAs, GitHub logins, and commands remain as-is.

## 2. Rendering rules

- Prefer editing the current navigation message.
- Send a new message for durable notifications, documents/files, large logs, or important results worth preserving.
- Use centralized renderers rather than scattered raw formatting strings.
- Keep primary screens concise; secondary detail behind buttons.
- Default to at most two primary buttons per row.
- Destructive/sensitive actions are isolated from harmless navigation.
- Always show target/consequence before a write or sensitive local cleanup.
- Never render access/refresh/installation tokens, OAuth code/state, PKCE verifier, private key, client secret, or raw upstream auth material.
- Do not treat callback possession as authority.

## 3. Navigation contract

Contextual navigation:

```text
[🏠 الرئيسية] [⬅️ رجوع]
```

During active wizards:

```text
[❌ إلغاء] [⬅️ رجوع]
```

Home/Cancel/Back must remain predictable. Home cancels transient search/input state where continuing would surprise the user. Once a persisted sensitive confirmation/staging authority exists, leaving the flow must consume/revoke that authority where applicable so old Telegram buttons do not remain executable.

## 4. Home screen

Connected example:

```text
🐙 GitDock

إدارة GitHub من تلجرام

👤 GitHub: ahmed9461
📦 المستودعات: 24
🔔 التنبيهات: مفعلة
✅ الاتصال: سليم
```

Current connected keyboard contract:

```text
[📦 مستودعاتي]      [🔎 البحث في GitHub]
[👤 حساب GitHub]     [🔔 التنبيهات]
[📊 النشاط]          [➕ مستودع جديد]
[⚙️ الإعدادات]
[🔄 تحديث]
```

`👤 حساب GitHub` is real since P3.2. `➕ مستودع جديد` is real since P3.3. Other future Home entries may remain placeholders until their milestone.

Disconnected users may still use public GitHub search. Installed-repository administration/write flows require current server-side authorization and never become executable merely because an old callback exists.

## 5. GitHub account — P3.2

Authorized account screen shows linked GitHub login, durable-user-authorization state, installation count, and safe refresh/re-authorization actions. Local disconnect uses a persisted confirmation and explicitly states that it does not uninstall the GitHub App remotely.

Rules:

- activate/re-authorize starts the established OAuth + PKCE flow;
- refresh may rotate credentials server-side but UI never displays token material;
- local disconnect is isolated from remote App uninstall;
- stale/cancelled/reused disconnect confirmation removes nothing.

## 6. Repository list

Repository list is paginated/filterable and uses compact stable repository-ID callbacks. Long repository names do not travel as callback authority.

Example:

```text
📦 مستودعاتي

1) 🔒 GitDock
   Python • main

2) 🌐 WebHub
   Kotlin • main • ⭐ 14
```

## 7. Repository dashboard

Example:

```text
📦 GitDock
🔒 خاص

🌿 الفرع الافتراضي: main
📝 آخر Commit: docs: update architecture
⭐ 0   🍴 0
```

Keyboard contract:

```text
[📁 الملفات]       [📝 Commits]
[🌿 الفروع]        [⚙️ Actions]
[❗ Issues]         [🔀 Pull Requests]
[🏷️ Releases]      [📥 تشغيل/تنزيل]
[🔔 التنبيهات]     [⚙️ إعدادات المستودع]
[🏠 الرئيسية]      [⬅️ رجوع]
```

Verified real entries now are:

- `📁 الملفات` — P4.1;
- `📝 Commits` — P4.2;
- `🌿 الفروع` — P4.2;
- `⚙️ إعدادات المستودع` — P3.3.

Other entries remain placeholders until their roadmap milestone.

## 8. Create repository — P3.3

Flow: name → description/skip → visibility → explicit preview → persisted confirmation.

Creation does not occur before preview + confirmation. Edit/back/cancel consumes issued confirmation. Reused/expired/cancelled confirmation creates nothing.

## 9. Repository settings — P3.3

Settings include name, description, visibility, archive/unarchive, default branch, and isolated delete.

Rules:

- state-changing settings use persisted preview/confirmation;
- stale target/preconditions perform no write;
- delete requires exact current `owner/repo` plus Tier 3 confirmation;
- edit/back/cancel after preview consumes pending authority.

## 10. File browser — P4.1

Directory actions include entry buttons, pagination, create/upload, change ref, refresh, parent directory, Home/Back.

Rules:

- directory page size is 8;
- entry callbacks carry short browse session ID + numeric index, never repository path;
- stale/unknown browse session fails closed;
- ref input accepts validated branch/tag/SHA for read navigation;
- write flows require a real writable branch and current preconditions, not merely a readable detached ref.

File view behavior:

- UTF-8 text is previewed only within the 256 KiB preview ceiling and split into ~2800-character pages;
- binary content is described as binary;
- large/missing-inline-content uses safe metadata/fallback;
- bounded downloadable content may be sent as Telegram document;
- arbitrary browser/GitHub URLs never become a generic outbound fetch primitive.

## 11. P4.1 one-file write UX

Create/upload/edit/replace/delete all stage a reviewable plan before GitHub changes.

Text preview example:

```text
✏️ مراجعة التغيير

📦 owner/repo
🌿 feature/update-docs
📄 docs/README.md

+ 8 أسطر
- 3 أسطر

Commit:
Update docs/README.md via GitDock

لن يتم تغيير GitHub حتى التأكيد.
```

```text
[👁️ عرض Diff]
[✅ تطبيق التغيير]
[❌ إلغاء]
```

If branch/file state changed after preview, UI states clearly that nothing was overwritten/deleted and asks the user to refresh/review. If final remote outcome cannot be proven, UI says the result is uncertain and does not suggest blindly replaying the operation.

## 12. Branch list/search — P4.2

`🌿 الفروع` is a real repository-dashboard flow.

Screen contract:

```text
🌿 الفروع — owner/repo
الافتراضي: main

عدد الفروع: N

• main 🔒 — 1a2b3c4
• feature/x — 5d6e7f8
```

Current actions:

```text
[➕ فرع جديد] [🔎 بحث]
[🔀 مقارنة refs] [🔄 تحديث]
[⬅️ رجوع] [🏠 الرئيسية]
```

Rules:

- branch data comes from GitHub, not repository cache;
- optional search is case-insensitive filtering over the fetched branch names;
- technical branch names/SHA remain unchanged;
- no one-tap branch replacement/update exists;
- no normal v1 force-push/force-update/branch-delete UI exists.

## 13. Branch creation — P4.2

Flow:

1. user taps `➕ فرع جديد`;
2. enter target branch name;
3. enter explicit base branch/tag/SHA ref;
4. server resolves base to a concrete current commit SHA and verifies target is absent;
5. render review screen;
6. persist one-time Tier 1 confirmation;
7. confirm or cancel.

Review pattern:

```text
✅ مراجعة إنشاء الفرع

📦 owner/repo
🌿 الفرع الجديد: feature/new
الأساس: main
Base SHA: 0123456789abcdef...

لن يتم إنشاء أي ref في GitHub حتى التأكيد.
إذا تحرك base قبل التأكيد ستتوقف العملية كـ stale.
```

```text
[✅ إنشاء الفرع]
[❌ إلغاء]
```

Execution UX rules:

- target/base shown before write;
- missing base or existing target produces no write;
- confirm-time moved base produces explicit stale message and no write;
- target is checked again before write;
- successful create shows new branch + SHA;
- existing target is never silently replaced;
- uncertain result explicitly says it is unresolved and asks the user to refresh branch state; GitDock does not blindly retry create-ref;
- cancellation consumes the persisted authority.

## 14. Commits — P4.2

`📝 Commits` is a real repository-dashboard flow.

List screen:

```text
📝 آخر الـCommits — owner/repo
🌿 المرجع: main

المعروض: N
```

Commit buttons show short SHA + bounded first-line message. List pagination is 8 commit buttons per Telegram page; service fetch currently requests up to 30 recent commits.

Actions include changing the ref (`branch`, `tag`, or SHA), refresh/navigation, and opening commit detail.

Commit detail shows:

- full SHA;
- author name;
- authored UTC time;
- bounded first-line message;
- changed-file count;
- additions/deletions;
- parent count;
- canonical GitHub commit link.

Commit detail is re-fetched from GitHub using the selected SHA/ref.

## 15. Compare refs — P4.2

From branches screen, user selects `🔀 مقارنة refs`, then enters base and head refs.

Summary includes:

```text
🔀 مقارنة — owner/repo
base ← head

الحالة: ahead/behind/diverged/identical
Ahead: N
Behind: N
Commits: N
Files: N
```

For returned changed files, Telegram renders at most the first **10** rows with filename/status/additions/deletions, followed by a remaining-files indicator when needed. This keeps large comparisons bounded instead of dumping unbounded diff content into chat.

P4.2 compare is read-only; it does not merge, reset, force-update, or execute patch content.

## 16. P4.2 callback/context contract

- repository identity arrives through compact repository callback context established by P2.3;
- P4.2 internal callbacks are compact and versioned;
- commit-detail buttons carry page/index rather than full commit metadata;
- confirmation buttons carry opaque one-time confirmation token only;
- repository/base/target/precondition authority is resolved from server-side/FSM/persisted context;
- callback possession is never permission proof.

## 17. Permission/capability UX

- installed repository read paths require current GitHub authorization context;
- P4.1 ordinary file writes require repository-scoped `contents: write` and workflow files additionally require `workflows: write`;
- P4.2 branch creation obtains repository-scoped `contents: write` only after confirmation and precondition revalidation;
- permission denial uses safe user-facing copy and must not claim a change occurred;
- cache/callback presence is never presented as authority proof.

## 18. Clone/setup/run — P4.3 target

Future UI must separate fresh clone, update existing clone, setup, and run commands. It should show detected stack/evidence, ask for OS where needed, produce copyable sections, label inference confidence/source, never insert tokens, and never auto-execute README/script instructions.

## 19. ZIP/project synchronization — P8 target

Future batch flow remains: scan archive → compare → review added/modified/deleted/unchanged/warnings → persisted immutable plan → review branch + coherent commit by default → optional PR. Direct default-branch mass update, if ever enabled, is a separate Tier 2 exception and never the default.

## 20. Notification, Issues/PR, Actions/release future rules

- notifications use durable event/preferences context and do not leak private payloads;
- PR merge must show current target/head/check state before confirmation;
- Actions dispatch shows workflow/ref/inputs and requires confirmation;
- logs are bounded/paginated/document-backed;
- Actions secrets are never displayed.

## 21. Accessibility/readability

- Arabic explanatory copy should be simple and concise;
- technical identifiers remain unmodified;
- avoid overly dense Telegram messages;
- bound lists/diffs and paginate where useful;
- state uncertainty and stale conflicts explicitly rather than hiding them behind generic failure text.
