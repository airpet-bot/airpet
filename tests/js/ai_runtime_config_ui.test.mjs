import test from 'node:test';
import assert from 'node:assert/strict';

import {
    runtimeConfigToFormState,
    buildRuntimeConfigPayloadFromFormState,
    getLocalRuntimeBackendIds,
} from '../../static/aiRuntimeConfigUi.js';

test('runtimeConfigToFormState applies deterministic defaults for both local backends', () => {
    const formState = runtimeConfigToFormState({});

    assert.deepEqual(getLocalRuntimeBackendIds().sort(), ['llama_cpp', 'lm_studio']);
    assert.equal(formState.backends.llama_cpp.base_url, 'http://127.0.0.1:8080');
    assert.equal(formState.backends.llama_cpp.endpoint_path, '/v1/chat/completions');
    assert.equal(formState.backends.llama_cpp.timeout_seconds, '600');
    assert.equal(formState.backends.llama_cpp.verify_tls, true);
    assert.equal(formState.backends.llama_cpp.headers_json, '{}');

    assert.equal(formState.backends.lm_studio.base_url, 'http://127.0.0.1:1234');
    assert.equal(formState.backends.lm_studio.timeout_seconds, '45');
    assert.equal(formState.backends.lm_studio.verify_tls, true);
});

test('runtimeConfigToFormState supports session shape and legacy backend-key shape', () => {
    const sessionShape = runtimeConfigToFormState({
        backends: {
            llama_cpp: {
                enabled: false,
                base_url: 'http://10.0.0.5:8080',
                model: 'qwen-2.5',
                headers: {
                    Authorization: 'Bearer token',
                    'X-Test': 42,
                },
            },
        },
    });

    assert.equal(sessionShape.backends.llama_cpp.enabled, false);
    assert.equal(sessionShape.backends.llama_cpp.base_url, 'http://10.0.0.5:8080');
    assert.equal(sessionShape.backends.llama_cpp.model, 'qwen-2.5');
    assert.ok(sessionShape.backends.llama_cpp.headers_json.includes('Authorization'));
    assert.ok(sessionShape.backends.llama_cpp.headers_json.includes('Bearer token'));

    const legacyShape = runtimeConfigToFormState({
        lm_studio: {
            base_url: 'http://localhost:5555',
            timeout_seconds: 120,
        },
    });

    assert.equal(legacyShape.backends.lm_studio.base_url, 'http://localhost:5555');
    assert.equal(legacyShape.backends.lm_studio.timeout_seconds, '120');
});

test('buildRuntimeConfigPayloadFromFormState parses booleans, numbers, and headers JSON deterministically', () => {
    const result = buildRuntimeConfigPayloadFromFormState({
        backends: {
            llama_cpp: {
                enabled: true,
                base_url: 'http://127.0.0.1:8080',
                endpoint_path: '/v1/chat/completions',
                model: 'llama-3.1',
                timeout_seconds: '120',
                max_retries: '2',
                retry_backoff_seconds: '0.5',
                verify_tls: false,
                headers_json: '{"Authorization":"Bearer abc"}',
            },
            lm_studio: {
                enabled: false,
                base_url: 'http://127.0.0.1:1234',
                endpoint_path: '/v1/chat/completions',
                model: 'qwen2.5-coder',
                timeout_seconds: '60',
                max_retries: '0',
                retry_backoff_seconds: '0',
                verify_tls: true,
                headers_json: '{}',
            },
        },
    });

    assert.equal(result.ok, true);
    assert.equal(result.runtimeConfig.backends.llama_cpp.enabled, true);
    assert.equal(result.runtimeConfig.backends.llama_cpp.timeout_seconds, 120);
    assert.equal(result.runtimeConfig.backends.llama_cpp.max_retries, 2);
    assert.equal(result.runtimeConfig.backends.llama_cpp.retry_backoff_seconds, 0.5);
    assert.deepEqual(result.runtimeConfig.backends.llama_cpp.headers, {
        Authorization: 'Bearer abc',
    });

    assert.equal(result.runtimeConfig.backends.lm_studio.enabled, false);
    assert.equal(result.runtimeConfig.backends.lm_studio.max_retries, 0);
    assert.equal(result.runtimeConfig.backends.lm_studio.verify_tls, true);
});

test('buildRuntimeConfigPayloadFromFormState returns actionable validation errors', () => {
    const badHeaders = buildRuntimeConfigPayloadFromFormState({
        backends: {
            llama_cpp: {
                base_url: 'http://127.0.0.1:8080',
                endpoint_path: '/v1/chat/completions',
                model: 'm',
                timeout_seconds: '10',
                max_retries: '1',
                retry_backoff_seconds: '0.1',
                headers_json: '{broken',
            },
            lm_studio: {
                base_url: 'http://127.0.0.1:1234',
                endpoint_path: '/v1/chat/completions',
                model: 'm',
                timeout_seconds: '10',
                max_retries: '1',
                retry_backoff_seconds: '0.1',
                headers_json: '{}',
            },
        },
    });

    assert.equal(badHeaders.ok, false);
    assert.ok(String(badHeaders.error).includes('headers must be valid JSON'));

    const badTimeout = buildRuntimeConfigPayloadFromFormState({
        backends: {
            llama_cpp: {
                base_url: 'http://127.0.0.1:8080',
                endpoint_path: '/v1/chat/completions',
                model: 'm',
                timeout_seconds: '0',
                max_retries: '1',
                retry_backoff_seconds: '0.1',
                headers_json: '{}',
            },
            lm_studio: {
                base_url: 'http://127.0.0.1:1234',
                endpoint_path: '/v1/chat/completions',
                model: 'm',
                timeout_seconds: '10',
                max_retries: '1',
                retry_backoff_seconds: '0.1',
                headers_json: '{}',
            },
        },
    });

    assert.equal(badTimeout.ok, false);
    assert.ok(String(badTimeout.error).includes('timeout'));
});
