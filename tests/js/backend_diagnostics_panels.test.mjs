import test from 'node:test';
import assert from 'node:assert/strict';

import {
    formatLocalModelOptionLabel,
    buildBackendStatusChip,
    applyBackendStatusChip,
    buildLocalBackendTooltip,
    formatBackendDiagnosticsError,
} from '../../static/backendDiagnosticsUi.js';

function createFakeStatusChipElement() {
    const classSet = new Set();
    return {
        className: '',
        textContent: '',
        title: '',
        classList: {
            add(name) {
                classSet.add(name);
            },
            has(name) {
                return classSet.has(name);
            },
            toArray() {
                return [...classSet];
            },
        },
    };
}

test('selector badge copy + tooltip copy remain stable for local model options', () => {
    const diagnostic = {
        status: 'timeout',
        readiness_code: 'backend_timeout',
        message: 'Timed out while probing local model list.',
        models_endpoint: 'http://127.0.0.1:1234/v1/models',
        runtime_profile: {
            source: 'session_profile',
        },
    };

    assert.equal(formatLocalModelOptionLabel('mistral-small', diagnostic), '🟠 mistral-small');

    const tooltip = buildLocalBackendTooltip('lm_studio', diagnostic);
    assert.ok(tooltip.includes('LM Studio readiness: timeout'));
    assert.ok(tooltip.includes('Code: backend_timeout'));
    assert.ok(tooltip.includes('Timed out while probing local model list.'));
    assert.ok(tooltip.includes('Runtime profile: using saved profile'));
    assert.ok(tooltip.includes('Saved profile is session-scoped and reused by diagnostics/chat unless request overrides are sent.'));
    assert.ok(tooltip.includes('Probe: http://127.0.0.1:1234/v1/models'));
});

test('status-chip transitions cover no-model, cloud, and local readiness states', () => {
    const diagnosticsById = {
        llama_cpp: {
            backend_id: 'llama_cpp',
            status: 'healthy',
            readiness_code: 'ok',
            message: 'ready',
            runtime_profile: {
                source: 'session_profile',
            },
        },
        lm_studio: {
            backend_id: 'lm_studio',
            status: 'unreachable',
            readiness_code: 'backend_unreachable',
            message: 'connection refused',
            runtime_profile: {
                source: 'built_in_defaults',
            },
        },
    };

    const noModelChip = buildBackendStatusChip('', diagnosticsById);
    assert.deepEqual(noModelChip, {
        text: 'Backend: n/a',
        title: 'No AI model selected.',
        statusClass: null,
    });

    const cloudChip = buildBackendStatusChip('gemini-2.5-pro', diagnosticsById);
    assert.deepEqual(cloudChip, {
        text: 'Backend: cloud',
        title: 'Gemini/Ollama routing does not require local backend readiness probes.',
        statusClass: null,
    });

    const healthyChip = buildBackendStatusChip('llama_cpp::qwen2.5', diagnosticsById);
    assert.equal(healthyChip.text, '🟢 llama.cpp: healthy · saved profile');
    assert.equal(healthyChip.statusClass, 'status-healthy');

    const unreachableChip = buildBackendStatusChip('lm_studio::llama-3.1-8b', diagnosticsById);
    assert.equal(unreachableChip.text, '🔴 LM Studio: unreachable · built-in defaults');
    assert.equal(unreachableChip.statusClass, 'status-unreachable');

    const fakeEl = createFakeStatusChipElement();
    applyBackendStatusChip(fakeEl, unreachableChip);
    assert.equal(fakeEl.className, 'ai-model-info ai-backend-status');
    assert.ok(fakeEl.classList.has('status-unreachable'));
    assert.equal(fakeEl.textContent, '🔴 LM Studio: unreachable · built-in defaults');
    assert.ok(fakeEl.title.includes('LM Studio readiness: unreachable'));
    assert.ok(fakeEl.title.includes('Runtime profile: using built-in defaults'));
});

