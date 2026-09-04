# GitDock — Telegram UI/UX Specification

Status: authoritative v1 interaction contract, updated through P3.3 repository-administration UI

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
- Never render access/refresh/installation tokens, OAuth code/state, PKCE verifier, private key, client secret, or raw upstream auth body.

## 3. Navigation contract

Contextual navigation:

```text
[🏠 الرئيسية] [⬅️ رجوع]
```

During active wizards:

```text
[❌ إلغاء] [⬅️ رجوع]
```

Home/Cancel/Back must remain predictable. Home cancels transient search/input state and invalidates pending local-disconnect authority where applicable. In P3.3, once a repository write preview has issued a persisted confirmation, edit/back/cancel consumes that specific confirmation before navigation so an old Telegram confirm button cannot remain active.

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

`👤 حساب GitHub` is real since P3.2. `➕ مستودع جديد` is real in P3.3. Other entries remain placeholders until their roadmap milestone.

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

Public search remains available independently of connection state. Repository creation requires durable GitHub user authorization and does not appear as executable authority merely because a callback exists.

## 5. GitHub account screen — P3.2

The account screen separates two concepts that must not be conflated:

- durable GitHub **user authorization**;
- local GitHub App **installation bindings**.

Authorized example:

```text
👤 حساب GitHub

GitHub: octocat
✅ صلاحية المستخدم: مفعلة
🏢 التثبيتات المرتبطة: 2
🔄 التجديد: متاح

تُحفظ رموز التفويض مشفرة داخل GitDock ولا يتم عرضها هنا.
```

Keyboard:

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
- local disconnect is isolated in its own row.

### P3.2 authorization handoff

After starting user authorization:

```text
🔐 تفويض GitHub

افتح GitHub لإكمال صلاحية المستخدم.
بعد العودة سيحفظ GitDock التفويض بشكل مشفر.
```

```text
[🔐 فتح GitHub]
[🏠 الرئيسية]
```

No OAuth state, verifier, code, client secret, or token is rendered.

### P3.2 local-disconnect confirmation

```text
⚠️ تأكيد قطع الربط المحلي

GitHub: octocat
التثبيتات المحلية: 2

سيحذف GitDock بيانات التفويض والربط المحلية الخاصة بهذا الحساب.
لن يقوم هذا بإلغاء تثبيت GitHub App من GitHub.

إذا تغير التفويض أو التثبيتات بعد فتح هذه الشاشة، يصبح زر التأكيد القديم غير صالح ولن يُحذف شيء.
```

```text
[✅ تأكيد قطع الربط]
[❌ إلغاء]
[🏠 الرئيسية]
```

Rules:

- confirmation is persisted server-side, expires, and is one-time use;
- Confirm/Cancel/Home all invalidate the particular pending authority as appropriate;
- stale/reused/invalid callbacks never claim that deletion happened;
- successful result says that **local** GitDock data was cleared and does not imply remote GitHub App uninstall/revocation.

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

Keyboard:

```text
[1 • GitDock] [2 • WebHub]
[3 • Wasl]    [4 • ...]
[◀️ السابق]   [التالي ▶️]
[🎛 تصفية]    [🔄 تحديث]
[🏠 الرئيسية]
```

Do not place full long repository names in callback payloads; use compact stable IDs.

Filters:

```text
[🔒 خاص] [🌐 عام]
[🟢 نشط] [📦 مؤرشف]
[🌿 المصدر] [🍴 Fork]
[🧹 مسح التصفية]
```

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

Keyboard target contract:

```text
[📁 الملفات]       [📝 Commits]
[🌿 الفروع]        [⚙️ Actions]
[❗ Issues]         [🔀 Pull Requests]
[🏷️ Releases]      [📥 تشغيل/تنزيل]
[🔔 التنبيهات]     [⚙️ إعدادات المستودع]
[🏠 الرئيسية]      [⬅️ رجوع]
```

`⚙️ إعدادات المستودع` is real in P3.3. Unimplemented entries remain placeholders until their milestone.

## 8. Create repository wizard — P3.3 verified

Step 1:

```text
➕ إنشاء مستودع

أرسل اسم المستودع.
مثال: MyProject
```

Step 2:

```text
📝 الوصف

أرسل وصفًا مختصرًا، أو اختر تخطي.
```

```text
[تخطي]
[❌ إلغاء] [⬅️ رجوع]
```

Step 3:

```text
🔐 نوع المستودع
```

```text
[🔒 خاص] [🌐 عام]
```

Step 4 preview:

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

