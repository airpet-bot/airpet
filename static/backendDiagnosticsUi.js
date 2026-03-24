// static/backendDiagnosticsUi.js

export function getBackendLabel(backendId) {
    if (backendId === 'llama_cpp') return 'llama.cpp';
    if (backendId === 'lm_studio') return 'LM Studio';
    return backendId || 'AI backend';
}

const BACKEND_FAILURE_STAGE_LABELS = Object.freeze({
    selector_validation: 'selector validation',
    selector_requirements: 'selector requirements mismatch',
    backend_runtime: 'backend runtime failure',
});

const REMEDIATION_ACTION_LABELS = Object.freeze({
    use_backend_model_selector_format: "Use '<backend>::<model_name>' local selector format.",
    select_nonempty_local_model_name: 'Select a local model with a non-empty model name.',
    review_backend_requirements: 'Review backend selector requirements (tools/json/streaming/context) for this backend.',
    allow_backend_fallback: 'Enable allow_fallback=true to permit backend fallback.',
    switch_backend_for_missing_capabilities: 'Switch to a backend that supports the missing capabilities.',
    align_selector_requirements_with_effective_capabilities: 'Align selector requirements with effective backend capability overrides.',
    update_runtime_capability_overrides_for_selected_backend: 'Update runtime capability overrides for the selected backend profile.',
    allow_fallback_or_choose_capability_compatible_backend: 'Allow fallback or choose a capability-compatible backend.',
    disable_tool_requirement_for_local_backends: 'Set require_tools=false for local text-first backends.',
    switch_to_cloud_backend_for_tool_calls: 'Use a Gemini/Ollama model when tool calling is required.',
    increase_backend_timeout: 'Increase backend timeout_seconds or reduce prompt size.',
    retry_after_backend_idle: 'Retry after the local model server is idle.',
    verify_local_host_resources: 'Verify local CPU/RAM resources are not saturated.',
    start_local_backend_service: 'Start the local backend service.',
    verify_backend_base_url_and_port: 'Verify backend base_url and port configuration.',
    verify_models_endpoint_reachable: "Confirm '<base_url>/v1/models' is reachable.",
    fix_backend_configuration: 'Fix local backend runtime_config fields.',
    set_valid_local_model_name: "Set a valid local model name exposed by '/v1/models'.",
    validate_openai_compatible_models_payload: "Validate '/v1/models' returns an OpenAI-compatible payload.",
    retry_request: 'Retry once to rule out a transient backend failure.',
    inspect_backend_logs: 'Inspect local backend logs for runtime errors.',
    capture_runtime_backend_request_context: 'Capture runtime request context and backend metadata for debugging.',
    inspect_backend_runtime_logs: 'Inspect backend runtime logs for contradiction between readiness and execution.',
    reprobe_backend_after_runtime_failure: 'Re-run backend readiness probes immediately after runtime failure.',
    refresh_backend_diagnostics: 'Refresh backend diagnostics and retry.',
});

const RUNTIME_PROFILE_LABELS = Object.freeze({
    built_in_defaults: 'using built-in defaults',
    session_profile: 'using saved profile',
    request_overrides: 'using request overrides',
    session_profile_plus_request_overrides: 'using saved profile + request overrides',
});

const RUNTIME_PROFILE_CHIP_SUFFIX = Object.freeze({
    built_in_defaults: 'built-in defaults',
    session_profile: 'saved profile',
    request_overrides: 'request overrides',
    session_profile_plus_request_overrides: 'saved profile + request overrides',
});

const RUNTIME_PROFILE_DETAIL_LINES = Object.freeze({
    built_in_defaults: 'Session profile not set; built-in backend defaults are active.',
    session_profile: 'Saved profile is session-scoped and reused by diagnostics/chat unless request overrides are sent.',
    request_overrides: 'Request-level runtime overrides are active for this check.',
    session_profile_plus_request_overrides: 'Saved session profile is active; request overrides take precedence for this check.',
});

export function getBackendFailureStageLabel(stage) {
    return BACKEND_FAILURE_STAGE_LABELS[stage] || 'backend diagnostics error';
}

export function getBackendRemediationActions(remediation) {
    if (!remediation || typeof remediation !== 'object') return [];

    if (Array.isArray(remediation.actions) && remediation.actions.length > 0) {
        return remediation.actions
            .map(action => String(action || '').trim())
            .filter(Boolean);
    }

    if (Array.isArray(remediation.action_codes) && remediation.action_codes.length > 0) {
        return remediation.action_codes
            .map(code => {
                const normalizedCode = String(code || '').trim();
                if (!normalizedCode) return null;
                return REMEDIATION_ACTION_LABELS[normalizedCode] || `Action code: ${normalizedCode}`;
            })
            .filter(Boolean);
    }

    return [];
}

