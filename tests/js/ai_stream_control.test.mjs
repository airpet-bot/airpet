import assert from 'node:assert/strict';
import test from 'node:test';

import { streamAiChatMessage } from '../../static/apiService.js';


test('streamAiChatMessage exposes caller cancellation as a user stop', async () => {
    const originalDocument = globalThis.document;
    const originalWindow = globalThis.window;
    const originalFetch = globalThis.fetch;

    globalThis.document = {
        hidden: false,
        addEventListener() {},
        removeEventListener() {},
    };
    globalThis.window = {
        dispatchEvent() {},
    };
    globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => {
        options.signal.addEventListener('abort', () => {
            const error = new Error('aborted');
            error.name = 'AbortError';
            reject(error);
        }, { once: true });
    });

    try {
        const controller = new AbortController();
        const request = streamAiChatMessage(
            'build a detector',
            'llama_cpp::test-model',
            500,
            null,
            [],
            { signal: controller.signal },
        );
        controller.abort();

        await assert.rejects(request, (error) => {
            assert.equal(error.type, 'ai_stream_cancelled');
            assert.equal(error.message, 'AI run stopped by user.');
            return true;
        });
    } finally {
        globalThis.document = originalDocument;
        globalThis.window = originalWindow;
        globalThis.fetch = originalFetch;
    }
});