- creation is never performed before preview + persisted Tier 1 confirmation;
- personal create uses current durable GitHub user authorization;
- organization create is supported at the service/gateway boundary when an organization is explicitly requested and authorized; the current Telegram v1 wizard defaults to the linked personal account unless a future UI exposes organization choice;
- `✏️ تعديل البيانات` consumes the issued confirmation before returning to input;
- `❌ إلغاء` consumes the issued confirmation before leaving the preview;
- reused/expired/cancelled confirmation never creates a repository;
- the callback token is transport only; server-side state remains authoritative.

## 9. Repository settings — P3.3 verified

```text
⚙️ إعدادات GitDock

الاسم: GitDock
الظهور: 🔒 خاص
الفرع الافتراضي: main
الحالة: نشط
```

Current keyboard:

```text
[✏️ الاسم]       [📝 الوصف]
[🌐 جعله عامًا / 🔒 جعله خاصًا] [📦 أرشفة / 📤 إلغاء الأرشفة]
[🌿 الفرع الافتراضي]
[🗑 حذف المستودع]
[🏠 الرئيسية] [⬅️ رجوع]
```

Rules:

- delete button is always isolated;
- name/description/default branch collect typed input then show preview;
- visibility and archive/unarchive still pass through a persisted Tier 2 preview/confirmation rather than executing from the settings tap;
- update preview contains the repository target and requested change;
- `✅ تطبيق التغيير` is the only final write action and consumes server-side confirmation;
- Back/Cancel after preview consumes pending confirmation before navigation;
- stale repository state or stale confirmation performs no write and requires reopening/refreshing the settings context.

### P3.3 Tier 2 update preview

```text
⚠️ مراجعة تغيير المستودع

المستودع: owner/repo
التغيير: ...

لن يتم تطبيق التغيير حتى التأكيد.
```

```text
[✅ تطبيق التغيير]
[⬅️ رجوع] [❌ إلغاء]
```

### P3.3 Tier 3 deletion

Deletion has two explicit gates:

1. user must type the exact current full repository name `owner/repo`;
2. GitDock then renders an isolated Tier 3 delete preview backed by a persisted confirmation.

Wrong name does not issue a valid delete confirmation and does not write anything.

Final preview pattern:

```text
🗑 حذف المستودع نهائيًا

المستودع: owner/repo

هذا حذف دائم على GitHub.
```

```text
[🗑 تأكيد الحذف نهائيًا]
[⬅️ رجوع] [❌ إلغاء]
```

The confirmation expires, is single-use, and is invalidated by successful Back/Cancel. Before execution GitDock refreshes repository state and fails closed if the target changed.

## 10. File browser — target

Directory:

```text
📁 GitDock / docs
🌿 main

📁 api
📁 assets
📄 ARCHITECTURE.md
📄 ROADMAP.md
📄 SECURITY_MODEL.md
```

```text
[📁 api] [📁 assets]
[📄 ARCHITECTURE.md]
[📄 ROADMAP.md]
[📄 SECURITY_MODEL.md]
[➕ ملف] [⬆️ رفع/استبدال]
[⬅️ مجلد أعلى]
[🏠 الرئيسية] [⬅️ رجوع]
```

File view:

```text
📄 docs/ARCHITECTURE.md
🌿 main
📦 18.4 KB

<text preview>

الجزء 1 من 4
```

```text
[◀️] [▶️]
[✏️ تعديل] [♻️ استبدال]
[🌿 تغيير الفرع] [📥 تنزيل]
[🗑 حذف]
[🏠 الرئيسية] [⬅️ رجوع]
```

Unsupported/binary content uses metadata/download fallback rather than fake text preview.

## 11. Single-file update confirmation — target

```text
✏️ مراجعة التغيير

📦 GitDock
🌿 feature/update-docs
📄 docs/README.md

+ 8 أسطر
- 3 أسطر

Commit:
Update docs/README.md via GitDock
```

```text
[👁️ عرض Diff]
[✅ تطبيق التغيير]
[❌ إلغاء]
```

If source SHA changed:

```text
⚠️ تغير الملف في GitHub بعد فتحه.
لم يتم استبدال أي شيء.
حدّث الملف وراجع التغييرات من جديد.
```

```text
[🔄 تحديث ومقارنة]
[❌ إلغاء]
```

## 12. ZIP/project synchronization — target

Start:

```text
♻️ تحديث المشروع

📦 GitDock
🌿 الأساس: main

أرسل ملف ZIP للمشروع.
سيتم فحصه ومقارنته قبل رفع أي تغيير.
```

Comparison:

```text
🔍 نتيجة المقارنة

➕ جديد: 7
✏️ معدل: 14
🗑 محذوف: 2
⭕ بدون تغيير: 83
⚠️ يحتاج مراجعة: 1

الأساس: main @ a81c2f1
الطريقة الافتراضية: فرع مراجعة + Commit واحد
```