export function formatBackendDiagnosticsError(err) {
    const diagnostics = (err?.data?.backend_diagnostics && typeof err.data.backend_diagnostics === 'object')
        ? err.data.backend_diagnostics
        : ((err?.backend_diagnostics && typeof err.backend_diagnostics === 'object') ? err.backend_diagnostics : null);
    if (!diagnostics) return null;

    const stage = String(diagnostics.failure_stage || '').toLowerCase();
    const stageLabel = getBackendFailureStageLabel(stage);

    const backendLabel = getBackendLabel(diagnostics.backend_id);
    const readiness = diagnostics.readiness && typeof diagnostics.readiness === 'object'
        ? diagnostics.readiness
        : {};

    const readinessStatus = String(readiness.status || 'unknown');
    const readinessCode = String(readiness.readiness_code || 'unknown');
    const readinessMessage = String(readiness.message || diagnostics.message || err.message || 'Unknown backend error.');

    const runtimeProfile = diagnostics.runtime_profile && typeof diagnostics.runtime_profile === 'object'
        ? diagnostics.runtime_profile
        : (readiness.runtime_profile && typeof readiness.runtime_profile === 'object' ? readiness.runtime_profile : null);
    const runtimeProfileLabel = runtimeProfile ? getRuntimeProfileLabel(runtimeProfile) : null;
    const runtimeProfileDetail = runtimeProfile ? getRuntimeProfileDetail(runtimeProfile) : '';

    const contradictions = Array.isArray(diagnostics.contradictions)
        ? diagnostics.contradictions.filter(item => item && typeof item === 'object')
        : [];

    const remediation = diagnostics.remediation && typeof diagnostics.remediation === 'object'
        ? diagnostics.remediation
        : null;
    const remediationSummary = remediation?.summary
        ? String(remediation.summary)
        : 'Follow backend diagnostics guidance and retry.';
    const remediationActions = getBackendRemediationActions(remediation);

    const backendSelection = err?.data?.backend_selection && typeof err.data.backend_selection === 'object'
        ? err.data.backend_selection
        : null;

    const alertMessage = `${backendLabel}: ${stageLabel} (${readinessStatus})`;
    const detailLines = [
        'AI backend failure',
        `Stage: ${stageLabel}`,
        `Backend: ${backendLabel}`,
        `Readiness: ${readinessStatus} (${readinessCode})`,
    ];

    if (runtimeProfileLabel) {
        detailLines.push(`Runtime profile: ${runtimeProfileLabel}`);
    }
    if (runtimeProfileDetail) {
        detailLines.push(`Runtime profile detail: ${runtimeProfileDetail}`);
    }

    if (backendSelection) {
        const selectionBackendId = backendSelection.resolved_backend_id || diagnostics.backend_id;
        const selectionBackendLabel = getBackendLabel(selectionBackendId);
        const selectionModel = backendSelection.resolved_model
            ? `::${backendSelection.resolved_model}`
            : '';
        const executionMode = backendSelection.execution_mode
            ? ` (${backendSelection.execution_mode})`
            : '';
        detailLines.push(`Selection: ${selectionBackendLabel}${selectionModel}${executionMode}`);
    }

    detailLines.push(`Detail: ${readinessMessage}`);
    detailLines.push(`Remediation: ${remediationSummary}`);

    if (typeof diagnostics.error_code === 'string' && diagnostics.error_code) {
        detailLines.push(`Error code: ${diagnostics.error_code}`);
    }

    if (contradictions.length > 0) {
        detailLines.push('Contradictions:');
        contradictions.slice(0, 3).forEach((item, index) => {
            const summary = String(item.summary || item.code || 'Unspecified contradiction.');
            const contradictionClass = item.contradiction_class
                ? `[${item.contradiction_class}] `
                : '';
            detailLines.push(`${index + 1}. ${contradictionClass}${summary}`);
        });
    }

    if (remediationActions.length > 0) {
        detailLines.push('Next steps:');
        remediationActions.forEach((step, index) => {
            detailLines.push(`${index + 1}. ${step}`);
        });
    }

    return {
        alertMessage,
        chatMessage: detailLines.join('\n'),
        readiness,
        backendSelection,
    };
}

export function normalizeAiBackendDiagnostics(localBackendDiagnostics) {
    if (Array.isArray(localBackendDiagnostics)) {
        return localBackendDiagnostics.reduce((acc, item) => {
            if (item && typeof item === 'object' && item.backend_id) {
                acc[item.backend_id] = item;
            }
            return acc;
        }, {});
    }

    if (localBackendDiagnostics && typeof localBackendDiagnostics === 'object') {
        return Object.entries(localBackendDiagnostics).reduce((acc, [backendId, diagnostic]) => {
            if (diagnostic && typeof diagnostic === 'object') {
                acc[backendId] = diagnostic;
            }
            return acc;
        }, {});
    }

    return {};
}

