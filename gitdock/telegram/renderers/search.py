"""Arabic-first renderers for public GitHub repository search."""

from __future__ import annotations

from datetime import UTC, datetime

from gitdock.github.search import RepositorySearchResult
from gitdock.services.search import SearchCriteria, SearchResultPage, SearchSort

_SORT_LABELS = {
    SearchSort.BEST_MATCH: "الأكثر صلة",
    SearchSort.STARS: "الأكثر نجومًا",
    SearchSort.UPDATED: "آخر تحديث",
}


def render_search_prompt() -> str:
    return (
        "🔎 البحث في GitHub\n\n"
        "أرسل اسم المشروع أو الفكرة التي تريد البحث عنها.\n"
        "يمكنك بعد ظهور النتائج الفرز والتصفية حسب اللغة والنجوم والمالك وTopic."
    )


def render_search_results(page: SearchResultPage) -> str:
    criteria = page.criteria
    lines = [
        f"🔎 نتائج: {_truncate(criteria.query, 80)}",
        "",
        f"الترتيب: {_SORT_LABELS[criteria.sort]}",
        f"الفلاتر: {_criteria_summary(criteria)}",
        "",
    ]
    if not page.items:
        lines.extend(["لا توجد نتائج مطابقة.", "", "غيّر عبارة البحث أو الفلاتر وحاول من جديد."])
    else:
        for index, repository in enumerate(page.items, start=1):
            archive = " • 📦 مؤرشف" if repository.archived else ""
            fork = " • 🍴 Fork" if repository.fork else ""
            lines.extend(
                [
                    f"{index}) {repository.full_name}{archive}{fork}",
                    (
                        f"   ⭐ {repository.stars} • 🍴 {repository.forks} • "
                        f"{repository.language or '—'}"
                    ),
                    (
                        f"   {repository.license_spdx or 'بدون License محددة'} • "
                        f"{_relative(repository.updated_at)}"
                    ),
                ]
            )
            if repository.description:
                lines.append(f"   {_truncate(repository.description, 120)}")
            lines.append("")
    lines.append(f"الصفحة {page.page} من {page.total_pages} • النتائج {page.total_items}")
    if page.incomplete_results:
        lines.append("⚠️ GitHub أشار إلى أن نتيجة البحث غير مكتملة مؤقتًا.")
    return "\n".join(lines).rstrip()


def render_search_detail(repository: RepositorySearchResult) -> str:
    archived = "📦 مؤرشف" if repository.archived else "🟢 نشط"
    source = "🍴 Fork" if repository.fork else "🌿 مصدر"
    topics = ", ".join(repository.topics[:8]) if repository.topics else "—"
    description = _truncate(repository.description, 350) if repository.description else "—"
    return (
        f"📦 {repository.full_name}\n"
        f"🌐 عام • {archived} • {source}\n\n"
        f"🌿 الفرع الافتراضي: {repository.default_branch}\n"
        f"🧩 اللغة: {repository.language or '—'}\n"
        f"⭐ {repository.stars}   🍴 {repository.forks}\n"
        f"📄 License: {repository.license_spdx or '—'}\n"
        f"🏷 Topics: {topics}\n"
        f"🕒 آخر تحديث: {_relative(repository.updated_at)}\n\n"
        f"📝 الوصف:\n{description}"
    )


def render_search_filters(criteria: SearchCriteria) -> str:
    return (
        "🎛 تصفية بحث GitHub\n\n"
        f"🧩 اللغة: {criteria.language.value if criteria.language else 'الكل'}\n"
        f"⭐ الحد الأدنى: {criteria.min_stars if criteria.min_stars is not None else 'بدون'}\n"
        f"👤 المالك/المنظمة: {criteria.owner_scope or 'بدون'}\n"
        f"🏷 Topic: {criteria.topic or 'بدون'}\n"
        f"📦 المؤرشف: {'يظهر' if criteria.include_archived else 'مخفي'}\n\n"
        "عدّل الفلاتر ثم اضغط تطبيق."
    )


def render_min_stars_prompt() -> str:
    return "⭐ الحد الأدنى للنجوم\n\nأرسل رقمًا صحيحًا مثل: 1000\nأرسل 0 لإزالة الحد."


def render_owner_prompt() -> str:
    return (
        "👤 المالك أو المنظمة\n\n"
        "أرسل أحد الشكلين:\n"
        "user:octocat\n"
        "org:github\n\n"
        "أرسل - لإزالة هذا الفلتر."
    )


def render_topic_prompt() -> str:
    return "🏷 Topic\n\nأرسل اسم Topic مثل: machine-learning\nأرسل - لإزالة هذا الفلتر."


def render_search_validation_error(message: str) -> str:
    return f"⚠️ قيمة البحث غير صالحة.\n{message}"


def render_search_expired() -> str:
    return (
        "⚠️ انتهت جلسة البحث أو تم بدء بحث أحدث.\n"
        "ابدأ بحثًا جديدًا حتى لا يتم تفسير زر قديم على نتائج مختلفة."
    )


def _criteria_summary(criteria: SearchCriteria) -> str:
    values: list[str] = []
    if criteria.language:
        values.append(criteria.language.value)
    if criteria.min_stars is not None:
        values.append(f"⭐≥{criteria.min_stars}")
    if criteria.owner_scope:
        values.append(criteria.owner_scope)
    if criteria.topic:
        values.append(f"#{criteria.topic}")
    if not criteria.include_archived:
        values.append("بدون المؤرشف")
    return " • ".join(values) if values else "بدون"


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
