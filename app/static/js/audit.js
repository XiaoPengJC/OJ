import { apiRequest } from "./api.js";
import { buildQuery, escapeHtml, formatDate, showError } from "./utils.js";

export async function renderAuditLogs(context, page = 1, filters = {}) {
    context.title.textContent = "审计日志";
    context.content.innerHTML = "<p>正在加载审计日志...</p>";
    try {
        const response = await apiRequest(`/api/audit-logs${buildQuery({ page, page_size: 20, ...filters })}`);
        const data = response.data;
        context.content.innerHTML = `
            <form id="audit-filter-form" class="filter-form">
                <label>操作者编号<input name="operator_id" value="${escapeHtml(filters.operator_id || "")}"></label>
                <label>动作<input name="action" value="${escapeHtml(filters.action || "")}"></label>
                <label>目标编号<input name="target_id" value="${escapeHtml(filters.target_id || "")}"></label>
                <button type="submit">筛选</button><button id="clear-audit" type="button" class="secondary-button">清空</button>
            </form>
            ${data.items.length ? `<div class="table-wrapper"><table><thead><tr><th>时间</th><th>操作者</th><th>动作</th><th>目标</th><th>成功</th><th>详情</th></tr></thead><tbody>${data.items.map(log => `
                <tr><td>${escapeHtml(formatDate(log.created_at))}</td><td><code>${escapeHtml(log.operator_id)}</code></td><td>${escapeHtml(log.action)}</td><td>${escapeHtml(log.target_type)} / <code>${escapeHtml(log.target_id)}</code></td><td>${log.success ? "是" : "否"}</td><td><pre>${escapeHtml(JSON.stringify(log.detail, null, 2))}</pre></td></tr>
            `).join("")}</tbody></table></div>` : "<p>暂无审计日志。</p>"}
            ${pagination(data)}
        `;
        context.content.querySelector("#audit-filter-form").addEventListener("submit", event => {
            event.preventDefault();
            renderAuditLogs(context, 1, Object.fromEntries(new FormData(event.currentTarget).entries()));
        });
        context.content.querySelector("#clear-audit").addEventListener("click", () => renderAuditLogs(context));
        context.content.querySelectorAll("[data-page]").forEach(button => button.addEventListener("click", () => renderAuditLogs(context, Number(button.dataset.page), filters)));
    } catch (error) {
        showError(context.content, error);
    }
}

function pagination(data) {
    const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
    return `<div class="pagination"><button data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""}>上一页</button><span>第 ${data.page} / ${totalPages} 页，共 ${data.total} 条</span><button data-page="${data.page + 1}" ${data.page >= totalPages ? "disabled" : ""}>下一页</button></div>`;
}
