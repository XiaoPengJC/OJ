import { apiRequest } from "./api.js";
import { escapeHtml, formatDate, showError } from "./utils.js";

export async function renderBackups(context) {
    context.title.textContent = "备份与恢复";
    context.content.innerHTML = "<p>正在加载备份记录...</p>";
    try {
        const response = await apiRequest("/api/admin/backups");
        const backups = response.data;
        context.content.innerHTML = `
            <div class="content-toolbar"><button id="create-backup">创建备份</button></div>
            <p id="backup-message" class="message"></p>
            ${backups.length ? `<div class="table-wrapper"><table><thead><tr><th>备份编号</th><th>创建时间</th><th>操作</th></tr></thead><tbody>${backups.map(item => `
                <tr><td><code>${escapeHtml(item.backup_id)}</code></td><td>${escapeHtml(formatDate(item.created_at))}</td><td><button class="restore-backup danger-button" data-id="${escapeHtml(item.backup_id)}">恢复此备份</button></td></tr>
            `).join("")}</tbody></table></div>` : "<p>暂无备份。</p>"}
        `;
        context.content.querySelector("#create-backup").addEventListener("click", () => createBackup(context));
        context.content.querySelectorAll(".restore-backup").forEach(button => button.addEventListener("click", () => restoreBackup(context, button.dataset.id)));
    } catch (error) {
        showError(context.content, error);
    }
}

async function createBackup(context) {
    const message = context.content.querySelector("#backup-message");
    message.className = "message status-pending";
    message.textContent = "正在创建一致性备份...";
    try {
        const response = await apiRequest("/api/admin/backups", { method: "POST" });
        message.className = "message status-accepted";
        message.textContent = `备份创建成功：${response.data.backup_id}`;
        await renderBackups(context);
    } catch (error) {
        message.className = "message status-error";
        message.textContent = error.message;
    }
}

async function restoreBackup(context, backupId) {
    if (!window.confirm("恢复将覆盖当前数据库，并使当前登录会话失效。确定继续吗？")) return;
    const message = context.content.querySelector("#backup-message");
    message.className = "message status-pending";
    message.textContent = "正在校验并恢复备份...";
    try {
        await apiRequest(`/api/admin/backups/${encodeURIComponent(backupId)}/restore`, { method: "POST" });
        window.alert("备份恢复成功。请重新登录。");
        context.onSessionExpired();
    } catch (error) {
        message.className = "message status-error";
        message.textContent = error.message;
    }
}