test('chat remediation rendering keeps deterministic stage/readiness and next-step copy', () => {
    const err = {
        message: 'Selector failed',
        data: {
            backend_diagnostics: {
                failure_stage: 'selector_requirements',
                backend_id: 'llama_cpp',
                error_code: 'backend_selection_failed',
                readiness: {
                    status: 'healthy',
                    readiness_code: 'ok',
                    message: 'Local backend reachable.',
                },
                remediation: {
                    summary: 'Selected backend cannot satisfy the requested capabilities.',
                    action_codes: [
                        'review_backend_requirements',
                        'allow_backend_fallback',
                    ],
                },
            },
        },
    };

    const formatted = formatBackendDiagnosticsError(err);
    assert.ok(formatted);
    assert.equal(formatted.alertMessage, 'llama.cpp: selector requirements mismatch (healthy)');

    assert.ok(formatted.chatMessage.includes('AI backend failure'));
    assert.ok(formatted.chatMessage.includes('Stage: selector requirements mismatch'));
    assert.ok(formatted.chatMessage.includes('Readiness: healthy (ok)'));
    assert.ok(formatted.chatMessage.includes('Remediation: Selected backend cannot satisfy the requested capabilities.'));
    assert.ok(formatted.chatMessage.includes('Error code: backend_selection_failed'));
    assert.ok(formatted.chatMessage.includes('Next steps:'));
    assert.ok(formatted.chatMessage.includes('1. Review backend selector requirements (tools/json/streaming/context) for this backend.'));
    assert.ok(formatted.chatMessage.includes('2. Enable allow_fallback=true to permit backend fallback.'));
});

test('chat remediation prefers explicit actions over action-code lookup and returns null without diagnostics', () => {
    const explicit = formatBackendDiagnosticsError({
        message: 'runtime fail',
        data: {
            backend_diagnostics: {
                failure_stage: 'backend_runtime',
                backend_id: 'lm_studio',
                readiness: {
                    status: 'unreachable',
                    readiness_code: 'backend_unreachable',
                },
                remediation: {
                    summary: 'LM Studio is unreachable from AIRPET.',
                    actions: ['Check LM Studio app is open.', 'Verify API port is correct.'],
                    action_codes: ['start_local_backend_service'],
                },
            },
        },
    });

    assert.ok(explicit.chatMessage.includes('1. Check LM Studio app is open.'));
    assert.ok(explicit.chatMessage.includes('2. Verify API port is correct.'));
    assert.ok(!explicit.chatMessage.includes('1. Start the local backend service.'));

    assert.equal(formatBackendDiagnosticsError({ message: 'plain error' }), null);
});

test('stream SSE backend diagnostics keep runtime-profile, contradiction, and selection details', () => {
    const streamErr = {
        message: 'Stream processing error: timed out while contacting local backend.',
        data: {
            backend_selection: {
                resolved_backend_id: 'llama_cpp',
                resolved_model: 'qwen2.5-coder',
                execution_mode: 'local_text_adapter',
            },
            backend_diagnostics: {
                failure_stage: 'backend_runtime',
                backend_id: 'llama_cpp',
                error_code: 'local_backend_invocation_failed',
                runtime_profile: {
                    source: 'session_profile_plus_request_overrides',
                },
                readiness: {
                    backend_id: 'llama_cpp',
                    status: 'timeout',
                    readiness_code: 'backend_timeout',
                    message: 'Timed out while waiting for local backend completion.',
                    runtime_profile: {
                        source: 'session_profile_plus_request_overrides',
                    },
                },
                contradictions: [
                    {
                        code: 'runtime_failure_despite_healthy_readiness',
                        contradiction_class: 'runtime_backend_mismatch',
                        summary: 'Readiness probe appears healthy but runtime call failed.',
                    },
                ],
                remediation: {
                    summary: 'Backend timed out during runtime invocation.',
                    action_codes: [
                        'increase_backend_timeout',
                        'capture_runtime_backend_request_context',
                    ],
                },
            },
        },
    };

    const formatted = formatBackendDiagnosticsError(streamErr);
    assert.ok(formatted);
    assert.equal(formatted.alertMessage, 'llama.cpp: backend runtime failure (timeout)');
    assert.equal(formatted.backendSelection?.resolved_backend_id, 'llama_cpp');

    assert.ok(formatted.chatMessage.includes('Runtime profile: using saved profile + request overrides'));
    assert.ok(formatted.chatMessage.includes('Selection: llama.cpp::qwen2.5-coder (local_text_adapter)'));
    assert.ok(formatted.chatMessage.includes('Contradictions:'));
    assert.ok(formatted.chatMessage.includes('1. [runtime_backend_mismatch] Readiness probe appears healthy but runtime call failed.'));
    assert.ok(formatted.chatMessage.includes('1. Increase backend timeout_seconds or reduce prompt size.'));
    assert.ok(formatted.chatMessage.includes('2. Capture runtime request context and backend metadata for debugging.'));

    const streamChip = buildBackendStatusChip('llama_cpp::qwen2.5-coder', {
        llama_cpp: formatted.readiness,
    });
    assert.equal(streamChip.text, '🟠 llama.cpp: timeout · saved profile + request overrides');
});