```text
[➕ الملفات الجديدة] [✏️ المعدلة]
[🗑 المحذوفة]       [⚠️ التحذيرات]
[👁️ عرض Diff]
[✅ متابعة الرفع]
[❌ إلغاء]
```

Final apply:

```text
⚠️ تأكيد تحديث المشروع

سيتم إنشاء الفرع:
gitdock/sync-20260831-0230

ثم تطبيق 23 تغييرًا في Commit واحد.
لن يتم تعديل main مباشرة.
```

```text
[✅ إنشاء الفرع والتحديث]
[🔀 إنشاء PR بعد التحديث]
[❌ إلغاء]
```

Direct default-branch mode, if ever enabled, uses separate Tier 2 confirmation and is not the default action.

## 13. Clone / update / run commands — P4.3 target

```text
📥 تشغيل وتنزيل GitDock

تم التعرف على المشروع:
🐍 Python
المصدر: pyproject.toml + README.md

اختر النظام:
```

```text
[🪟 Windows] [🐧 Linux]
[🍎 macOS]
```

Then show separate copyable blocks for:

- 📥 تنزيل جديد;
- 🔄 تحديث نسخة موجودة;
- ▶️ الإعداد والتشغيل.

```text
[📋 أوامر مختصرة] [ℹ️ كيف تم اكتشافها؟]
[🏠 الرئيسية] [⬅️ رجوع]
```

Never present uncertain guessed run commands as verified facts and never insert tokens.

## 14. GitHub search — P3.1

Start:

```text
🔎 البحث في GitHub

اكتب اسم المشروع أو الفكرة.
مثال:
telegram github manager
```

Results:

```text
🔎 نتائج: telegram github manager

1) owner/project
⭐ 12.8K • 🍴 1.4K • Python
MIT • تم التحديث قبل 3 أيام
وصف مختصر...
```

```text
[1 • التفاصيل] [2 • التفاصيل]
[⭐ الأكثر نجومًا] [🔄 آخر تحديث]
[🎛 التصفية] [🔎 بحث جديد]
[◀️] [▶️]
[🏠 الرئيسية]
```

Filters may include language, min-stars, owner/org, topic, and archive visibility. Search callbacks are active-session scoped; an older session fails closed after a newer search starts. Public search does not imply repository installation/authorization.

## 15. Actions screen — target

```text
⚙️ Actions — GitDock

✅ tests
آخر تشغيل: ناجح • 2m 14s

❌ deploy
آخر تشغيل: فشل • 48s

⏳ build
قيد التشغيل • 1m 03s
```

```text
[✅ tests] [❌ deploy]
[⏳ build]
[▶️ تشغيل Workflow]
[🔄 تحديث]
[🏠 الرئيسية] [⬅️ رجوع]
```

Run detail shows run number/ref/SHA/duration/jobs plus Logs/steps/retry/artifacts/GitHub navigation. Workflow dispatch must show workflow, ref, and all inputs before final confirmation.

## 16. Issue detail — target

```text
❗ Issue #42
Login fails after token refresh

🟢 مفتوحة
👤 author
🏷 bug, auth
💬 6 تعليقات
```

```text
[💬 التعليقات] [✍️ رد]
[🏷 Labels] [👤 Assignees]
[✅ إغلاق]
[🔗 GitHub]
[🏠 الرئيسية] [⬅️ رجوع]
```

## 17. Pull request detail — target

```text
🔀 PR #18
Fix webhook retries

🟢 مفتوح
feature/retry → main
✅ CI ناجح
💬 4 • مراجعات: 2
```

```text
[📄 الملفات] [💬 المحادثة]
[✅ Checks] [👀 المراجعات]
[✍️ تعليق] [🧪 مراجعة]
[🔀 دمج]
[🔗 GitHub]
[🏠 الرئيسية] [⬅️ رجوع]
```

Merge is confirmation-gated and surfaces failing/pending checks before confirmation.

## 18. Notifications — target

Durable notification example:

```text
🔔 GitDock

💬 تعليق جديد على Issue #42
📦 Wasl
👤 username

"..."
```

```text
[👁️ عرض المحادثة] [✍️ رد]
[🔕 كتم هذا النوع]
```

Workflow failure example provides Logs/retry/mute Actions. Notifications are new messages, not navigation-screen edits.

## 19. Notification preferences — target

```text
🔔 تنبيهات GitDock

✅ Push
✅ Issues
✅ التعليقات
✅ Pull Requests
✅ Actions
✅ Releases
❌ Stars
❌ Forks
```

Controls are per event/repository and include repository mute.

## 20. Loading state

For noticeable operations:

