# GitDock — Telegram UI/UX Specification

Status: authoritative v1 interaction contract, updated through P4.1 file-browser implementation verification

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
- Always show target/consequence before write or sensitive local cleanup.
- Use consistent icons from `docs/CONSTANTS.md`.
- Never render access/refresh/installation tokens, OAuth code/state, PKCE verifier, private key, client secret, raw upstream auth body, or staged file body as hidden callback authority.

## 3. Navigation contract

Contextual navigation:

```text
[🏠 الرئيسية] [⬅️ رجوع]
```

During active wizards:

```text
[❌ إلغاء] [⬅️ رجوع]
```

Home/Cancel/Back must remain predictable. Home cancels transient search/input state and invalidates pending local-disconnect authority where applicable. Once a persisted write confirmation/staging authority exists, edit/back/cancel must revoke or consume that authority before leaving the flow so an old Telegram confirmation cannot remain executable.

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

`👤 حساب GitHub` is real since P3.2. `➕ مستودع جديد` is real since P3.3. Repository-dashboard `📁 الملفات` is real in P4.1. Other entries remain placeholders until their roadmap milestone.

Disconnected example:

```text
🐙 GitDock

لم يتم ربط حساب GitHub بعد.
اربط الحساب لعرض مستودعاتك وإدارتها بأمان.
```

```text
[🔎 البحث في GitHub]
[🔗 ربط GitHub]
[ℹ️ كيف يعمل الربط؟]
[🔄 تحديث]
```

Public search remains available independently of connection state. Repository creation/file writes require current server-side authorization and do not become executable merely because a callback exists.

## 5. GitHub account screen — P3.2 verified

The account screen separates durable GitHub **user authorization** from local GitHub App **installation bindings**.

Authorized example:

```text
👤 حساب GitHub

GitHub: octocat
✅ صلاحية المستخدم: مفعلة
🏢 التثبيتات المرتبطة: 2
🔄 التجديد: متاح

تُحفظ رموز التفويض مشفرة داخل GitDock ولا يتم عرضها هنا.
```

```text
[🔐 إعادة التفويض]
[🔄 تحديث]
[🔌 قطع الربط المحلي]
[🏠 الرئيسية]
```

Legacy installation-only example:

```text
👤 حساب GitHub

⚠️ صلاحية المستخدم الدائمة غير مفعلة
🏢 التثبيتات المرتبطة: 1

يمكن تفعيل صلاحية المستخدم دون إعادة تثبيت GitHub App.
```

```text
[🔐 تفعيل صلاحية المستخدم]
[🔌 قطع الربط المحلي]
[🏠 الرئيسية]
```

Rules:

- activate/re-authorize starts standalone OAuth + PKCE through the established secure flow;
- it does not reinstall the GitHub App;
- refresh may perform expiry-aware token rotation server-side, but UI never displays token material;
- local disconnect is isolated and uses persisted one-time confirmation;
- UI states clearly that local disconnect does not uninstall the GitHub App remotely.

## 6. Repository list

Example:

```text
📦 مستودعاتي

1) 🔒 GitDock
   Python • main • تم التحديث قبل 8 دقائق

2) 🌐 WebHub
   Kotlin • main • ⭐ 14

3) 🔒 Wasl
   TypeScript • main

الصفحة 1 من 3
```

```text
[1 • GitDock] [2 • WebHub]
[3 • Wasl]    [4 • ...]
[◀️ السابق]   [التالي ▶️]
[🎛 تصفية]    [🔄 تحديث]
[🏠 الرئيسية]
```

Do not place full long repository names in callback payloads; use compact stable IDs.

## 7. Repository dashboard

Example:

```text
📦 GitDock
🔒 خاص

🌿 الفرع الافتراضي: main
📝 آخر Commit: docs: define system architecture
⭐ 0   🍴 0
❗ Issues: 0   🔀 PRs: 0
⚙️ Actions: لا توجد عمليات بعد

آخر تحديث: قبل 3 دقائق
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

`📁 الملفات` is real in P4.1. `⚙️ إعدادات المستودع` is real in P3.3. Unimplemented entries remain placeholders until their milestone.

## 8. Create repository wizard — P3.3 verified

Flow: repository name → description/skip → visibility → preview → persisted confirmation.

Preview pattern:

```text
✅ مراجعة الإنشاء

الاسم: MyProject
المالك: ahmed9461
النوع: 🔒 خاص
الوصف: ...

سيتم إنشاء المستودع في حساب GitHub المرتبط.
```

```text
[✅ إنشاء المستودع]
[✏️ تعديل البيانات]
[❌ إلغاء]
```

Rules:

- creation never occurs before preview + persisted Tier 1 confirmation;
- personal create uses current durable GitHub user authorization;
- organization create is supported at service/gateway level when explicitly requested/authorized; current Telegram wizard defaults to linked personal account;
- edit/cancel consumes issued confirmation;
- reused/expired/cancelled confirmation creates nothing.

## 9. Repository settings — P3.3 verified

```text
⚙️ إعدادات GitDock

