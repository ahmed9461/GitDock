"""Centralized Arabic renderers for P4.1 file browsing and writes."""

from __future__ import annotations

from math import ceil

from gitdock.github.contents import ContentKind
from gitdock.services.file_types import (
    DirectoryView,
    FileDisplayKind,
    FileView,
    FileWriteOutcome,
    FileWritePlan,
    FileWriteState,
)

DIRECTORY_PAGE_SIZE = 8


def render_directory(view: DirectoryView, *, page: int = 1) -> str:
    effective, total = directory_page_numbers(len(view.entries), page)
    start = (effective - 1) * DIRECTORY_PAGE_SIZE
    visible = view.entries[start : start + DIRECTORY_PAGE_SIZE]
    location = view.repository.name if not view.path else f"{view.repository.name} / {view.path}"
    lines = [f"📁 {location}", f"🌿 {view.ref}", ""]
    if visible:
        for entry in visible:
            icon = "📁" if entry.kind is ContentKind.DIRECTORY else "📄"
            lines.append(f"{icon} {entry.name}")
    else:
        lines.append("المجلد فارغ.")
    if total > 1:
        lines.extend(["", f"الصفحة {effective} من {total}"])
    return "\n".join(lines)


def render_file(view: FileView, *, page: int = 1) -> str:
    total = max(1, len(view.preview_pages))
    effective = min(max(page, 1), total)
    lines = [
        f"📄 {view.file.path}",
        f"🌿 {view.ref}",
        f"📦 {_size(view.file.size)}",
        "",
    ]
    if view.display_kind is FileDisplayKind.TEXT:
        lines.append(view.preview_pages[effective - 1])
        if total > 1:
            lines.extend(["", f"الجزء {effective} من {total}"])
    elif view.display_kind is FileDisplayKind.BINARY:
        lines.append("هذا ملف ثنائي؛ لن يعرض GitDock محتواه كنص.")
    elif view.display_kind is FileDisplayKind.LARGE:
        lines.append("الملف أكبر من حد المعاينة النصية؛ استخدم التنزيل أو افتحه في GitHub.")
    else:
        lines.append("GitHub لم يُرجع محتوى قابلًا للمعاينة هنا.")
    return "\n".join(lines)


def render_ref_prompt(current_ref: str) -> str:
    return (
        "🌿 تغيير الفرع / المرجع\n\n"
        f"الحالي: {current_ref}\n\n"
        "أرسل اسم فرع أو Tag أو SHA.\n"
        "ملاحظة: عمليات الكتابة تحتاج فرعًا حقيقيًا، وليس Tag أو SHA ثابتًا."
    )


def render_create_name_prompt(directory_path: str) -> str:
    location = directory_path or "/"
    return f"\u2795 ملف جديد\n\n\u0627لمجلد: {location}\n\nأرسل اسم الملف فقط، مثال: README.md"


def render_create_content_prompt(path: str) -> str:
    return (
        f"📝 محتوى الملف\n\n📄 {path}\n\n"
        "أرسل النص الكامل الذي تريد حفظه في الملف.\n"
        "للملفات الثنائية استخدم «رفع/استبدال» بدلًا من ذلك."
    )


def render_document_prompt(*, replace_path: str | None = None) -> str:
    if replace_path is not None:
        return f"♻️ استبدال ملف\n\n📄 {replace_path}\n\nأرسل الملف الجديد كمستند في تلجرام."
    return (
        "⬆️ رفع/استبدال\n\n"
        "أرسل ملفًا كمستند في تلجرام.\n"
        "إذا كان الاسم موجودًا في المجلد الحالي سيظهر لك Preview للاستبدال، وإلا للإنشاء."
    )


def render_edit_prompt(path: str) -> str:
    return (
        f"✏️ تعديل الملف\n\n📄 {path}\n\n"
        "أرسل النص الكامل البديل للملف. لن يتغير GitHub قبل شاشة المراجعة والتأكيد."
    )


def render_write_preview(plan: FileWritePlan) -> str:
    title = {
        "file.create": "\u2795 مراجعة إنشاء الملف",
        "file.update": "✏️ مراجعة التغيير",
        "file.delete": "🗑 مراجعة حذف الملف",
    }.get(plan.operation, "⚠️ مراجعة تغيير الملف")
    lines = [
        title,
        "",
        f"📦 {plan.repository.full_name}",
        f"🌿 {plan.branch}",
        f"📄 {plan.path}",
        "",
    ]
    if plan.diff is not None:
        lines.extend([f"+ {plan.diff.additions} أسطر", f"- {plan.diff.deletions} أسطر", ""])
    else:
        lines.extend(["المحتوى ثنائي/غير نصي؛ لا تتوفر معاينة Diff نصية.", ""])
    lines.extend(["Commit:", _default_commit_message(plan), "", "لن يتم تغيير GitHub حتى التأكيد."])
    return "\n".join(lines)


def render_diff(plan: FileWritePlan) -> str:
    if plan.diff is None or not plan.diff.preview:
        return "👁️ Diff\n\nل\u0627 توجد معاينة نصية متاحة لهذا التغيير."
    return f"👁️ Diff — {plan.path}\n\n{plan.diff.preview}"


def render_write_outcome(outcome: FileWriteOutcome) -> str:
    target = outcome.path or "الملف المحدد"
    if outcome.state is FileWriteState.APPLIED:
        lines = ["✅ تم تطبيق التغيير على GitHub", "", f"📄 {target}"]
        if outcome.branch:
            lines.append(f"🌿 {outcome.branch}")
        if outcome.commit_sha:
            lines.append(f"Commit: {outcome.commit_sha[:12]}")
        return "\n".join(lines)
    if outcome.state is FileWriteState.STALE:
        return (
            "⚠️ تغير الملف أو الفرع في GitHub بعد فتحه.\n"
            "لم يتم استبدال أو حذف أي شيء.\n"
            "حدّث الملف وراجع التغييرات من جديد."
        )
    if outcome.state is FileWriteState.UNCERTAIN:
        return (
            "⚠️ نتيجة العملية غير محسومة.\n\n"
            "تعذر إثبات نجاح أو فشل التغيير بعد انقطاع/خطأ GitHub.\n"
            "لا تعِد تنفيذ العملية بشكل أعمى؛ افتح الملف أو GitHub وحدّث الحالة أولًا."
        )
    return "⚠️ التأكيد غير صالح أو منتهي أو تم استخدامه/إلغاؤه سابقًا. لم يُنفذ تغيير جديد."


def render_file_error(message: str) -> str:
    return f"⚠️ تعذر إكمال عملية الملفات\n\n{message}"


def render_file_cancelled() -> str:
    return "❌ تم إلغاء العملية. لم يتم تغيير أي ملف في GitHub."


def directory_page_numbers(total_items: int, page: int) -> tuple[int, int]:
    total_pages = max(1, ceil(total_items / DIRECTORY_PAGE_SIZE))
    return min(max(page, 1), total_pages), total_pages


def _default_commit_message(plan: FileWritePlan) -> str:
    verb = {
        "file.create": "Create",
        "file.update": "Update",
        "file.delete": "Delete",
    }.get(plan.operation, "Update")
    return f"{verb} {plan.path} via GitDock"


def _size(value: int) -> str:
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"