```text
⏳ جاري تحميل بيانات المستودع...
```

Then edit in place to result/error where practical. Do not spam loading messages for tiny requests.

For authorization refresh or repository administration, use concise status/error copy; do not expose transport/token details.

## 21. Empty states

Examples:

```text
📦 لا توجد مستودعات متاحة لهذا الربط.
```

```text
⚙️ لا توجد Workflows في هذا المستودع.
```

```text
🔔 لا توجد أحداث جديدة حاليًا.
```

Account state with installations but no durable UAT is not labelled “fully disconnected”; it explains that user authorization is not active and offers activation/local disconnect.

## 22. Error copy contract

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

Unexpected:

```text
❌ لم تكتمل العملية.
لم يتم تأكيد أي تغيير غير معروف.

معرّف العملية: GD-...
```

P3.2 stale local confirmation:

```text
⚠️ تغيرت حالة الربط منذ فتح شاشة التأكيد.
لم يتم حذف أي ربط أو رمز.
افتح حساب GitHub وحدّث الحالة قبل المحاولة من جديد.
```

Invalid/reused confirmation:

```text
ℹ️ انتهى أو استُخدم هذا التأكيد.
لم يتم تنفيذ أي تغيير.
```

P3.3 stale repository administration:

```text
⚠️ تغيرت حالة المستودع منذ فتح شاشة التأكيد.
لم يتم تطبيق التغيير.
افتح إعدادات المستودع وحدّث الحالة ثم راجع العملية من جديد.
```

P3.3 uncertain remote write:

```text
⚠️ تعذر تأكيد النتيجة النهائية من GitHub.
لم يقم GitDock بإعادة تنفيذ العملية تلقائيًا.
حدّث حالة المستودع قبل أي محاولة جديدة.
```

Never show stack traces, secret-bearing raw auth errors, token/private-key data, or claim a definite result when reconciliation remains uncertain.

## 23. Danger confirmation patterns

### Tier 2 GitHub write

```text
⚠️ عملية مؤثرة

العملية: تغيير ظهور المستودع
المستودع: owner/repo
من: 🔒 خاص
إلى: 🌐 عام

راجع البيانات قبل المتابعة.
```

```text
[✅ تطبيق التغيير]
[❌ إلغاء]
```

P3.3 Tier 2 confirmations are persisted server-side, expire, are single-use, and are invalidated by successful Back/Cancel.

### Tier 3 repository deletion

First require exact full repository name, then final isolated delete button. Confirmation expires and cannot be reused. Before executing, GitDock refreshes current repository state; stale target/preconditions fail closed.

### Sensitive local account cleanup

P3.2 local disconnect uses the dedicated account confirmation from section 5. It is not described as GitHub repository deletion or remote App uninstall, but still uses persisted explicit confirmation because it destroys local credential/binding state.

## 24. Interaction state rules

- Simple browsing may use lightweight callback context.
- Wizards may use aiogram FSM.
- High-impact/sensitive operation state must also be persisted server-side with expiry/preconditions.
- Back restores previous meaningful state.
- Cancel invalidates pending confirmation/session and returns safely.
- Home invalidates transient search/input state and pending GitHub local-disconnect confirmations as defined by the active flow.
- After a P3.3 create/update/delete preview exists, edit/back/cancel consumes the specific pending write confirmation before navigation.
- Repeated callbacks on completed/consumed operations are idempotent or return clear expired/already-used copy.
- Callback payload never serves as sole proof of current authorization.
- Repository write callbacks carry compact IDs/tokens, not durable credentials or full authorization state.

## 25. Copy style

- Direct and calm.
- Avoid unnecessary jargon.
- Do not overuse “رسمي/غير رسمي” or warnings on harmless screens.
- Use warnings exactly where consequences matter.
- Visually isolate repository/branch/path/login values from prose.
- Avoid excessive emojis; icons communicate category/status rather than decoration.
- When an operation is local-only, say “محلي” and never imply a remote GitHub effect that did not happen.
- When a remote write outcome remains uncertain, say it is uncertain and never imply that retry is safe by default.

## 26. P3.3 verification

Implementation head before documentation synchronization: `4e71d7f1c962e61584d6532d03c913703dc5295a`.

CI `33890407945` verified the P3.3 UI/service integration as part of the **117-test** suite on Python 3.12 and 3.13, including repository-admin callback/keyboards/renderers, confirmation cancellation semantics, create/update/delete service paths, and stale/negative behavior. PostgreSQL 17 migration and all configured quality/security/lock gates also passed.

P3.3 remains merge/governance pending until the documentation-head CI, non-draft PR, unchanged-head merge, post-merge `main` CI, and governance closeout complete.