الاسم: GitDock
الظهور: 🔒 خاص
الفرع الافتراضي: main
الحالة: نشط
```

```text
[✏️ الاسم]       [📝 الوصف]
[🌐 جعله عامًا / 🔒 جعله خاصًا] [📦 أرشفة / 📤 إلغاء الأرشفة]
[🌿 الفرع الافتراضي]
[🗑 حذف المستودع]
[🏠 الرئيسية] [⬅️ رجوع]
```

Rules:

- delete is isolated;
- name/description/default branch collect input then preview;
- visibility/archive/unarchive use persisted Tier 2 preview/confirmation, not one-tap execution;
- Back/Cancel after preview consumes pending confirmation;
- stale target/preconditions produce no write;
- deletion requires exact current `owner/repo` then separate persisted Tier 3 confirmation.

## 10. File browser — P4.1 verified implementation

Directory screen:

```text
📁 GitDock / docs
🌿 main

📁 api
📁 assets
📄 ARCHITECTURE.md
📄 ROADMAP.md
📄 SECURITY_MODEL.md

الصفحة 1 من 2
```

Current directory actions include entry buttons plus:

```text
[◀️ السابق] [التالي ▶️]
[➕ ملف] [⬆️ رفع/استبدال]
[🌿 تغيير الفرع] [🔄 تحديث]
[⬅️ مجلد أعلى]
[🏠 الرئيسية] [⬅️ رجوع]
```

Rules:

- directory page size is 8 entries;
- entry callbacks contain short browse session ID + numeric index, never the repository path itself;
- stale/unknown browse session fails closed;
- parent navigation operates on validated server-side path context;
- ref input accepts a validated branch/Tag/SHA for read navigation;
- write flows require a real writable branch and current preconditions, not merely a readable detached ref.

### P4.1 file view

```text
📄 docs/ARCHITECTURE.md
🌿 main
📦 18.4 KB

<text preview>

الجزء 1 من 4
```

Current actions:

```text
[◀️] [▶️]
[✏️ تعديل] [♻️ استبدال]
[🌿 تغيير الفرع] [📥 تنزيل]
[🗑 حذف]
[🏠 الرئيسية] [⬅️ رجوع]
```

Behavior:

- UTF-8 text is previewed only within the 256 KiB preview ceiling and split into 2800-character pages;
- binary content is described as binary, not rendered as fake text;
- large content uses a clear metadata/fallback message;
- missing inline content uses a safe fallback rather than guessing;
- bounded downloadable content is sent as a Telegram document; unsupported/too-large content directs the user to GitHub rather than attempting an unbounded fetch;
- UI never turns GitHub/browser URLs into arbitrary outbound fetch targets.

## 11. P4.1 create/upload/edit/replace/delete flows

### Create text file

1. `➕ ملف` from current directory.
2. Ask for **one filename segment only** (for example `README.md`); nested paths are rejected in this input step.
3. Ask for full text content.
4. Server stages the intended create and returns Preview.
5. User confirms or cancels.

### Upload / create-or-replace

`⬆️ رفع/استبدال` asks for a Telegram document. The server combines the validated current directory with the document filename and checks whether that path currently exists at the selected ref. Existing target becomes an update/replace plan; missing target becomes create. The UI does not choose create/update solely from filename assumptions.

### Edit / replace existing file

- `✏️ تعديل` asks for full replacement text.
- `♻️ استبدال` asks for a replacement Telegram document.
- Both stage a reviewable update against current GitHub preconditions before any write.

### Delete

`🗑 حذف` stages a delete plan for the currently selected file and shows the same explicit write-review/confirmation pattern. It never deletes directly from the file-view tap.

## 12. P4.1 single-file write confirmation

Text-write preview pattern:

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

Binary/non-text plan explicitly says a textual Diff is unavailable rather than inventing one.

Durable behavior:

- preview creates server-side staged intent + persisted confirmation; callback token is transport only;
- staged intent is tied to repository, branch, path, branch head/current file SHA, desired content digest, operation, user, expiry, and nonce/version;
- a newer staging for the same user/repository/branch/path invalidates the older staged authority;
- cancel consumes the pending authority and clears staged content;
- staged content is temporary and can survive restart for at most 15 minutes; it is cleared on consume/cancel/supersede/expiry/prune;
- audit contains no file body.

If file/branch state changed:

```text
⚠️ تغير الملف أو الفرع في GitHub بعد فتحه.
لم يتم استبدال أو حذف أي شيء.
حدّث الملف وراجع التغييرات من جديد.
```

If the final remote result cannot be proven after an uncertain GitHub error:

```text
⚠️ نتيجة العملية غير محسومة.

