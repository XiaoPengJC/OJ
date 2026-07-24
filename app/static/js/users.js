import { apiRequest } from "./api.js";
import { escapeHtml, formatDate, showError, translateRole } from "./utils.js";

export async function renderUsers(context, page = 1) {
    context.title.textContent = "用户管理";
    context.content.innerHTML = "<p>正在加载用户...</p>";
    try {
        const response = await apiRequest(`/api/users?page=${page}&page_size=20`);
        const data = response.data;
        context.content.innerHTML = `
            <details class="management-panel"><summary>创建用户</summary>
                <form id="create-user-form" class="form-grid">
                    <label>用户名<input name="username" minlength="3" maxlength="32" required></label>
                    <label>密码<input name="password" type="password" minlength="8" required></label>
                    <label>角色<select name="role"><option value="student">学生</option><option value="teacher">教师</option><option value="admin">管理员</option></select></label>
                    <button type="submit">创建用户</button>
                </form><p id="create-user-message" class="message"></p>
            </details>
            <div class="table-wrapper"><table>
                <thead><tr><th>用户名</th><th>角色</th><th>启用</th><th>创建时间</th><th>操作</th></tr></thead>
                <tbody>${data.items.map(userRow).join("")}</tbody>
            </table></div>
            ${pagination(data)}
        `;

        context.content.querySelector("#create-user-form").addEventListener("submit", event => createUser(context, event));
        context.content.querySelectorAll(".save-user-button").forEach(button => {
            button.addEventListener("click", () => updateUser(context, button.dataset.id));
        });
        context.content.querySelectorAll("[data-page]").forEach(button => {
            button.addEventListener("click", () => renderUsers(context, Number(button.dataset.page)));
        });
    } catch (error) {
        showError(context.content, error);
    }
}

function userRow(user) {
    return `<tr data-user-id="${escapeHtml(user.id)}">
        <td><strong>${escapeHtml(user.username)}</strong><br><code>${escapeHtml(user.id)}</code></td>
        <td><select class="user-role"><option value="student" ${user.role === "student" ? "selected" : ""}>学生</option><option value="teacher" ${user.role === "teacher" ? "selected" : ""}>教师</option><option value="admin" ${user.role === "admin" ? "selected" : ""}>管理员</option></select></td>
        <td><input class="user-active" type="checkbox" ${user.is_active ? "checked" : ""}></td>
        <td>${escapeHtml(formatDate(user.created_at))}</td>
        <td><button class="save-user-button" data-id="${escapeHtml(user.id)}">保存</button><p class="row-message message"></p></td>
    </tr>`;
}

async function createUser(context, event) {
    event.preventDefault();
    const form = event.currentTarget;
    const message = context.content.querySelector("#create-user-message");
    const data = Object.fromEntries(new FormData(form).entries());
    try {
        await apiRequest("/api/users", { method: "POST", body: JSON.stringify(data) });
        message.className = "message status-accepted";
        message.textContent = "用户创建成功。";
        form.reset();
        await renderUsers(context);
    } catch (error) {
        message.className = "message status-error";
        message.textContent = error.message;
    }
}

async function updateUser(context, userId) {
    const row = context.content.querySelector(`[data-user-id="${CSS.escape(userId)}"]`);
    const message = row.querySelector(".row-message");
    const body = {
        role: row.querySelector(".user-role").value,
        is_active: row.querySelector(".user-active").checked,
    };
    try {
        const response = await apiRequest(`/api/users/${encodeURIComponent(userId)}`, { method: "PUT", body: JSON.stringify(body) });
        message.className = "row-message message status-accepted";
        message.textContent = `已保存：${translateRole(response.data.role)} / ${response.data.is_active ? "启用" : "禁用"}`;
    } catch (error) {
        message.className = "row-message message status-error";
        message.textContent = error.message;
    }
}

function pagination(data) {
    const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
    return `<div class="pagination"><button data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""}>上一页</button><span>第 ${data.page} / ${totalPages} 页，共 ${data.total} 名用户</span><button data-page="${data.page + 1}" ${data.page >= totalPages ? "disabled" : ""}>下一页</button></div>`;
}
