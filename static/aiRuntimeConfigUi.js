// static/aiRuntimeConfigUi.js

const BACKEND_LABELS = Object.freeze({
    llama_cpp: 'llama.cpp',
    lm_studio: 'LM Studio',
});

export const LOCAL_BACKEND_RUNTIME_DEFAULTS = Object.freeze({
    llama_cpp: Object.freeze({
        enabled: true,
        base_url: 'http://127.0.0.1:8080',
        endpoint_path: '/v1/chat/completions',
        model: 'local-model',
        timeout_seconds: 600,
        max_retries: 1,
        retry_backoff_seconds: 0.25,
        verify_tls: true,
        headers: Object.freeze({}),
    }),
    lm_studio: Object.freeze({
        enabled: true,
        base_url: 'http://127.0.0.1:1234',
        endpoint_path: '/v1/chat/completions',
        model: 'local-model',
        timeout_seconds: 45,
        max_retries: 1,
        retry_backoff_seconds: 0.25,
        verify_tls: true,
        headers: Object.freeze({}),
    }),
});

export function getLocalRuntimeBackendIds() {
    return Object.keys(LOCAL_BACKEND_RUNTIME_DEFAULTS);
}

function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function coerceBoolean(value, fallback = false) {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') return value !== 0;
    if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        if (normalized === 'true' || normalized === '1' || normalized === 'yes' || normalized === 'on') return true;
        if (normalized === 'false' || normalized === '0' || normalized === 'no' || normalized === 'off') return false;
    }
    return fallback;
}

function normalizeHeadersObject(headers) {
    const source = asObject(headers);
    const normalized = {};

    Object.entries(source).forEach(([rawKey, rawValue]) => {
        const key = String(rawKey || '').trim();
        if (!key) return;
        normalized[key] = String(rawValue ?? '').trim();
    });

    return normalized;
}

function normalizeBackendConfig(runtimeConfig, backendId) {
    const defaults = LOCAL_BACKEND_RUNTIME_DEFAULTS[backendId] || {};
    const rootObj = asObject(runtimeConfig);
    const backendMap = asObject(rootObj.backends);
    const raw = asObject(backendMap[backendId] || rootObj[backendId]);

    return {
        enabled: coerceBoolean(raw.enabled, defaults.enabled),
        base_url: String(raw.base_url ?? defaults.base_url ?? '').trim(),
        endpoint_path: String(raw.endpoint_path ?? defaults.endpoint_path ?? '').trim(),
        model: String(raw.model ?? defaults.model ?? '').trim(),
        timeout_seconds: Number(raw.timeout_seconds ?? defaults.timeout_seconds ?? 0),
        max_retries: Number(raw.max_retries ?? defaults.max_retries ?? 0),
        retry_backoff_seconds: Number(raw.retry_backoff_seconds ?? defaults.retry_backoff_seconds ?? 0),
        verify_tls: coerceBoolean(raw.verify_tls, defaults.verify_tls),
        headers: normalizeHeadersObject(raw.headers ?? defaults.headers),
    };
}

export function runtimeConfigToFormState(runtimeConfig = {}) {
    const backends = {};

    getLocalRuntimeBackendIds().forEach((backendId) => {
        const normalized = normalizeBackendConfig(runtimeConfig, backendId);
        backends[backendId] = {
            enabled: !!normalized.enabled,
            base_url: normalized.base_url,
            endpoint_path: normalized.endpoint_path,
            model: normalized.model,
            timeout_seconds: String(normalized.timeout_seconds),
            max_retries: String(normalized.max_retries),
            retry_backoff_seconds: String(normalized.retry_backoff_seconds),
            verify_tls: !!normalized.verify_tls,
            headers_json: JSON.stringify(normalized.headers, null, 2),
        };
    });

    return { backends };
}

function parseRequiredString(value, label) {
    const parsed = String(value ?? '').trim();
    if (!parsed) {
        return { ok: false, error: `${label} is required.` };
    }
    return { ok: true, value: parsed };
}

function parseFiniteNumber(value, label, { min = null, integer = false } = {}) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        return { ok: false, error: `${label} must be a valid number.` };
    }
    if (integer && !Number.isInteger(parsed)) {
        return { ok: false, error: `${label} must be an integer.` };
    }
    if (min !== null && parsed < min) {
        return { ok: false, error: `${label} must be >= ${min}.` };
    }
    return { ok: true, value: parsed };
}

function parseHeadersJson(rawValue, backendLabel) {
    const text = String(rawValue ?? '').trim();
    if (!text) {
        return { ok: true, value: {} };
    }

    let parsed;
    try {
        parsed = JSON.parse(text);
    } catch (_err) {
        return {
            ok: false,
            error: `${backendLabel} headers must be valid JSON. Example: {"Authorization": "Bearer ..."}`,
        };
    }

    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        return {
            ok: false,
            error: `${backendLabel} headers must be a JSON object of key/value pairs.`,
        };
    }

    return { ok: true, value: normalizeHeadersObject(parsed) };
}

export function buildRuntimeConfigPayloadFromFormState(formState = {}) {
    const formObject = asObject(formState);
    const backendForms = asObject(formObject.backends);
    const runtimeConfig = { backends: {} };

    for (const backendId of getLocalRuntimeBackendIds()) {
        const backendLabel = BACKEND_LABELS[backendId] || backendId;
        const defaults = LOCAL_BACKEND_RUNTIME_DEFAULTS[backendId] || {};
        const raw = asObject(backendForms[backendId] || formObject[backendId]);

        const baseUrl = parseRequiredString(raw.base_url ?? defaults.base_url, `${backendLabel} base URL`);
        if (!baseUrl.ok) return { ok: false, error: baseUrl.error };

        const endpointPath = parseRequiredString(raw.endpoint_path ?? defaults.endpoint_path, `${backendLabel} endpoint path`);
        if (!endpointPath.ok) return { ok: false, error: endpointPath.error };

        const model = parseRequiredString(raw.model ?? defaults.model, `${backendLabel} model`);
        if (!model.ok) return { ok: false, error: model.error };

        const timeout = parseFiniteNumber(raw.timeout_seconds ?? defaults.timeout_seconds, `${backendLabel} timeout (seconds)`, { min: 0.1 });
        if (!timeout.ok) return { ok: false, error: timeout.error };

        const maxRetries = parseFiniteNumber(raw.max_retries ?? defaults.max_retries, `${backendLabel} max retries`, { min: 0, integer: true });
        if (!maxRetries.ok) return { ok: false, error: maxRetries.error };

        const retryBackoff = parseFiniteNumber(
            raw.retry_backoff_seconds ?? defaults.retry_backoff_seconds,
            `${backendLabel} retry backoff (seconds)`,
            { min: 0 }
        );
        if (!retryBackoff.ok) return { ok: false, error: retryBackoff.error };

        const parsedHeaders = parseHeadersJson(raw.headers_json, backendLabel);
        if (!parsedHeaders.ok) return { ok: false, error: parsedHeaders.error };

        runtimeConfig.backends[backendId] = {
            enabled: coerceBoolean(raw.enabled, defaults.enabled),
            base_url: baseUrl.value,
            endpoint_path: endpointPath.value,
            model: model.value,
            timeout_seconds: timeout.value,
            max_retries: maxRetries.value,
            retry_backoff_seconds: retryBackoff.value,
            verify_tls: coerceBoolean(raw.verify_tls, defaults.verify_tls),
            headers: parsedHeaders.value,
        };
    }

    return {
        ok: true,
        runtimeConfig,
    };
}
