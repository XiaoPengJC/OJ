import { apiRequest } from "./api.js";
import { renderAuditLogs } from "./audit.js";
import { renderBackups } from "./backups.js";
import { renderProblems } from "./problems.js";
import { renderSubmissionDetail, renderSubmissions } from "./submissions.js";
import { renderUsers } from "./users.js";
import { translateRole } from "./utils.js";

const authSection = document.getElementById("auth-section");
const dashboardSection = document.getElementById("dashboard-section");
const loginView = document.getElementById("login-view");
const registerView = document.getElementById("register-view");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const authMessage = document.getElementById("auth-message");
const currentUserText = document.getElementById("current-user");
const logoutButton = document.getElementById("logout-button");
const title = document.getElementById("dashboard-title");
const roleHint = document.getElementById("role-hint");
const content = document.getElementById("content-area");

const navButtons = {
    problems: document.getElementById("nav-problems"),
    submissions: document.getElementById("nav-submissions"),
    users: document.getElementById("nav-users"),
    audit: document.getElementById("nav-audit"),
    backups: document.getElementById("nav-backups"),
};

const context = {
    currentUser: null,
    title,
    content,
    openSubmission: submissionId => showPage("submissions", submissionId),
    onSessionExpired: showLoggedOut,
};

function showAuthView(view) {
    const loginActive = view === "login";
    loginView.hidden = !loginActive;
    registerView.hidden = loginActive;
    document.getElementById("show-login-button").className = loginActive ? "" : "secondary-button";
    document.getElementById("show-register-button").className = loginActive ? "secondary-button" : "";
    authMessage.textContent = "";
}

function showLoggedOut() {
    context.currentUser = null;
    authSection.hidden = false;
    dashboardSection.hidden = true;
    logoutButton.hidden = true;
    currentUserText.textContent = "未登录";
    content.innerHTML = "";
    showAuthView("login");
}

function showLoggedIn(user) {
    context.currentUser = user;
    authSection.hidden = true;
    dashboardSection.hidden = false;
    logoutButton.hidden = false;
    currentUserText.textContent = `${user.username}（${translateRole(user.role)}）`;
    roleHint.textContent = user.role === "student"
        ? "学生只能查看自己的提交与裁剪后的日志。"
        : "教师和管理员可以查看全部提交、完整日志并发起重新评测。";
    document.querySelectorAll(".admin-only").forEach(element => {
        element.hidden = user.role !== "admin";
    });
}

async function showPage(page, parameter = null) {
    for (const [name, button] of Object.entries(navButtons)) {
        button.className = name === page ? "" : "secondary-button";
    }

    if (page === "problems") return renderProblems(context);
    if (page === "submissions") {
        return parameter
            ? renderSubmissionDetail(context, parameter)
            : renderSubmissions(context);
    }
    if (page === "users") return renderUsers(context);
    if (page === "audit") return renderAuditLogs(context);
    if (page === "backups") return renderBackups(context);
}

loginForm.addEventListener("submit", async event => {
    event.preventDefault();
    authMessage.className = "message status-pending";
    authMessage.textContent = "正在登录...";
    try {
        const response = await apiRequest("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({
                username: document.getElementById("login-username").value,
                password: document.getElementById("login-password").value,
            }),
        });
        loginForm.reset();
        showLoggedIn(response.data);
        await showPage("problems");
    } catch (error) {
        authMessage.className = "message status-error";
        authMessage.textContent = error.message;
    }
});

registerForm.addEventListener("submit", async event => {
    event.preventDefault();
    const username = document.getElementById("register-username").value;
    const password = document.getElementById("register-password").value;
    const confirmation = document.getElementById("register-password-confirm").value;
    if (password !== confirmation) {
        authMessage.className = "message status-error";
        authMessage.textContent = "两次输入的密码不一致。";
        return;
    }

    authMessage.className = "message status-pending";
    authMessage.textContent = "正在注册...";
    try {
        await apiRequest("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({ username, password }),
        });
        const loginResponse = await apiRequest("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ username, password }),
        });
        registerForm.reset();
        showLoggedIn(loginResponse.data);
        await showPage("problems");
    } catch (error) {
        authMessage.className = "message status-error";
        authMessage.textContent = error.message;
    }
});

logoutButton.addEventListener("click", async () => {
    try {
        await apiRequest("/api/auth/logout", { method: "POST" });
    } finally {
        showLoggedOut();
    }
});

document.getElementById("show-login-button").addEventListener("click", () => showAuthView("login"));
document.getElementById("show-register-button").addEventListener("click", () => showAuthView("register"));
navButtons.problems.addEventListener("click", () => showPage("problems"));
navButtons.submissions.addEventListener("click", () => showPage("submissions"));
navButtons.users.addEventListener("click", () => showPage("users"));
navButtons.audit.addEventListener("click", () => showPage("audit"));
navButtons.backups.addEventListener("click", () => showPage("backups"));

async function initializePage() {
    try {
        const response = await apiRequest("/api/auth/me");
        showLoggedIn(response.data);
        await showPage("problems");
    } catch {
        showLoggedOut();
    }
}

initializePage();
