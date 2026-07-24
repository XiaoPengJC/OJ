import { apiRequest } from "./api.js";
import { escapeHtml, formatText, showError, sleep, translateResult, translateStatus } from "./utils.js";

export async function renderProblems(context) {
    context.title.textContent = "题目列表";
    context.content.innerHTML = "<p>正在加载题目...</p>";
    try {
        const response = await apiRequest("/api/problems");
        const problems = response.data;
        if (!problems.length) {
            context.content.innerHTML = "<p>当前暂无题目。</p>";
            return;
        }
        context.content.innerHTML = problems.map(problem => `
            <article class="problem-card" data-problem-id="${escapeHtml(problem.id)}">
                <h3>${escapeHtml(problem.id)}：${escapeHtml(problem.title)}</h3>
                <div class="problem-meta">
                    <span>难度：${escapeHtml(problem.difficulty)}</span>
                    <span>时间限制：${escapeHtml(problem.time_limit)} 秒</span>
                    <span>内存限制：${escapeHtml(problem.memory_limit)} MB</span>
                    ${(problem.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
                </div>
            </article>
        `).join("");

        context.content.querySelectorAll(".problem-card").forEach(card => {
            card.addEventListener("click", () => renderProblemDetail(context, card.dataset.problemId));
        });
    } catch (error) {
        showError(context.content, error);
    }
}

export async function renderProblemDetail(context, problemId) {
    context.title.textContent = "题目详情";
    context.content.innerHTML = "<p>正在加载题目详情...</p>";
    try {
        const response = await apiRequest(`/api/problems/${encodeURIComponent(problemId)}`);
        const problem = response.data;
        const samples = (problem.samples || []).map((sample, index) => `
            <div class="sample-block">
                <strong>样例 ${index + 1} 输入</strong>
                <pre>${escapeHtml(sample.input)}</pre>
                <strong>样例 ${index + 1} 输出</strong>
                <pre>${escapeHtml(sample.output)}</pre>
            </div>
        `).join("") || "<p>暂无公开样例。</p>";

        context.content.innerHTML = `
            <div class="content-toolbar"><button id="back-problems" class="secondary-button">返回题目列表</button></div>
            <h2>${escapeHtml(problem.id)}：${escapeHtml(problem.title)}</h2>
            <div class="problem-meta">
                <span>难度：${escapeHtml(problem.difficulty)}</span>
                <span>时间限制：${escapeHtml(problem.time_limit)} 秒</span>
                <span>内存限制：${escapeHtml(problem.memory_limit)} MB</span>
            </div>
            <section class="problem-section"><h3>题目描述</h3><p>${formatText(problem.description)}</p></section>
            <section class="problem-section"><h3>输入说明</h3><p>${formatText(problem.input_description)}</p></section>
            <section class="problem-section"><h3>输出说明</h3><p>${formatText(problem.output_description)}</p></section>
            <section class="problem-section"><h3>数据范围</h3><p>${formatText(problem.constraints)}</p></section>
            <section class="problem-section"><h3>公开样例</h3>${samples}</section>
            <section class="problem-section">
                <h3>提交 Python 代码</h3>
                <form id="submission-form">
                    <textarea id="source-code" spellcheck="false" required placeholder="请在此输入 Python 代码..."></textarea>
                    <button id="submit-code-button" type="submit">提交代码</button>
                </form>
                <p id="submission-message" class="message"></p>
            </section>
        `;
        context.content.querySelector("#back-problems").addEventListener("click", () => renderProblems(context));
        context.content.querySelector("#submission-form").addEventListener("submit", event => submitSolution(context, event, problem.id));
    } catch (error) {
        showError(context.content, error);
    }
}

async function submitSolution(context, event, problemId) {
    event.preventDefault();
    const sourceCode = context.content.querySelector("#source-code").value;
    const message = context.content.querySelector("#submission-message");
    const button = context.content.querySelector("#submit-code-button");
    message.className = "message status-pending";
    message.textContent = "正在提交...";
    button.disabled = true;

    try {
        const response = await apiRequest("/api/submissions", {
            method: "POST",
            body: JSON.stringify({ problem_id: problemId, language: "python", source_code: sourceCode }),
        });
        const submissionId = response.data.submission_id;
        message.innerHTML = `提交成功。提交编号：<code>${escapeHtml(submissionId)}</code><br>当前状态：等待评测`;
        await pollSubmission(message, submissionId);
        message.innerHTML += `<br><button id="open-submission" type="button">查看提交详情</button>`;
        message.querySelector("#open-submission").addEventListener("click", () => context.openSubmission(submissionId));
    } catch (error) {
        message.className = "message status-error";
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}

async function pollSubmission(message, submissionId) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
        await sleep(500);
        const response = await apiRequest(`/api/submissions/${encodeURIComponent(submissionId)}`);
        const submission = response.data;
        if (submission.status === "pending" || submission.status === "running") {
            message.className = "message status-pending";
            message.textContent = `提交编号：${submissionId}\n当前状态：${translateStatus(submission.status)}`;
            continue;
        }
        message.className = submission.result === "AC" ? "message status-accepted" : "message status-error";
        message.innerHTML = `提交编号：<code>${escapeHtml(submissionId)}</code><br>状态：${escapeHtml(translateStatus(submission.status))}<br>结果：${escapeHtml(translateResult(submission.result))}<br>得分：${escapeHtml(submission.score)}<br>总运行时间：${escapeHtml(submission.total_time ?? 0)} 秒`;
        return;
    }
    message.textContent = "评测时间较长，请前往提交记录页面手动刷新。";
}
