"""Arabic-first GitHub account and user-authorization renderers."""

from __future__ import annotations

from datetime import UTC, datetime

from gitdock.services.user_authorization import (
    DisconnectRequest,
    DisconnectResult,
    DisconnectState,
    UserAuthorizationStatus,
)


def render_account(status: UserAuthorizationStatus) -> str:
    if status.authorized:
        refresh_state = "✅ متاح" if status.refresh_available else "⚠️ غير متاح"
        return (
            "👤 حساب GitHub\n\n"
            f"المستخدم: {status.login or '—'}\n"
            "✅ صلاحية المستخدم: مفعلة\n"
            f"🔗 تثبيتات GitHub App المحلية: {status.installation_count}\n"
            f"🔄 التجديد الآمن: {refresh_state}\n"
            f"⏳ انتهاء Access Token: {_expiry(status.access_expires_at)}\n"
            f"🗓 انتهاء Refresh Token: {_expiry(status.refresh_expires_at)}\n\n"
            "الرموز السرية محفوظة مشفرة ولا تظهر داخل Telegram."
        )

    if status.installation_count > 0:
        return (
            "👤 حساب GitHub\n\n"
            "🔗 GitHub App مرتبط محليًا بالمستودعات.\n"
            "⚠️ صلاحية المستخدم الدائمة غير مفعلة بعد.\n"
            f"تثبيتات GitHub App المحلية: {status.installation_count}\n\n"
            "فعّل صلاحية المستخدم للميزات التي تحتاج تنفيذًا باسم حسابك، "
            "بدون إعادة تثبيت GitHub App."
        )

    return (
        "👤 حساب GitHub\n\n"
        "لا توجد صلاحية مستخدم أو تثبيت GitHub App مرتبط محليًا الآن.\n"
        "يمكن بدء الربط من الصفحة الرئيسية."
    )


def render_authorization_ready() -> str:
    return (
        "🔐 صلاحية مستخدم GitHub\n\n"
        "تم إنشاء جلسة تفويض قصيرة الصلاحية باستخدام PKCE.\n"
        "افتح GitHub من الزر أدناه وأكمل التفويض، ثم ارجع إلى البوت.\n\n"
        "لن يطلب GitDock منك لصق Token داخل Telegram."
    )


def render_disconnect_confirmation(request: DisconnectRequest) -> str:
    return (
        "⚠️ تأكيد قطع الربط المحلي\n\n"
        f"الحساب/التثبيت: {request.account_login}\n"
        f"تثبيتات محلية ستزال: {request.installation_count}\n\n"
        "سيقوم GitDock بـ:\n"
        "• حذف رموز المستخدم المشفرة من قاعدة بيانات GitDock.\n"
        "• حذف روابط GitHub App المحلية وذاكرة المستودعات المؤقتة.\n"
        "• إلغاء جلسات التفويض غير المكتملة.\n\n"
        "لن يقوم هذا بإلغاء تثبيت GitHub App من حسابك في موقع GitHub.\n"
        "أي زر تأكيد قديم يصبح غير صالح إذا تغيرت حالة الربط."
    )


def render_disconnect_result(result: DisconnectResult) -> str:
    if result.state is DisconnectState.DISCONNECTED:
        return (
            "✅ تم قطع الربط المحلي\n\n"
            f"الحساب: {result.account_login or '—'}\n"
            f"التثبيتات المحلية المحذوفة: {result.installations_removed}\n\n"
            "تم حذف بيانات التفويض المحلية بأمان.\n"
            "GitHub App لم يُلغَ تثبيته من موقع GitHub."
        )
    if result.state is DisconnectState.STALE:
        return (
            "⚠️ تغيرت حالة ربط GitHub منذ شاشة التأكيد.\n"
            "لم يتم حذف أي ربط أو رمز. افتح حساب GitHub وراجع الحالة من جديد."
        )
    return (
        "⚠️ انتهى هذا التأكيد أو تم استخدامه/إلغاؤه سابقًا.\n"
        "لم يتم حذف أي شيء. افتح حساب GitHub وابدأ العملية من جديد إذا لزم."
    )


def render_reauthorization_required() -> str:
    return (
        "⚠️ تحتاج صلاحية المستخدم إلى تفويض جديد من GitHub.\n"
        "لم يتم عرض أو حذف أي رمز سري. استخدم زر إعادة التفويض للمتابعة."
    )


def render_authorization_changed() -> str:
    return (
        "⚠️ تغيرت حالة التفويض أثناء التحديث.\n"
        "لم يتم استبدال الحالة الأحدث. افتح حساب GitHub وحدّثه من جديد."
    )


def render_authorization_error() -> str:
    return (
        "⚠️ تعذر تحديث صلاحية مستخدم GitHub الآن.\n"
        "لم يتم عرض أي بيانات سرية. حاول مجددًا أو أعد التفويض."
    )


def _expiry(value: datetime | None) -> str:
    if value is None:
        return "غير محدد"
    current = datetime.now(UTC)
    timestamp = value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
    seconds = int((timestamp - current).total_seconds())
    if seconds <= 0:
        return "منتهٍ"
    minutes = seconds // 60
    if minutes < 60:
        return f"بعد {max(minutes, 1)} د"
    hours = minutes // 60
    if hours < 48:
        return f"بعد {hours} س"
    return f"بعد {hours // 24} يوم"
