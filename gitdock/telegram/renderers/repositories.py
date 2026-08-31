"""Arabic-first P2.3 Telegram renderers."""

from __future__ import annotations

from datetime import UTC, datetime

from gitdock.github.errors import GitHubErrorKind, GitHubGatewayError
from gitdock.github.repositories import RepositorySnapshot
from gitdock.services.repositories import HomeStatus, RepositoryFilter, RepositoryListPage

FILTER_LABELS = {
    RepositoryFilter.ALL: "الكل",
    RepositoryFilter.PRIVATE: "خاص",
    RepositoryFilter.PUBLIC: "عام",
    RepositoryFilter.ACTIVE: "نشط",
    RepositoryFilter.ARCHIVED: "مؤرشف",
    RepositoryFilter.SOURCE: "مصدر",
    RepositoryFilter.FORK: "Fork",
}


def render_home(status: HomeStatus) -> str:
    if not status.connected:
        return (
            "🐙 GitDock\n\n"
            "لم يتم ربط حساب GitHub بعد.\n"
            "اربط GitHub App لعرض المستودعات المتاحة لك بأمان."
        )
    return (
        "🐙 GitDock\n\n"
        "إدارة GitHub من تلجرام\n\n"
        f"👤 GitHub: {status.account_label or '—'}\n"
        f"📦 المستودعات: {status.repository_count}\n"
        "🔔 التنبيهات: ستُفعّل في مرحلة Webhooks\n"
        "✅ الاتصال: سليم"
    )


def render_repository_list(page: RepositoryListPage) -> str:
    title = "📦 مستودعاتي"
    filter_label = FILTER_LABELS[page.repository_filter]
    if not page.items:
        return (
            f"{title}\n\n"
            f"لا توجد مستودعات ضمن التصفية: {filter_label}.\n\n"
            f"الصفحة {page.page} من {page.total_pages}"
        )

    lines = [title, "", f"التصفية: {filter_label}", ""]
    for index, repository in enumerate(page.items, start=1):
        visibility = "🔒" if repository.private else "🌐"
        state = " 📦" if repository.archived else ""
        language = repository.language or "—"
        fork = " • Fork" if repository.fork else ""
        lines.extend(
            [
                f"{index}) {visibility} {repository.name}{state}",
                (
                    f"   {language} • {repository.default_branch}{fork} • "
                    f"{_relative(repository.updated_at)}"
                ),
            ]
        )
        if not repository.private:
            lines.append(f"   ⭐ {repository.stars} • 🍴 {repository.forks}")
        lines.append("")
    lines.append(f"الصفحة {page.page} من {page.total_pages} • الإجمالي {page.total_items}")
    return "\n".join(lines).rstrip()


def render_repository_detail(repository: RepositorySnapshot) -> str:
    visibility = "🔒 خاص" if repository.private else "🌐 عام"
    archived = "📦 مؤرشف" if repository.archived else "🟢 نشط"
    source = "🍴 Fork" if repository.fork else "🌿 مصدر"
    description = _truncate(repository.description, 300) if repository.description else "—"
    return (
        f"📦 {repository.full_name}\n"
        f"{visibility} • {archived} • {source}\n\n"
        f"🌿 الفرع الافتراضي: {repository.default_branch}\n"
        f"🧩 اللغة: {repository.language or '—'}\n"
        f"⭐ {repository.stars}   🍴 {repository.forks}\n"
        f"🕒 آخر تحديث: {_relative(repository.updated_at)}\n\n"
        f"📝 الوصف:\n{description}"
    )


def render_filter_screen(current: RepositoryFilter) -> str:
    return (
        "🎛 تصفية المستودعات\n\n"
        f"التصفية الحالية: {FILTER_LABELS[current]}\n"
        "اختر نوع المستودعات التي تريد عرضها."
    )


def render_connection_info(can_connect: bool) -> str:
    if not can_connect:
        return (
            "\u2139\ufe0f ربط GitHub\n\n"
            "GitHub App أو رابط الخدمة العام غير مهيأ بالكامل على الخادم بعد.\n"
            "لن يطلب GitDock أي رمز وصول منك داخل Telegram."
        )
    return (
        "\u2139\ufe0f ربط GitHub\n\n"
        "يتم الربط عبر GitHub App وصفحة GitHub الرسمية.\n"
        "GitDock لا يطلب منك لصق PAT أو Token داخل Telegram، ولا يعرض الرموز السرية في المحادثة."
    )


def render_connection_ready() -> str:
    return (
        "🔗 ربط GitHub\n\n"
        "تم إنشاء جلسة ربط قصيرة الصلاحية.\n"
        "افتح GitHub من الزر أدناه وأكمل التثبيت والتحقق، ثم ارجع للبوت واضغط تحديث."
    )


def render_stale_selection() -> str:
    return (
        "⚠️ هذا الاختيار لم يعد صالحًا أو أن المستودع لم يعد ضمن التثبيت.\n"
        "حدّث قائمة المستودعات واختره من جديد."
    )


def render_github_error(error: GitHubGatewayError) -> str:
    messages = {
        GitHubErrorKind.AUTHENTICATION: "تعذر التحقق من اتصال GitHub. أعد الربط أو حدّث الصفحة.",
        GitHubErrorKind.PERMISSION: "صلاحية القراءة المطلوبة غير متاحة لهذا التثبيت.",
        GitHubErrorKind.NOT_FOUND: "المستودع لم يعد موجودًا أو لم يعد متاحًا لهذا التثبيت.",
        GitHubErrorKind.CONFLICT: "تغيرت حالة المورد في GitHub. حدّث البيانات وحاول مجددًا.",
        GitHubErrorKind.VALIDATION: "رفض GitHub طلب القراءة بسبب بيانات غير صالحة.",
        GitHubErrorKind.RATE_LIMITED: "وصل GitHub إلى حد الطلبات مؤقتًا. حاول بعد قليل.",
        GitHubErrorKind.TRANSIENT: "GitHub غير متاح مؤقتًا. أعد المحاولة بعد قليل.",
        GitHubErrorKind.UNEXPECTED: "تعذر قراءة بيانات GitHub الآن.",
    }
    return f"⚠️ {messages[error.kind]}"


def _relative(value: datetime, now: datetime | None = None) -> str:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    timestamp = value.astimezone(UTC)
    seconds = max(int((current - timestamp).total_seconds()), 0)
    if seconds < 60:
        return "الآن"
    minutes = seconds // 60
    if minutes < 60:
        return f"قبل {minutes} د"
    hours = minutes // 60
    if hours < 24:
        return f"قبل {hours} س"
    days = hours // 24
    return f"قبل {days} يوم"


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[: limit - 1]}…"