تعذر إثبات نجاح أو فشل التغيير بعد انقطاع/خطأ GitHub.
لا تعِد تنفيذ العملية بشكل أعمى؛ افتح الملف أو GitHub وحدّث الحالة أولًا.
```

Never label uncertainty as definite failure/success merely to simplify UX.

## 13. P4.1 permission/capability UX

- browsing requires current installed-repository `contents: read` authority;
- ordinary create/update/delete requires repository-scoped `contents: write`;
- writes under `.github/workflows/` additionally require `workflows: write`;
- permission denial uses safe missing-permission copy and says no change occurred;
- cache/callback presence is never presented as permission proof.

## 14. ZIP/project synchronization — future P8 target

ZIP/project sync remains a later batch flow: scan archive → compare → review added/modified/deleted/unchanged/warnings → persisted immutable plan → review branch + coherent commit by default → optional PR. Direct default-branch mass update, if ever enabled, is a separate Tier 2 exception and never the default.

## 15. Clone / update / run commands — P4.3 target

Show detected stack/evidence, choose OS, then separate copyable sections for fresh clone, update existing clone, and setup/run. Never present uncertain guessed commands as verified and never insert tokens or automatically execute repository-controlled instructions.

## 16. GitHub search — P3.1 verified

Search supports query, stars/update sorting, language/min-stars/owner/topic/archive filters, result pagination, active-session callbacks, and detail re-fetch. Public search does not imply repository installation/authorization. `📥 أوامر التنزيل` remains P4.3 placeholder functionality.

## 17. Actions / Issues / PRs / Releases / notifications — future targets

Future screens keep the established control-panel pattern: concise detail, stable resource context, safe navigation, explicit write confirmation, current checks/preconditions before high-impact operations, and no GitHub secret exposure.

Notifications are sent as durable new messages rather than replacing navigation state. Preferences are per repository/event type.

## 18. Loading/empty states

Use concise loading copy only for noticeable operations, then edit to final state where practical. Empty states describe the missing resource without implying auth failure. Installation-only account state is not mislabeled fully disconnected.

## 19. Error copy contract

Authentication/reauthorization:

```text
🔐 يحتاج GitDock إلى إعادة تفويض GitHub لإكمال هذه العملية.
```

Missing permission:

```text
⚠️ هذه العملية تحتاج صلاحية GitHub غير مفعلة حاليًا.
لم يتم إجراء أي تغيير.
```

Rate limit:

```text
⏳ وصل GitDock مؤقتًا إلى حد طلبات GitHub.
لم يتم فقدان أي تغيير. جرّب بعد وقت إعادة الضبط المعروض.
```

Invalid/reused confirmation:

```text
ℹ️ انتهى أو استُخدم هذا التأكيد.
لم يتم تنفيذ أي تغيير.
```

Unexpected:

```text
❌ لم تكتمل العملية.
لم يتم تأكيد أي تغيير غير معروف.

معرّف العملية: GD-...
```

Never show stack traces, secret-bearing raw auth errors, token/private-key data, staged file body, or claim a definite result when reconciliation remains uncertain.

## 20. Danger confirmation patterns

- Tier 2 GitHub writes show operation, repository, current/requested values, and consequence before persisted confirmation.
- Tier 3 repository deletion first requires exact full repository name, then isolated persisted final confirmation.
- Sensitive local account cleanup is labelled local and never implies remote uninstall.
- P4.1 one-file writes use persisted staged intent/confirmation even where the operation is narrower than repository-admin Tier 2/3 because stale/replay/restart safety still requires server-side authority.

## 21. Interaction state rules

- Simple browsing may use lightweight callback/FSM context.
- Long repository paths do not belong in callback data; P4.1 uses short session/index/token context.
- High-impact/sensitive operation state must be persisted server-side with expiry/preconditions.
- Back restores previous meaningful state.
- Cancel invalidates pending confirmation/staged authority and returns safely.
- Repeated callbacks on completed/consumed operations are idempotent or return clear expired/already-used copy.
- Callback payload never serves as sole proof of current authorization.

## 22. Copy style

- Direct and calm.
- Avoid unnecessary jargon.
- Use warnings where consequences matter, not on harmless screens.
- Visually isolate repository/branch/path/login values from prose.
- Avoid excessive emojis; icons communicate category/status rather than decoration.
- When an operation is local-only, say “محلي”.
- When a remote write outcome remains uncertain, say it is uncertain and never imply blind retry is safe.

## 23. Verification state

P3.3 repository administration is fully merged/post-merge/governance verified.

P4.1 implementation head before documentation synchronization: `614f013b35644fcdd05e880c9a37ff30fd503fdf`.

CI `34639736010` verified P4.1 as part of the **148-test** suite on Python 3.12 and 3.13, with Ruff format/lint, mypy across **87 source files**, compile, dependency audit, secret scan, byte-for-byte PEP 751 locks, and PostgreSQL 17 migration roundtrip through `0006_file_write_sessions` all green.

P4.1 remains **implementation verified, merge/governance pending** until documentation-head CI, non-draft PR CI, unchanged-head merge, post-feature `main` CI, and governance closeout complete.
