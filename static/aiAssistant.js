// static/aiAssistant.js
import * as APIService from './apiService.js';
import * as UIManager from './uiManager.js';

let messageList, promptInput, generateButton, clearButton, modelSelect, contextStatsEl;
let isProcessing = false;
let onGeometryUpdateCallback = () => {};

export function init(callbacks) {
    messageList = document.getElementById('ai_message_list');
    promptInput = document.getElementById('ai_prompt_input');
    generateButton = document.getElementById('ai_generate_button');
    clearButton = document.getElementById('clear_chat_btn');
    modelSelect = document.getElementById('ai_model_select');
    contextStatsEl = document.getElementById('ai_context_stats');
    
    if (callbacks && callbacks.onGeometryUpdate) {
        onGeometryUpdateCallback = callbacks.onGeometryUpdate;
    }

    generateButton.addEventListener('click', handleSend);
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    if (clearButton) {
        clearButton.addEventListener('click', handleClear);
    }

    if (modelSelect) {
        modelSelect.addEventListener('change', () => {
            refreshContextStats();
            UIManager.updateAiBackendStatus?.();
        });
    }

    // Load existing history
    loadHistory();
}

async function loadHistory() {
    try {
        const res = await APIService.getAiChatHistory();
        if (res.history) {
            renderHistory(res.history);
        }
    } catch (err) {
        console.error("Failed to load chat history:", err);
    } finally {
        refreshContextStats();
    }
}

export function reloadHistory() {
    loadHistory();
}

function renderHistory(history) {
    messageList.innerHTML = '';
    // Skip the first two messages (system instructions)
    if (history.length <= 2) {
        addMessageToUI('system', "Welcome to AIRPET AI. How can I help you with your detector geometry today?");
        return;
    }
    history.slice(2).forEach(msg => {
        // Gemini API uses 'parts' with 'text', Ollama uses 'content'
        // Skip tool results and system updates
        if (msg.role === 'tool' || msg.role === 'system') return;
        
        // --- NEW: Use original_message from metadata if available ---
        let text = "";
        if (msg.role === 'user' && msg.metadata && msg.metadata.original_message) {
            text = msg.metadata.original_message;
        } else {
            text = msg.parts ? msg.parts.map(p => p.text || '').join('\n').trim() : (msg.content || '').trim();
        }
        
        if (text && !text.startsWith('[System Context Update]')) {
            addMessageToUI(msg.role === 'user' ? 'user' : 'model', text);
        }
    });

    // Ensure the model selector is synced if history was loaded
    if (history.length > 0) {
        // Trigger a tiny delay to ensure models are loaded
        setTimeout(() => {
            // Find the last message that has a model_id in its metadata
            const lastModelMsg = [...history].reverse().find(m => m.metadata && m.metadata.model_id);
            if (lastModelMsg && lastModelMsg.metadata.model_id) {
                const select = document.getElementById('ai_model_select');
                if (select) select.value = lastModelMsg.metadata.model_id;
            }
        }, 500);
    }
    scrollToBottom();
}

function getBackendLabel(backendId) {
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
    disable_tool_requirement_for_local_backends: 'Set require_tools=false for local text-first backends.',
    allow_backend_fallback: 'Enable allow_fallback=true to permit Gemini/Ollama fallback.',
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
    refresh_backend_diagnostics: 'Refresh backend diagnostics and retry.',
});

function getBackendFailureStageLabel(stage) {
    return BACKEND_FAILURE_STAGE_LABELS[stage] || 'backend diagnostics error';
}

function getBackendRemediationActions(remediation) {
    if (!remediation || typeof remediation !== 'object') return [];

    if (Array.isArray(remediation.actions) && remediation.actions.length > 0) {
        return remediation.actions
            .map(action => String(action || '').trim())
            .filter(Boolean);
    }

    if (Array.isArray(remediation.action_codes) && remediation.action_codes.length > 0) {
        return remediation.action_codes
            .map(code => REMEDIATION_ACTION_LABELS[String(code)] || null)
            .filter(Boolean);
    }

    return [];
}

