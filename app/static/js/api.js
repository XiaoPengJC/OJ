export class ApiError extends Error {
    constructor(message, status, payload = null) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.payload = payload;
    }
}

export async function apiRequest(url, options = {}) {
    const requestOptions = {
        credentials: "same-origin",
        ...options,
        headers: { ...(options.headers || {}) },
    };

    if (options.body !== undefined) {
        requestOptions.headers["Content-Type"] = "application/json";
    }

    let response;
    try {
        response = await fetch(url, requestOptions);
    } catch {
        throw new ApiError("网络请求失败，请检查后端服务是否正在运行。", 0);
    }

    let payload;
    try {
        payload = await response.json();
    } catch {
        throw new ApiError("服务器返回了无法解析的数据。", response.status);
    }

    if (!response.ok) {
        throw new ApiError(
            payload.message || payload.detail || "请求失败",
            response.status,
            payload,
        );
    }
    return payload;
}
