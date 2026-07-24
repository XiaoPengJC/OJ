export function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

export function formatText(value) {
    return escapeHtml(value).replaceAll("\n", "<br>");
}

export function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

export function sleep(milliseconds) {
    return new Promise(resolve => setTimeout(resolve, milliseconds));
}

export function translateRole(role) {
    return { student: "学生", teacher: "教师", admin: "管理员" }[role] || role;
}

export function translateStatus(status) {
    return {
        pending: "等待评测",
        running: "正在评测",
        finished: "评测完成",
        failed: "评测失败",
    }[status] || status || "未知";
}

export function translateResult(result) {
    return {
        AC: "答案正确",
        WA: "答案错误",
        RE: "运行错误",
        TLE: "超出时间限制",
        SE: "系统错误",
    }[result] || result || "-";
}

export function resultClass(result, status) {
    if (result === "AC") return "status-accepted";
    if (status === "pending" || status === "running") return "status-pending";
    return "status-error";
}

export function showError(container, error) {
    const message = error?.message || String(error || "未知错误");
    container.innerHTML = `<p class="error-message">${escapeHtml(message)}</p>`;
}

export function buildQuery(parameters) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(parameters)) {
        if (value !== undefined && value !== null && value !== "") {
            query.set(key, value);
        }
    }
    const text = query.toString();
    return text ? `?${text}` : "";
}
