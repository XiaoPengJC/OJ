import { apiRequest } from "./api.js";
import { escapeHtml, formatText, showError, sleep, translateResult, translateStatus } from "./utils.js";

function canManageProblems(context) {
    return context.currentUser && ["teacher", "admin"].includes(context.currentUser.role);
}

function difficultyText(value) {
    return { easy: "简单", medium: "中等", hard: "困难" }[value] || value;
}

export async function renderProblems(context) {
    context.title.textContent = "题目列表";
    context.content.innerHTML = "<p>正在加载题目...</p>";
    try {
        const response = await apiRequest("/api/problems");
        const problems = response.data;
        const managementButton = canManageProblems(context)
            ? '<button id="create-problem-button" type="button">新建题目</button>'
            : "";

        context.content.innerHTML = `
            <div class="content-toolbar">
                <span class="muted">共 ${problems.length} 道题目</span>
                ${managementButton}
            </div>
            <div id="problem-list">
                ${problems.length ? problems.map(problem => `
                    <article class="problem-card" data-problem-id="${escapeHtml(problem.id)}">
                        <div class="problem-card-heading">
                            <h3>${escapeHtml(problem.id)}：${escapeHtml(problem.title)}</h3>
                            ${canManageProblems(context) ? `
                                <div class="inline-actions">
                                    <button class="secondary-button edit-problem-button" type="button">编辑</button>
                                    <button class="danger-button delete-problem-button" type="button">删除</button>
                                </div>
                            ` : ""}
                        </div>
                        <div class="problem-meta">
                            <span>难度：${escapeHtml(difficultyText(problem.difficulty))}</span>
                            <span>时间限制：${escapeHtml(problem.time_limit)} 秒</span>
                            <span>内存限制：${escapeHtml(problem.memory_limit)} MB</span>
                            ${(problem.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
                        </div>
                    </article>
                `).join("") : "<p>当前暂无题目。</p>"}
            </div>
        `;

        context.content.querySelector("#create-problem-button")?.addEventListener("click", () => renderProblemForm(context));
        context.content.querySelectorAll(".problem-card").forEach(card => {
            card.addEventListener("click", () => renderProblemDetail(context, card.dataset.problemId));
            card.querySelector(".edit-problem-button")?.addEventListener("click", event => {
                event.stopPropagation();
                renderProblemForm(context, card.dataset.problemId);
            });
            card.querySelector(".delete-problem-button")?.addEventListener("click", event => {
                event.stopPropagation();
                deleteProblem(context, card.dataset.problemId);
            });
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

        const testCases = canManageProblems(context) && problem.test_cases
            ? `<section class="problem-section"><h3>测试点（教师/管理员可见）</h3>${problem.test_cases.map(testCase => `
                <div class="case-card">
                    <strong>${escapeHtml(testCase.case_id)}</strong>
                    <span class="tag">${testCase.is_hidden ? "隐藏" : "公开"}</span>
                    <span>分值：${escapeHtml(testCase.score)}</span>
                    <p><strong>输入</strong></p><pre>${escapeHtml(testCase.input)}</pre>
                    <p><strong>期望输出</strong></p><pre>${escapeHtml(testCase.output)}</pre>
                </div>
            `).join("")}</section>`
            : "";

        context.content.innerHTML = `
            <div class="content-toolbar">
                <button id="back-problems" class="secondary-button" type="button">返回题目列表</button>
                ${canManageProblems(context) ? `
                    <div class="inline-actions">
                        <button id="edit-problem" type="button">编辑题目</button>
                        <button id="delete-problem" class="danger-button" type="button">删除题目</button>
                    </div>
                ` : ""}
            </div>
            <h2>${escapeHtml(problem.id)}：${escapeHtml(problem.title)}</h2>
            <div class="problem-meta">
                <span>难度：${escapeHtml(difficultyText(problem.difficulty))}</span>
                <span>时间限制：${escapeHtml(problem.time_limit)} 秒</span>
                <span>内存限制：${escapeHtml(problem.memory_limit)} MB</span>
                ${(problem.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
            </div>
            <section class="problem-section"><h3>题目描述</h3><p>${formatText(problem.description)}</p></section>
            <section class="problem-section"><h3>输入说明</h3><p>${formatText(problem.input_description)}</p></section>
            <section class="problem-section"><h3>输出说明</h3><p>${formatText(problem.output_description)}</p></section>
            <section class="problem-section"><h3>数据范围</h3><p>${formatText(problem.constraints)}</p></section>
            <section class="problem-section"><h3>公开样例</h3>${samples}</section>
            ${testCases}
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
        context.content.querySelector("#edit-problem")?.addEventListener("click", () => renderProblemForm(context, problem.id));
        context.content.querySelector("#delete-problem")?.addEventListener("click", () => deleteProblem(context, problem.id));
        context.content.querySelector("#submission-form").addEventListener("submit", event => submitSolution(context, event, problem.id));
    } catch (error) {
        showError(context.content, error);
    }
}

async function renderProblemForm(context, problemId = null) {
    if (!canManageProblems(context)) return;
    context.title.textContent = problemId ? "编辑题目" : "新建题目";
    context.content.innerHTML = "<p>正在加载...</p>";

    let problem = {
        id: "", title: "", description: "", input_description: "", output_description: "",
        samples: [{ input: "", output: "" }], constraints: "", time_limit: 1,
        memory_limit: 128, difficulty: "easy", tags: [],
        test_cases: [{ case_id: "case_01", input: "", output: "", score: 100, is_hidden: false }],
    };
    if (problemId) {
        try {
            problem = (await apiRequest(`/api/problems/${encodeURIComponent(problemId)}`)).data;
        } catch (error) {
            showError(context.content, error);
            return;
        }
    }

    context.content.innerHTML = `
        <div class="content-toolbar"><button id="cancel-problem-form" class="secondary-button" type="button">返回题目列表</button></div>
        <form id="problem-form" class="problem-form">
            <div class="form-grid">
                <label>题目编号
                    <input id="problem-id" required maxlength="32" value="${escapeHtml(problem.id)}" ${problemId ? "readonly" : ""} placeholder="例如 P1001">
                </label>
                <label>标题
                    <input id="problem-title" required maxlength="100" value="${escapeHtml(problem.title)}">
                </label>
                <label>难度
                    <select id="problem-difficulty">
                        <option value="easy" ${problem.difficulty === "easy" ? "selected" : ""}>简单</option>
                        <option value="medium" ${problem.difficulty === "medium" ? "selected" : ""}>中等</option>
                        <option value="hard" ${problem.difficulty === "hard" ? "selected" : ""}>困难</option>
                    </select>
                </label>
                <label>标签（逗号分隔）
                    <input id="problem-tags" value="${escapeHtml((problem.tags || []).join(", "))}" placeholder="math, loop">
                </label>
                <label>时间限制（秒）
                    <input id="problem-time-limit" type="number" min="0.01" step="0.01" required value="${escapeHtml(problem.time_limit)}">
                </label>
                <label>内存限制（MB）
                    <input id="problem-memory-limit" type="number" min="1" required value="${escapeHtml(problem.memory_limit)}">
                </label>
            </div>
            <label>题目描述<textarea id="problem-description" required>${escapeHtml(problem.description)}</textarea></label>
            <label>输入说明<textarea id="problem-input-description" class="short-textarea" required>${escapeHtml(problem.input_description)}</textarea></label>
            <label>输出说明<textarea id="problem-output-description" class="short-textarea" required>${escapeHtml(problem.output_description)}</textarea></label>
            <label>数据范围<textarea id="problem-constraints" class="short-textarea">${escapeHtml(problem.constraints || "")}</textarea></label>

            <section class="form-section">
                <div class="content-toolbar"><h3>公开样例</h3><button id="add-sample" class="secondary-button" type="button">添加样例</button></div>
                <div id="samples-editor"></div>
            </section>

            <section class="form-section">
                <div class="content-toolbar"><h3>测试点</h3><button id="add-test-case" class="secondary-button" type="button">添加测试点</button></div>
                <p class="muted">所有测试点分值总和必须等于 100。</p>
                <div id="test-cases-editor"></div>
            </section>

            <p id="problem-form-message" class="message"></p>
            <button id="save-problem" type="submit">${problemId ? "保存修改" : "创建题目"}</button>
        </form>
    `;

    const samplesEditor = context.content.querySelector("#samples-editor");
    const casesEditor = context.content.querySelector("#test-cases-editor");
    const sampleState = (problem.samples || []).map(item => ({ ...item }));
    const caseState = (problem.test_cases || []).map(item => ({ ...item }));

    const renderSamplesEditor = () => {
        samplesEditor.innerHTML = sampleState.map((sample, index) => `
            <div class="editor-card" data-index="${index}">
                <div class="content-toolbar"><strong>样例 ${index + 1}</strong>${sampleState.length > 1 ? '<button class="danger-button remove-sample" type="button">删除</button>' : ""}</div>
                <label>输入<textarea class="sample-input short-textarea">${escapeHtml(sample.input)}</textarea></label>
                <label>输出<textarea class="sample-output short-textarea">${escapeHtml(sample.output)}</textarea></label>
            </div>
        `).join("");
        samplesEditor.querySelectorAll(".editor-card").forEach(card => {
            const index = Number(card.dataset.index);
            card.querySelector(".sample-input").addEventListener("input", event => { sampleState[index].input = event.target.value; });
            card.querySelector(".sample-output").addEventListener("input", event => { sampleState[index].output = event.target.value; });
            card.querySelector(".remove-sample")?.addEventListener("click", () => { sampleState.splice(index, 1); renderSamplesEditor(); });
        });
    };

    const renderCasesEditor = () => {
        casesEditor.innerHTML = caseState.map((testCase, index) => `
            <div class="editor-card" data-index="${index}">
                <div class="content-toolbar"><strong>测试点 ${index + 1}</strong>${caseState.length > 1 ? '<button class="danger-button remove-case" type="button">删除</button>' : ""}</div>
                <div class="form-grid">
                    <label>测试点编号<input class="case-id" required value="${escapeHtml(testCase.case_id)}"></label>
                    <label>分值<input class="case-score" type="number" min="0" required value="${escapeHtml(testCase.score)}"></label>
                    <label class="checkbox-label"><input class="case-hidden" type="checkbox" ${testCase.is_hidden ? "checked" : ""}> 隐藏测试点</label>
                </div>
                <label>输入<textarea class="case-input short-textarea">${escapeHtml(testCase.input)}</textarea></label>
                <label>期望输出<textarea class="case-output short-textarea">${escapeHtml(testCase.output)}</textarea></label>
            </div>
        `).join("");
        casesEditor.querySelectorAll(".editor-card").forEach(card => {
            const index = Number(card.dataset.index);
            card.querySelector(".case-id").addEventListener("input", event => { caseState[index].case_id = event.target.value; });
            card.querySelector(".case-score").addEventListener("input", event => { caseState[index].score = Number(event.target.value); });
            card.querySelector(".case-hidden").addEventListener("change", event => { caseState[index].is_hidden = event.target.checked; });
            card.querySelector(".case-input").addEventListener("input", event => { caseState[index].input = event.target.value; });
            card.querySelector(".case-output").addEventListener("input", event => { caseState[index].output = event.target.value; });
            card.querySelector(".remove-case")?.addEventListener("click", () => { caseState.splice(index, 1); renderCasesEditor(); });
        });
    };

    renderSamplesEditor();
    renderCasesEditor();
    context.content.querySelector("#cancel-problem-form").addEventListener("click", () => renderProblems(context));
    context.content.querySelector("#add-sample").addEventListener("click", () => { sampleState.push({ input: "", output: "" }); renderSamplesEditor(); });
    context.content.querySelector("#add-test-case").addEventListener("click", () => {
        caseState.push({ case_id: `case_${String(caseState.length + 1).padStart(2, "0")}`, input: "", output: "", score: 0, is_hidden: true });
        renderCasesEditor();
    });
    context.content.querySelector("#problem-form").addEventListener("submit", event => saveProblem(context, event, problemId, sampleState, caseState));
}

async function saveProblem(context, event, originalProblemId, samples, testCases) {
    event.preventDefault();
    const message = context.content.querySelector("#problem-form-message");
    const button = context.content.querySelector("#save-problem");
    const totalScore = testCases.reduce((sum, testCase) => sum + Number(testCase.score || 0), 0);
    if (totalScore !== 100) {
        message.className = "message status-error";
        message.textContent = `测试点总分必须为 100，当前为 ${totalScore}。`;
        return;
    }

    const payload = {
        id: context.content.querySelector("#problem-id").value.trim(),
        title: context.content.querySelector("#problem-title").value.trim(),
        description: context.content.querySelector("#problem-description").value,
        input_description: context.content.querySelector("#problem-input-description").value,
        output_description: context.content.querySelector("#problem-output-description").value,
        samples,
        constraints: context.content.querySelector("#problem-constraints").value,
        time_limit: Number(context.content.querySelector("#problem-time-limit").value),
        memory_limit: Number(context.content.querySelector("#problem-memory-limit").value),
        difficulty: context.content.querySelector("#problem-difficulty").value,
        tags: context.content.querySelector("#problem-tags").value.split(",").map(tag => tag.trim()).filter(Boolean),
        test_cases: testCases,
    };

    message.className = "message status-pending";
    message.textContent = originalProblemId ? "正在保存修改..." : "正在创建题目...";
    button.disabled = true;
    try {
        await apiRequest(originalProblemId ? `/api/problems/${encodeURIComponent(originalProblemId)}` : "/api/problems", {
            method: originalProblemId ? "PUT" : "POST",
            body: JSON.stringify(payload),
        });
        await renderProblemDetail(context, payload.id);
    } catch (error) {
        message.className = "message status-error";
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}

async function deleteProblem(context, problemId) {
    if (!window.confirm(`确定删除题目 ${problemId} 吗？此操作不可撤销。`)) return;
    try {
        await apiRequest(`/api/problems/${encodeURIComponent(problemId)}`, { method: "DELETE" });
        await renderProblems(context);
    } catch (error) {
        window.alert(error.message);
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
