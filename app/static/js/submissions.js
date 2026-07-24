import { apiRequest } from "./api.js";
import {
    buildQuery,
    escapeHtml,
    formatDate,
    resultClass,
    showError,
    sleep,
    translateResult,
    translateStatus,
} from "./utils.js";

export async function renderSubmissions(context, page = 1, filters = {}) {
    context.title.textContent = context.currentUser.role === "student" ? "我的提交记录" : "提交管理";
    context.content.innerHTML = "<p>正在加载提交记录...</p>";
    const isTeacher = ["teacher", "admin"].includes(context.currentUser.role);

    try {
        const query = buildQuery({ page, page_size: 20, ...filters });
        const response = await apiRequest(`/api/submissions${query}`);
        const data = response.data;
        const filterForm = `
            <form id="submission-filter-form" class="filter-form">
                <label>题目编号<input name="problem_id" value="${escapeHtml(filters.problem_id || "")}"></label>
                ${isTeacher ? `<label>用户编号<input name="user_id" value="${escapeHtml(filters.user_id || "")}"></label>` : ""}
                <label>状态<select name="status">
                    ${option("", "全部状态", filters.status)}
                    ${option("pending", "等待评测", filters.status)}
                    ${option("running", "正在评测", filters.status)}
                    ${option("finished", "评测完成", filters.status)}
                    ${option("failed", "评测失败", filters.status)}
                </select></label>
                <label>结果<select name="result">
                    ${option("", "全部结果", filters.result)}
                    ${["AC", "WA", "RE", "TLE", "SE"].map(value => option(value, value, filters.result)).join("")}
                </select></label>
                <button type="submit">筛选</button>
                <button id="clear-submission-filters" type="button" class="secondary-button">清空</button>
            </form>
        `;

        const rows = data.items.map(item => `
            <tr class="submission-row" data-id="${escapeHtml(item.id)}">
                <td><code>${escapeHtml(item.id)}</code></td>
                ${isTeacher ? `<td><code>${escapeHtml(item.user_id)}</code></td>` : ""}
                <td>${escapeHtml(item.problem_id)}</td>
                <td>${escapeHtml(formatDate(item.created_at))}</td>
                <td>${escapeHtml(translateStatus(item.status))}</td>
                <td class="${resultClass(item.result, item.status)}">${escapeHtml(translateResult(item.result))}</td>
                <td>${escapeHtml(item.score)}</td>
            </tr>
        `).join("");

        context.content.innerHTML = `
            ${filterForm}
            ${data.items.length ? `
                <div class="table-wrapper"><table>
                    <thead><tr><th>提交编号</th>${isTeacher ? "<th>用户编号</th>" : ""}<th>题目</th><th>提交时间</th><th>状态</th><th>结果</th><th>得分</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table></div>
            ` : "<p>当前筛选条件下暂无提交记录。</p>"}
            ${paginationHtml(data)}
        `;

        context.content.querySelector("#submission-filter-form").addEventListener("submit", event => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            const nextFilters = Object.fromEntries(formData.entries());
            renderSubmissions(context, 1, nextFilters);
        });
        context.content.querySelector("#clear-submission-filters").addEventListener("click", () => renderSubmissions(context));
        context.content.querySelectorAll(".submission-row").forEach(row => {
            row.addEventListener("click", () => renderSubmissionDetail(context, row.dataset.id));
        });
        context.content.querySelectorAll("[data-page]").forEach(button => {
            button.addEventListener("click", () => renderSubmissions(context, Number(button.dataset.page), filters));
        });
    } catch (error) {
        showError(context.content, error);
    }
}

