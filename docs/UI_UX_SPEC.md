# GitDock — Telegram UI/UX Specification

Status: authoritative v1 interaction contract

## 1. Experience goal

GitDock should feel like a compact professional GitHub control panel inside Telegram. The user should always know:

- where they are;
- which repository/ref/resource is selected;
- whether an action is read-only or will change GitHub;
- what will happen before a risky action is confirmed;
- how to return Home/Back without starting over.

Arabic is the primary UI language. Technical values such as repository names, branch names, paths, workflow names, SHAs, and commands remain as-is.

## 2. Rendering rules

- Prefer editing the current screen message for navigation.
- Send a new message when it is a durable event/notification, a file/document, a large log, or a user action result worth preserving.
- Use Telegram rich text/entities through a centralized renderer; do not hand-build raw formatting strings throughout handlers.
- Keep primary screens concise.
- Put secondary detail behind buttons.
- Default to 2 primary buttons per row maximum.
- Do not mix a destructive action into a row with harmless navigation.
- Always show target context for write actions.
- Use consistent icons from `docs/CONSTANTS.md`.

## 3. Navigation contract

Contextual bottom row should use these labels consistently:

```text
[🏠 الرئيسية] [⬅️ رجوع]
```

During active wizards:

```text
[❌ إلغاء] [⬅️ رجوع]
```

Where Home + Cancel + Back are all needed, keep them clear and avoid rearranging order randomly between screens.

## 4. Home screen

Message:

```text
🐙 GitDock

إدارة GitHub من تلجرام

👤 GitHub: ahmed9461
📦 المستودعات: 24
🔔 التنبيهات: مفعلة
✅ الاتصال: سليم
```

Keyboard:

```text
[📦 مستودعاتي]    [🔎 البحث في GitHub]
[🔔 التنبيهات]    [📊 النشاط]
[➕ مستودع جديد]  [⚙️ الإعدادات]
```

If GitHub is not connected:

```text
🐙 GitDock

لم يتم ربط حساب GitHub بعد.
اربط الحساب لعرض مستودعاتك وإدارتها بأمان.
```

```text
[🔗 ربط GitHub]
[ℹ️ كيف يعمل الربط؟]
```

## 5. Repository list

Message example:

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
[🔎 تصفية]    [🔄 تحديث]
[🏠 الرئيسية]
```

Do not put full long repository names inside callback payloads; use short interaction IDs.

Filters:

```text
[🔒 خاص] [🌐 عام]
[🟢 نشط] [📦 مؤرشف]
[🌿 المصدر] [🍴 Fork]
[مسح التصفية]
```

## 6. Repository dashboard

Message example:

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

Keyboard:

```text
[📁 الملفات]       [📝 Commits]
[🌿 الفروع]        [⚙️ Actions]
[❗ Issues]         [🔀 Pull Requests]
[🏷️ Releases]      [📥 تشغيل/تنزيل]
[🔔 التنبيهات]     [⚙️ إعدادات المستودع]
[🏠 الرئيسية]      [⬅️ رجوع]
```

## 7. Create repository wizard

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

Creation is not performed before preview/confirm.

## 8. Repository settings

```text
⚙️ إعدادات GitDock

الاسم: GitDock
الظهور: 🔒 خاص
الفرع الافتراضي: main
الحالة: نشط
```

```text
[✏️ الاسم]       [📝 الوصف]
[👁️ الظهور]      [📦 أرشفة]
[🌿 الفرع الافتراضي]
[🗑 حذف المستودع]
[🏠 الرئيسية] [⬅️ رجوع]
```

The delete button is always isolated.

## 9. File browser

Directory screen:

```text
📁 GitDock / docs
🌿 main

📁 api
📁 assets
📄 ARCHITECTURE.md
📄 ROADMAP.md
📄 SECURITY_MODEL.md
```

Keyboard uses numbered/short labels if paths are long:

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

Do not attempt inline text preview for unsupported/binary content.

## 10. Single-file update confirmation

Before write:

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

If source SHA changed after preview:

```text
⚠️ تغير الملف في GitHub بعد فتحه.
لم يتم استبدال أي شيء.
حدّث الملف وراجع التغييرات من جديد.
```

```text
[🔄 تحديث ومقارنة]
[❌ إلغاء]
```

## 11. ZIP/project synchronization

Start:

```text
♻️ تحديث المشروع

📦 GitDock
🌿 الأساس: main

أرسل ملف ZIP للمشروع.
سيتم فحصه ومقارنته قبل رفع أي تغيير.
```

After analysis:

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

Final apply screen:

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

Direct default-branch mode, when enabled, uses a separate Tier 2 confirmation and is not shown as the default button.

## 12. Clone / update / run commands

Screen:

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

Then:

```text
📥 تنزيل جديد

<copyable command block>

🔄 تحديث نسخة موجودة

<copyable command block>

▶️ الإعداد والتشغيل

<copyable command block>
```

```text
[📋 أوامر مختصرة] [ℹ️ كيف تم اكتشافها؟]
[🏠 الرئيسية] [⬅️ رجوع]
```

Never present uncertain guessed run commands as verified facts.

## 13. GitHub search

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

2) owner/another
⭐ 7.1K • 🍴 620 • TypeScript
Apache-2.0 • تم التحديث أمس
```

