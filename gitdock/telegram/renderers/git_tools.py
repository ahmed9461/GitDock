"""Arabic renderers for P4.2 branch/commit tools."""

from __future__ import annotations

from gitdock.github.git_tools import BranchSnapshot, CommitDetail
from gitdock.services.git_tools import (
    BranchCreateOutcome,
    BranchCreatePlan,
    BranchCreateState,
    BranchListView,
    CommitListView,
    CompareView,
)


def render_branches(view: BranchListView, *, query: str | None = None) -> str:
    lines = [f"🌿 الفروع — {view.repository_full_name}", f"الافتراضي: {view.default_branch}"]
    if query:
        lines.append(f"البحث: {query}")
    lines.append("")
    if not view.branches:
        lines.append("لا توجد فروع مطابقة.")
    else:
        lines.append(f"عدد الفروع: {len(view.branches)}")
        lines.append("")
        for branch in view.branches[:24]:
            marker = " 🔒" if branch.protected else ""
            lines.append(f"• {branch.name}{marker} — {branch.sha[:7]}")
        if len(view.branches) > 24:
            lines.append(f"… و{len(view.branches) - 24} فروع أخرى")
    return "\n".join(lines)


def render_branch(branch: BranchSnapshot) -> str:
    protected = "نعم" if branch.protected else "لا"
    return (
        "🌿 تفاصيل الفرع\n\n"
        f"الاسم: {branch.name}\n"
        f"SHA: {branch.sha}\n"
        f"محمي: {protected}"
    )


def render_commits(view: CommitListView) -> str:
    return (
        f"📝 آخر الـCommits — {view.repository_full_name}\n"
        f"🌿 المرجع: {view.ref}\n\n"
        f"المعروض: {len(view.commits)}"
    )


def render_commit(detail: CommitDetail) -> str:
    message = detail.message.strip().splitlines()[0][:300]
    return (
        "📝 تفاصيل Commit\n\n"
        f"SHA: {detail.sha}\n"
        f"الكاتب: {detail.author_name}\n"
        f"التاريخ: {detail.authored_at:%Y-%m-%d %H:%M UTC}\n"
        f"الرسالة: {message}\n\n"
        f"الملفات: {detail.changed_files}\n"
        f"+{detail.additions} / -{detail.deletions}\n"
        f"Parents: {len(detail.parents)}"
    )


def render_branch_plan(plan: BranchCreatePlan) -> str:
    return (
        "✅ مراجعة إنشاء الفرع\n\n"
        f"📦 {plan.repository_full_name}\n"
        f"🌿 الفرع الجديد: {plan.branch}\n"
        f"الأساس: {plan.base_ref}\n"
        f"Base SHA: {plan.base_sha}\n\n"
        "لن يتم إنشاء أي ref في GitHub حتى التأكيد.\n"
        "إذا تحرك base قبل التأكيد ستتوقف العملية كـ stale."
    )


def render_branch_outcome(outcome: BranchCreateOutcome) -> str:
    if outcome.state is BranchCreateState.APPLIED:
        return f"✅ تم إنشاء الفرع {outcome.branch}\nSHA: {outcome.sha}"
    if outcome.state is BranchCreateState.STALE:
        return "⚠️ تغيّر الـbase بعد المراجعة. لم يتم إنشاء الفرع. أعد المراجعة من الحالة الحالية."
    if outcome.state is BranchCreateState.EXISTS:
        return f"ℹ️ الفرع {outcome.branch} موجود بالفعل. لم يتم استبدال أي ref."
    if outcome.state is BranchCreateState.UNCERTAIN:
        return (
            "⚠️ نتيجة إنشاء الفرع غير محسومة.\n"
            "لم تتم إعادة الطلب بشكل أعمى. حدّث قائمة الفروع للتحقق من GitHub."
        )
    return "ℹ️ انتهى أو استُخدم هذا التأكيد. لم يتم إنشاء فرع."


def render_compare(view: CompareView) -> str:
    comparison = view.comparison
    lines = [
        f"🔀 مقارنة — {view.repository_full_name}",
        f"{view.base} ← {view.head}",
        "",
        f"الحالة: {comparison.status}",
        f"Ahead: {comparison.ahead_by}",
        f"Behind: {comparison.behind_by}",
        f"Commits: {comparison.total_commits}",
        f"Files: {len(comparison.files)}",
    ]
    if comparison.files:
        lines.append("")
        for item in comparison.files[:10]:
            lines.append(f"• {item.filename} ({item.status}) +{item.additions}/-{item.deletions}")
        if len(comparison.files) > 10:
            lines.append(f"… و{len(comparison.files) - 10} ملفات أخرى")
    return "\n".join(lines)