function formatBackendDiagnosticsError(err) {
    const diagnostics = err?.data?.backend_diagnostics;
    if (!diagnostics || typeof diagnostics !== 'object') return null;

    const stage = String(diagnostics.failure_stage || '').toLowerCase();
    const stageLabel = getBackendFailureStageLabel(stage);

    const backendLabel = getBackendLabel(diagnostics.backend_id);
    const readiness = diagnostics.readiness && typeof diagnostics.readiness === 'object'
        ? diagnostics.readiness
        : {};

    const readinessStatus = String(readiness.status || 'unknown');
    const readinessCode = String(readiness.readiness_code || 'unknown');
    const readinessMessage = String(readiness.message || diagnostics.message || err.message || 'Unknown backend error.');

    const remediation = diagnostics.remediation && typeof diagnostics.remediation === 'object'
        ? diagnostics.remediation
        : null;
    const remediationSummary = remediation?.summary
        ? String(remediation.summary)
        : 'Follow backend diagnostics guidance and retry.';
    const remediationActions = getBackendRemediationActions(remediation);

    const alertMessage = `${backendLabel}: ${stageLabel} (${readinessStatus})`;
    const detailLines = [
        'AI backend failure',
        `Stage: ${stageLabel}`,
        `Backend: ${backendLabel}`,
        `Readiness: ${readinessStatus} (${readinessCode})`,
        `Detail: ${readinessMessage}`,
        `Remediation: ${remediationSummary}`,
    ];

    if (typeof diagnostics.error_code === 'string' && diagnostics.error_code) {
        detailLines.push(`Error code: ${diagnostics.error_code}`);
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
    };
}
async function handleSend() {
    if (isProcessing) return;
    
    const message = promptInput.value.trim();
    if (!message) return;

    const model = UIManager.getAiSelectedModel();
    if (!model || model === '--export--') {
        UIManager.showError("Please select a valid AI model for chat.");
        return;
    }

    const turnLimitInput = document.getElementById('ai_turn_limit');
    const turnLimit = turnLimitInput ? parseInt(turnLimitInput.value, 10) : 10;

    setLoading(true);
    addMessageToUI('user', message);
    promptInput.value = '';
    scrollToBottom();

    try {
        const result = await APIService.sendAiChatMessage(message, model, turnLimit);
        addMessageToUI('model', result.message);
        
        // Notify main.js that geometry might have changed
        if (onGeometryUpdateCallback) {
            onGeometryUpdateCallback(result);
        }
    } catch (err) {
        const backendError = formatBackendDiagnosticsError(err);

        if (backendError) {
            UIManager.showError("AI Error: " + backendError.alertMessage);
            addMessageToUI('system', backendError.chatMessage);
            UIManager.upsertAiBackendDiagnostic?.(backendError.readiness);

            try {
                const diagResponse = await APIService.getAiBackendDiagnostics(['llama_cpp', 'lm_studio']);
                if (diagResponse?.success && Array.isArray(diagResponse.diagnostics)) {
                    diagResponse.diagnostics.forEach(diagnostic => {
                        UIManager.upsertAiBackendDiagnostic?.(diagnostic);
                    });
                }
            } catch (_diagErr) {
                // Ignore diagnostics refresh failure in chat error path.
            }
        } else {
            UIManager.showError("AI Error: " + err.message);
            addMessageToUI('system', "Error: " + err.message);
        }
    } finally {
        setLoading(false);
        scrollToBottom();
        refreshContextStats();
    }
}

async function handleClear() {
    if (!confirm("Clear AI chat history? This won't undo geometry changes.")) return;
    try {
        await APIService.clearAiChatHistory();
        messageList.innerHTML = '';
        addMessageToUI('system', "History cleared.");
    } catch (err) {
        UIManager.showError("Failed to clear history: " + err.message);
    } finally {
        refreshContextStats();
    }
}

function addMessageToUI(role, text) {
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    
    // Simple markdown-ish rendering for code blocks or tool calls
    // In the future, we could use a proper library like marked.js
    let formattedText = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br>");
    
    // Highlight bracketed tool calls if present in the text (often added by AI explanation)
    formattedText = formattedText.replace(/\[Tool: (.*?)\]/g, '<span class="tool-call">🛠️ $1</span>');

    div.innerHTML = formattedText;
    messageList.appendChild(div);
}

async function refreshContextStats() {
    if (!contextStatsEl) return;
    const model = UIManager.getAiSelectedModel?.() || '';
    try {
        const stats = await APIService.getAiContextStats(model);
        if (!stats.success) throw new Error(stats.error || 'Could not read context stats');

        const sourceLabel = stats.context_source === 'gemini'
            ? 'Gemini'
            : (stats.context_source === 'ollama'
                ? 'Ollama'
                : (stats.context_source === 'llama_cpp'
                    ? 'llama.cpp'
                    : (stats.context_source === 'lm_studio' ? 'LM Studio' : 'Unknown')));

        if (stats.max_context_tokens) {
            contextStatsEl.textContent = `Context: ~${stats.estimated_tokens}/${stats.max_context_tokens} (${sourceLabel})`;
        } else {
            contextStatsEl.textContent = `Context: ~${stats.estimated_tokens} tokens (${sourceLabel})`;
        }
    } catch (err) {
        contextStatsEl.textContent = 'Context: n/a';
    }
}

function setLoading(loading) {
    isProcessing = loading;
    generateButton.classList.toggle('loading', loading);
    generateButton.disabled = loading;
    promptInput.disabled = loading;
}

function scrollToBottom() {
    messageList.scrollTop = messageList.scrollHeight;
}

function scrollToBottomSmooth() {
    messageList.scrollTo({
        top: messageList.scrollHeight,
        behavior: 'smooth'
    });
}