```text
[1 • التفاصيل] [2 • التفاصيل]
[⭐ الأكثر نجومًا] [🔄 آخر تحديث]
[🎛 التصفية] [🔎 بحث جديد]
[◀️] [▶️]
[🏠 الرئيسية]
```

Filter screen:

```text
[🐍 Python] [🟨 JavaScript]
[🔷 TypeScript] [🤖 Kotlin]
[⭐ حد أدنى] [👤 مالك/منظمة]
[#️⃣ Topic] [📦 إخفاء المؤرشف]
[✅ تطبيق] [🧹 مسح]
```

## 14. Actions screen

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

Run detail:

```text
❌ deploy #128
🌿 main
📝 a81c2f1
⏱ 48s

Jobs:
✅ tests
❌ deploy-server
```

```text
[📜 Logs] [🧩 الخطوات]
[🔁 إعادة الفاشل] [📦 Artifacts]
[🔗 فتح في GitHub]
[⬅️ رجوع]
```

Workflow dispatch wizard must show selected workflow, ref, and all inputs before final confirmation.

## 15. Issue detail

```text
❗ Issue #42
Login fails after token refresh

🟢 مفتوحة
👤 author
🏷 bug, auth
💬 6 تعليقات

آخر تعليق:
...
```

```text
[💬 التعليقات] [✍️ رد]
[🏷 Labels] [👤 Assignees]
[✅ إغلاق]
[🔗 GitHub]
[🏠 الرئيسية] [⬅️ رجوع]
```

## 16. Pull request detail

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

Merge is always confirmation-gated and should surface failing/pending CI/check state before confirmation.

## 17. Notifications

Example durable notification:

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

Workflow failure:

```text
❌ GitHub Actions فشل

📦 WebHub
⚙️ Build APK
🌿 main
📝 f314c9a

المهمة الفاشلة: build-release
```

```text
[📜 Logs] [🔁 إعادة الفاشل]
[🔕 كتم Actions]
```

Notification messages are new messages; they are not navigation-screen edits.

## 18. Notification preferences

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

```text
[Push ✅] [Issues ✅]
[Comments ✅] [PR ✅]
[Actions ✅] [Releases ✅]
[Stars ❌] [Forks ❌]
[🔕 كتم المستودع]
[⬅️ رجوع]
```

## 19. Generic loading state

For actions expected to take noticeable time:

```text
⏳ جاري تحميل بيانات المستودع...
```

Then edit in place to result/error when practical.

Do not send a new “loading” message for every tiny API request.

## 20. Empty states

No repositories:

```text
📦 لا توجد مستودعات متاحة لهذا الربط.

يمكنك إنشاء مستودع جديد أو تعديل المستودعات المسموح لـ GitDock بالوصول إليها.
```

No Actions:

```text
⚙️ لا توجد Workflows في هذا المستودع.
```

No notifications:

```text
🔔 لا توجد أحداث جديدة حاليًا.
```

## 21. Error copy contract

Authentication:

```text
🔐 يحتاج GitDock إلى إعادة ربط GitHub لإكمال هذه العملية.
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

Unexpected error:

```text
❌ لم تكتمل العملية.
لم يتم تأكيد أي تغيير غير معروف.

معرّف العملية: GD-...
```

Never show stack traces, raw authorization errors containing secrets, or internal private-key/token data.

## 22. Danger confirmation patterns

### Tier 2

```text
⚠️ عملية مؤثرة

العملية: تغيير ظهور المستودع
المستودع: owner/repo
من: 🔒 خاص
إلى: 🌐 عام

راجع البيانات قبل المتابعة.
```

```text
[⚠️ تأكيد التغيير]
[❌ إلغاء]
```

### Tier 3 repository deletion

Step 1:

```text
🗑 حذف المستودع

سيتم حذف:
owner/repo

هذه عملية غير قابلة للتراجع من GitDock.
أرسل اسم المستودع كاملًا للتأكيد:
owner/repo
```

Only an exact normalized match proceeds.

Step 2:

```text
🚨 التأكيد النهائي

owner/repo

سيتم إرسال طلب الحذف إلى GitHub الآن.
```

```text
[🗑 نعم، احذف المستودع]
[❌ إلغاء]
```

Confirmation expires and cannot be reused.

## 23. Interaction state rules

- Simple browsing may use lightweight callback context.
- Wizards may use aiogram FSM for conversational flow.
- High-impact operation state must also be persisted server-side with expiry/preconditions.
- Back restores the previous meaningful screen/state, not an arbitrary handler default.
- Cancel invalidates any pending confirmation/session and returns to a safe parent/home screen.
- Repeated callback presses on completed operations must be idempotent or return a clear “already completed/expired” result.

## 24. Copy style

- Direct and calm.
- No unnecessary technical jargon in user-facing errors.
- Do not overuse “رسمي/غير رسمي” or security warnings on harmless screens.
- Use warnings exactly where consequences matter.
- Repository/branch/path names are visually isolated from prose.
- Avoid excessive emojis; icons convey category/status rather than decoration.