export async function renderSubmissionDetail(context, submissionId) {
    context.title.textContent = "提交详情";
    context.content.innerHTML = "<p>正在加载提交详情和评测日志...</p>";
    const canRejudge = ["teacher", "admin"].includes(context.currentUser.role);

    try {
        const [submissionResponse, logsResponse] = await Promise.all([
            apiRequest(`/api/submissions/${encodeURIComponent(submissionId)}`),
            apiRequest(`/api/submissions/${encodeURIComponent(submissionId)}/logs`),
        ]);
        const submission = submissionResponse.data;
        const logs = logsResponse.data;
        const rejudgeButton = canRejudge && ["finished", "failed"].includes(submission.status)
            ? `<button id="rejudge-button" class="danger-button">重新评测</button>`
            : "";

        context.content.innerHTML = `
            <div class="content-toolbar">
                <button id="back-submissions" class="secondary-button">返回提交记录</button>
                ${rejudgeButton}
            </div>
            <div class="submission-summary">
                ${summary("提交编号", `<code>${escapeHtml(submission.id)}</code>`)}
                ${summary("题目编号", escapeHtml(submission.problem_id))}
                ${summary("用户编号", `<code>${escapeHtml(submission.user_id)}</code>`)}
                ${summary("状态", escapeHtml(translateStatus(submission.status)))}
                ${summary("结果", `<span class="${resultClass(submission.result, submission.status)}">${escapeHtml(translateResult(submission.result))}</span>`)}
                ${summary("得分", escapeHtml(submission.score))}
                ${summary("总运行时间", `${escapeHtml(submission.total_time ?? "-")} 秒`)}
                ${summary("提交时间", escapeHtml(formatDate(submission.created_at)))}
            </div>
            <h3>源代码</h3><pre>${escapeHtml(submission.source_code)}</pre>
            <h3>测试点日志</h3>
            <div id="log-list">${logs.length ? logs.map(renderLog).join("") : "<p>暂无测试点日志，评测可能仍在进行。</p>"}</div>
            <p id="rejudge-message" class="message"></p>
        `;

        context.content.querySelector("#back-submissions").addEventListener("click", () => renderSubmissions(context));
        const rejudge = context.content.querySelector("#rejudge-button");
        if (rejudge) {
            rejudge.addEventListener("click", () => rejudgeSubmission(context, submissionId));
        }
    } catch (error) {
        showError(context.content, error);
    }
}

async function rejudgeSubmission(context, submissionId) {
    const message = context.content.querySelector("#rejudge-message");
    message.className = "message status-pending";
    message.textContent = "已发起重新评测...";
    try {
        await apiRequest(`/api/submissions/${encodeURIComponent(submissionId)}/rejudge`, { method: "POST" });
        for (let attempt = 0; attempt < 60; attempt += 1) {
            await sleep(500);
            const response = await apiRequest(`/api/submissions/${encodeURIComponent(submissionId)}`);
            if (["pending", "running"].includes(response.data.status)) {
                message.textContent = `重新评测中：${translateStatus(response.data.status)}`;
                continue;
            }
            await renderSubmissionDetail(context, submissionId);
            return;
        }
        message.textContent = "重新评测仍在进行，请稍后刷新。";
    } catch (error) {
        message.className = "message status-error";
        message.textContent = error.message;
    }
}

function renderLog(log) {
    const input = log.input_data !== undefined ? `<strong>输入数据</strong><pre>${escapeHtml(log.input_data)}</pre>` : "";
    const stdout = log.stdout !== undefined ? `<strong>程序输出</strong><pre>${escapeHtml(log.stdout)}</pre>` : "";
    const expected = log.expected_output !== undefined ? `<strong>标准输出</strong><pre>${escapeHtml(log.expected_output)}</pre>` : "";
    const stderr = log.stderr ? `<strong>错误信息</strong><pre>${escapeHtml(log.stderr)}</pre>` : "";
    const hidden = log.is_hidden !== undefined ? `<p>隐藏测试点：${log.is_hidden ? "是" : "否"}</p>` : "";
    const exitCode = log.exit_code !== undefined ? `<p>退出码：${escapeHtml(log.exit_code ?? "-")}</p>` : "";
    return `
        <article class="case-card">
            <h4>测试点：${escapeHtml(log.case_id)}</h4>
            <p>结果：<span class="${resultClass(log.result, "finished")}">${escapeHtml(translateResult(log.result))}</span></p>
            <p>得分：${escapeHtml(log.score)}；运行时间：${escapeHtml(log.time_used)} 秒</p>
            <p>评测信息：${escapeHtml(log.message)}</p>
            ${hidden}${exitCode}${input}${stdout}${expected}${stderr}
        </article>
    `;
}

function option(value, label, selected) {
    return `<option value="${escapeHtml(value)}" ${value === (selected || "") ? "selected" : ""}>${escapeHtml(label)}</option>`;
}

function summary(label, value) {
    return `<div class="summary-card"><strong>${escapeHtml(label)}</strong>${value}</div>`;
}

function paginationHtml(data) {
    const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
    if (totalPages <= 1) return `<p class="muted">共 ${data.total} 条记录</p>`;
    return `<div class="pagination">
        <button data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""}>上一页</button>
        <span>第 ${data.page} / ${totalPages} 页，共 ${data.total} 条</span>
        <button data-page="${data.page + 1}" ${data.page >= totalPages ? "disabled" : ""}>下一页</button>
    </div>`;
}
