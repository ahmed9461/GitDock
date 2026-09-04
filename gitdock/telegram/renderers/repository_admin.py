"""Arabic renderers for repository creation and administration flows."""

from __future__ import annotations

from gitdock.github.repositories import RepositorySnapshot
from gitdock.github.repository_admin import RepositoryUpdateRequest
from gitdock.services.repository_admin import (
    RepositoryAdminResult,
    RepositoryAdminState,
    RepositoryCreatePlan,
    RepositoryDeletePlan,
    RepositoryUpdatePlan,
)


def render_create_name_prompt() -> str:
    return "➕ إنشاء مستودع\n\nأرسل اسم المستودع.\nمثال: MyProject"


def render_create_description_prompt(name: str) -> str:
    return f"📝 الوصف\n\nالمستودع: {name}\nأرسل وصفًا مختصرًا، أو اختر تخطي."


def render_create_visibility_prompt(name: str, description: str | None) -> str:
    description_label = description or "بدون وصف"
    return f"🔐 نوع المستودع\n\nالاسم: {name}\nالوصف: {description_label}\n\nاختر مستوى الظهور."


def render_create_preview(plan: RepositoryCreatePlan) -> str:
    request = plan.request
    visibility = "🔒 خاص" if request.private else "🌐 عام"
    description = request.description or "بدون وصف"
    return (
        "✅ مراجعة الإنشاء\n\n"
        f"الاسم: {request.name.strip()}\n"
        f"المالك: {plan.owner_label}\n"
        f"النوع: {visibility}\n"
        f"الوصف: {description}\n\n"
        "سيتم إنشاء المستودع في GitHub فقط بعد الضغط على زر التأكيد."
    )


def render_repository_settings(repository: RepositorySnapshot) -> str:
    visibility = "🔒 خاص" if repository.private else "🌐 عام"
    status = "📦 مؤرشف" if repository.archived else "🟢 نشط"
    description = repository.description or "بدون وصف"
    return (
        f"⚙️ إعدادات {repository.name}\n\n"
        f"الاسم: {repository.name}\n"
        f"الظهور: {visibility}\n"
        f"الفرع الافتراضي: {repository.default_branch}\n"
        f"الحالة: {status}\n"
        f"الوصف: {description}\n\n"
        "أي تغيير على GitHub سيعرض للمراجعة قبل التنفيذ."
    )


def render_setting_input(action: str, repository: RepositorySnapshot) -> str:
    prompts = {
        "name": (f"✏️ تغيير اسم المستودع\n\nالحالي: {repository.name}\n\nأرسل الاسم الجديد."),
        "desc": (
            "📝 تعديل الوصف\n\n"
            f"الحالي: {repository.description or 'بدون وصف'}\n\n"
            "أرسل الوصف الجديد. أرسل - لمسح الوصف."
        ),
        "branch": (
            "🌿 تغيير الفرع الافتراضي\n\n"
            f"الحالي: {repository.default_branch}\n\n"
            "أرسل اسم الفرع الجديد. يجب أن يكون الفرع موجودًا في GitHub."
        ),
        "delete": (
            "⚠️ حذف المستودع نهائيًا\n\n"
            f"المستودع: {repository.full_name}\n\n"
            "للمتابعة اكتب الاسم الكامل كما هو تمامًا:\n"
            f"{repository.full_name}"
        ),
    }
    return prompts[action]


def render_update_preview(plan: RepositoryUpdatePlan) -> str:
    changes = _render_update_changes(plan.request)
    return (
        "⚠️ مراجعة تغيير المستودع\n\n"
        f"المستودع: {plan.repository.full_name}\n"
        f"{changes}\n\n"
        "لن يطبق GitDock التغيير قبل التأكيد. إذا تغير المستودع في GitHub قبل التأكيد، "
        "سيتم رفض العملية كحالة قديمة."
    )


def render_delete_preview(plan: RepositoryDeletePlan) -> str:
    return (
        "🚨 تأكيد الحذف النهائي\n\n"
        f"المستودع: {plan.repository.full_name}\n"
        "سيُحذف المستودع من GitHub. هذه عملية مدمرة ولا يمكن لـGitDock التراجع عنها.\n\n"
        "اضغط تأكيد الحذف فقط إذا كنت متأكدًا."
    )


def render_repository_admin_result(result: RepositoryAdminResult, operation: str) -> str:
    if result.state is RepositoryAdminState.APPLIED:
        if operation == "delete":
            target = result.repository.full_name if result.repository is not None else "المستودع"
            return f"✅ تم حذف المستودع من GitHub\n\n{target}"
        if operation == "create":
            target = result.repository.full_name if result.repository is not None else "المستودع"
            return f"✅ تم إنشاء المستودع بنجاح\n\n{target}"
        target = result.repository.full_name if result.repository is not None else "المستودع"
        return f"✅ تم تطبيق التغيير على GitHub\n\n{target}"
    if result.state is RepositoryAdminState.UNCERTAIN:
        return (
            "⚠️ نتيجة العملية غير محسومة\n\n"
            "تعذر إثبات ما إذا كان GitHub طبق التغيير أم لا بعد انقطاع الاتصال. "
            "لم يقم GitDock بإعادة تنفيذ العملية بشكل أعمى. حدّث حالة المستودع قبل أي محاولة جديدة."
        )
    if result.state is RepositoryAdminState.STALE:
        return (
            "⚠️ تغيرت حالة المستودع بعد فتح شاشة التأكيد.\n"
            "لم ينفذ GitDock التغيير. حدّث المستودع وراجع العملية من جديد."
        )
    return "⚠️ التأكيد غير صالح أو منتهي أو تم استخدامه سابقًا.\nلم ينفذ GitDock أي تغيير."


def render_invalid_repository_admin_input(message: str) -> str:
    return f"⚠️ {message}\n\nلم يتم تنفيذ أي تغيير على GitHub."


def _render_update_changes(request: RepositoryUpdateRequest) -> str:
    lines: list[str] = []
    if request.name is not None:
        lines.append(f"الاسم الجديد: {request.name}")
    if request.description is not None:
        lines.append(f"الوصف الجديد: {request.description or 'بدون وصف'}")
    if request.private is not None:
        lines.append(f"الظهور الجديد: {'🔒 خاص' if request.private else '🌐 عام'}")
    if request.visibility is not None:
        lines.append(f"الظهور الجديد: {request.visibility}")
    if request.archived is not None:
        lines.append(f"الحالة الجديدة: {'📦 مؤرشف' if request.archived else '🟢 نشط'}")
    if request.default_branch is not None:
        lines.append(f"الفرع الافتراضي الجديد: {request.default_branch}")
    return "\n".join(lines) or "لا توجد تغييرات"