export function getLocalBackendIdForModel(modelValue) {
    if (typeof modelValue !== 'string') return null;
    if (modelValue.startsWith('llama_cpp::')) return 'llama_cpp';
    if (modelValue.startsWith('lm_studio::')) return 'lm_studio';
    return null;
}

export function getBackendDisplayName(backendId) {
    if (backendId === 'llama_cpp') return 'llama.cpp';
    if (backendId === 'lm_studio') return 'LM Studio';
    return backendId || 'Local backend';
}

export function getReadinessBadge(status) {
    switch ((status || '').toLowerCase()) {
        case 'healthy':
            return '🟢';
        case 'timeout':
            return '🟠';
        case 'unreachable':
            return '🔴';
        case 'misconfigured':
            return '🟣';
        default:
            return '⚪';
    }
}

export function getReadinessLabel(status) {
    switch ((status || '').toLowerCase()) {
        case 'healthy':
            return 'healthy';
        case 'timeout':
            return 'timeout';
        case 'unreachable':
            return 'unreachable';
        case 'misconfigured':
            return 'misconfigured';
        default:
            return 'unknown';
    }
}

function normalizeRuntimeProfileSource(runtimeProfile) {
    const source = String(runtimeProfile?.source || '').trim().toLowerCase();
    return Object.prototype.hasOwnProperty.call(RUNTIME_PROFILE_LABELS, source)
        ? source
        : 'built_in_defaults';
}

function getRuntimeProfileLabel(runtimeProfile) {
    if (runtimeProfile?.label) {
        return String(runtimeProfile.label).trim();
    }
    return RUNTIME_PROFILE_LABELS[normalizeRuntimeProfileSource(runtimeProfile)] || RUNTIME_PROFILE_LABELS.built_in_defaults;
}

function getRuntimeProfileDetail(runtimeProfile) {
    if (runtimeProfile?.message) {
        return String(runtimeProfile.message).trim();
    }
    return RUNTIME_PROFILE_DETAIL_LINES[normalizeRuntimeProfileSource(runtimeProfile)] || '';
}

function getRuntimeProfileChipSuffix(runtimeProfile) {
    const source = normalizeRuntimeProfileSource(runtimeProfile);
    return RUNTIME_PROFILE_CHIP_SUFFIX[source] || RUNTIME_PROFILE_CHIP_SUFFIX.built_in_defaults;
}

export function buildLocalBackendTooltip(backendId, diagnostic) {
    const backendLabel = getBackendDisplayName(backendId);
    const status = getReadinessLabel(diagnostic?.status);
    const readinessCode = diagnostic?.readiness_code || 'n/a';
    const message = diagnostic?.message || 'No readiness diagnostics available yet.';
    const endpoint = diagnostic?.models_endpoint;
    const runtimeProfile = diagnostic?.runtime_profile;

    const lines = [
        `${backendLabel} readiness: ${status}`,
        `Code: ${readinessCode}`,
        message,
        `Runtime profile: ${getRuntimeProfileLabel(runtimeProfile)}`,
    ];

    const runtimeProfileDetail = getRuntimeProfileDetail(runtimeProfile);
    if (runtimeProfileDetail) {
        lines.push(runtimeProfileDetail);
    }

    if (endpoint) {
        lines.push(`Probe: ${endpoint}`);
    }

    return lines.join('\n');
}

export function formatLocalModelOptionLabel(modelName, diagnostic) {
    return `${getReadinessBadge(diagnostic?.status)} ${modelName}`;
}

export function buildBackendStatusChip(selectedModel, diagnosticsById = {}) {
    if (!selectedModel) {
        return {
            text: 'Backend: n/a',
            title: 'No AI model selected.',
            statusClass: null,
        };
    }

    const backendId = getLocalBackendIdForModel(selectedModel);
    if (!backendId) {
        return {
            text: 'Backend: cloud',
            title: 'Gemini/Ollama routing does not require local backend readiness probes.',
            statusClass: null,
        };
    }

    const diagnostic = diagnosticsById[backendId] || null;
    const status = getReadinessLabel(diagnostic?.status);
    const badge = getReadinessBadge(diagnostic?.status);
    const runtimeSuffix = getRuntimeProfileChipSuffix(diagnostic?.runtime_profile);

    return {
        text: `${badge} ${getBackendDisplayName(backendId)}: ${status} · ${runtimeSuffix}`,
        title: buildLocalBackendTooltip(backendId, diagnostic),
        statusClass: `status-${status}`,
    };
}

export function applyBackendStatusChip(element, chip) {
    if (!element || !chip) return;

    element.className = 'ai-model-info ai-backend-status';
    if (chip.statusClass && element.classList?.add) {
        element.classList.add(chip.statusClass);
    }

    element.textContent = chip.text;
    element.title = chip.title;
}

export const __TEST_ONLY__ = {
    BACKEND_FAILURE_STAGE_LABELS,
    REMEDIATION_ACTION_LABELS,
};
