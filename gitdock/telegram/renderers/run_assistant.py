"""Arabic HTML renderers for P4.3 clone/setup/run guidance."""

from __future__ import annotations

from html import escape

from gitdock.domain.run_assistant import (
    CommandPlan,
    CommandSuggestion,
    Confidence,
    PlanNote,
    TargetOS,
)

_OS_LABELS = {
    TargetOS.WINDOWS: "Windows PowerShell",
    TargetOS.LINUX: "Linux",
    TargetOS.MACOS: "macOS",
}
_CONFIDENCE_LABELS = {
    Confidence.HIGH: "عالية",
    Confidence.MEDIUM: "متوسطة",
    Confidence.LOW: "منخفضة",
}


def render_os_prompt(repository_full_name: str) -> str:
    return (
        "📥 تشغيل/تنزيل\n\n"
        f"📦 {repository_full_name}\n\n"
        "اختر نظام التشغيل لتوليد أوامر مناسبة له.\n"
        "GitDock يولّد الأوامر للنسخ فقط ولا ينفذها تلقائيًا."
    )


def render_command_plan(plan: CommandPlan) -> str:
    stacks = "، ".join(item.stack.value for item in plan.stacks) or "لم يُكتشف Stack مؤكد"
    sections = [
        "📥 <b>تشغيل/تنزيل</b>",
        "",
        f"📦 <code>{escape(plan.repository_full_name)}</code>",
        f"🖥 النظام: <b>{escape(_OS_LABELS[plan.target_os])}</b>",
        f"🌿 الفرع الافتراضي: <code>{escape(plan.default_branch)}</code>",
        f"🔎 المكتشف: {escape(stacks)}",
        "",
        _commands_section("1️⃣ نسخة جديدة", plan.clone_fresh),
        _commands_section("2️⃣ تحديث نسخة موجودة", plan.update_existing),
    ]

    if plan.setup:
        sections.extend(("", "🔧 <b>3️⃣ إعداد الاعتمادات / البناء</b>"))
        for suggestion in plan.setup:
            sections.append(_suggestion(suggestion))
    else:
        sections.extend(("", "🔧 <b>3️⃣ الإعداد</b>\nلا توجد أوامر إعداد مؤكدة من الأدلة الحالية."))

    if plan.run:
        sections.extend(("", "▶️ <b>4️⃣ التشغيل</b>"))
        for suggestion in plan.run:
            sections.append(_suggestion(suggestion))
    else:
        sections.extend(("", "▶️ <b>4️⃣ التشغيل</b>\nلم يتم استنتاج أمر تشغيل موثوق."))

    if plan.notes:
        sections.extend(("", "⚠️ <b>ملاحظات الأمان والدقة</b>"))
        sections.extend(f"• {_note(note)}" for note in plan.notes)

    sections.extend(
        (
            "",
            "🔒 لا تتضمن الأوامر أي GitHub token أو بيانات دخول، ولا ينفذ GitDock أي أمر تلقائيًا.",
            "⚠️ أوامر الإعداد/التشغيل قد تشغّل hooks أو build logic أو scripts من داخل المشروع عند تنفيذك لها؛ راجع المشروع والأمر قبل التشغيل.",
        )
    )
    return "\n".join(sections)


def _commands_section(title: str, commands: tuple[str, ...]) -> str:
    body = escape("\n".join(commands))
    return f"<b>{title}</b>\n<pre>{body}</pre>"


def _suggestion(suggestion: CommandSuggestion) -> str:
    label = "إعداد" if suggestion.purpose.value == "setup" else "تشغيل"
    confidence = _CONFIDENCE_LABELS[suggestion.confidence]
    sources = "، ".join(escape(source) for source in suggestion.sources) or "—"
    body = escape("\n".join(suggestion.commands))
    note = f"\n⚠️ {_note(suggestion.note)}" if suggestion.note is not None else ""
    return (
        f"\n<b>{label} {escape(suggestion.stack.value)}</b>"
        f"\nالثقة: {confidence} | المصدر: {sources}"
        f"\n<pre>{body}</pre>{note}"
    )


def _note(note: PlanNote) -> str:
    if note is PlanNote.README_PRESENT:
        return "README موجود، لكن GitDock لا ينسخ أو ينفذ أوامره تلقائيًا؛ راجعه بنفسك."
    if note is PlanNote.REPOSITORY_DEFINED_COMMAND:
        return "بعض أوامر التشغيل تستدعي script/entry point معرفًا داخل المستودع؛ راجعه قبل التنفيذ."
    if note is PlanNote.DOCKER_RUNTIME_OPTIONS:
        return "أمر Dockerfile عام وقد يحتاج ports أو volumes أو environment variables إضافية."
    if note is PlanNote.NO_STACK_EVIDENCE:
        return "لم توجد ملفات جذرية كافية لتحديد Stack؛ أوامر Git فقط هي المؤكدة."
    if note is PlanNote.NO_RUN_COMMAND:
        return "لم يخمّن GitDock أمر تشغيل عند غياب دليل واضح."
    return "راجع الأمر ومصدره قبل التنفيذ."
