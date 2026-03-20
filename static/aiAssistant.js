// static/aiAssistant.js
import * as APIService from './apiService.js';
import * as UIManager from './uiManager.js';
import { formatBackendDiagnosticsError } from './backendDiagnosticsUi.js';

let messageList, promptInput, generateButton, clearButton, modelSelect, contextStatsEl;
let isProcessing = false;
let onGeometryUpdateCallback = () => {};
let localUnsavedMessages = [];
let currentRecentTools = [];
let currentTurn = 1;
let currentTurnLimit = 10;

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
        
        const savedMessages = localStorage.getItem('airpet_unsaved_messages');
        if (savedMessages) {
            try {
                localUnsavedMessages = JSON.parse(savedMessages);
                localUnsavedMessages.forEach(msg => {
                    addMessageToUI(msg.role, msg.text);
                });
                localUnsavedMessages = [];
                localStorage.removeItem('airpet_unsaved_messages');
            } catch (e) {
                console.error('Failed to parse unsaved messages:', e);
            }
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
        addMessageToUI('system', "Welcome to AIRPET AI. How can I help you with your detector geometry today?", false);
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
            addMessageToUI(msg.role === 'user' ? 'user' : 'model', text, false);
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

    currentRecentTools = [];
    currentTurn = 1;
    currentTurnLimit = turnLimit;

    const thinkingIndicator = createThinkingIndicator();
    
    try {
        const result = await APIService.streamAiChatMessage(message, model, turnLimit, (progress) => {
            updateThinkingIndicator(thinkingIndicator, progress);
        });
        removeThinkingIndicator(thinkingIndicator);
        addMessageToUI('model', result.message);
        
        if (onGeometryUpdateCallback) {
            onGeometryUpdateCallback(result);
        }
    } catch (err) {
        removeThinkingIndicator(thinkingIndicator);
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

function addMessageToUI(role, text, skipSave = false) {
    const div = document.createElement('div');
    div.className = `chat-message ${role} markdown-content`;
    
    const formattedText = marked.marked(text);
    div.innerHTML = formattedText;
    messageList.appendChild(div);
    
    if (!skipSave && (role === 'user' || role === 'model')) {
        localUnsavedMessages.push({ role, text });
        try {
            localStorage.setItem('airpet_unsaved_messages', JSON.stringify(localUnsavedMessages));
        } catch (e) {
            console.warn('Failed to save unsaved messages to localStorage:', e);
        }
    }
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

function createThinkingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'chat-message model thinking-indicator';
    indicator.id = 'ai-thinking-indicator';
    indicator.innerHTML = '<span class="thinking-text">Thinking...</span>';
    messageList.appendChild(indicator);
    scrollToBottom();
    return indicator;
}

function updateThinkingIndicator(indicator, progress) {
    if (!indicator || !indicator.isConnected) return;
    
    const thinkingText = indicator.querySelector('.thinking-text');
    
    if (progress.type === 'turn_start') {
        currentTurn = progress.turn;
        currentTurnLimit = progress.turnLimit;
        
        if (currentRecentTools.length > 0) {
            const turnBadge = `<span class="turn-badge">Turn ${currentTurn}/${currentTurnLimit}</span>`;
            const toolsHtml = currentRecentTools.map(tool => 
                `<div class="tool-entry">🛠️ ${tool}</div>`
            ).join('');
            thinkingText.innerHTML = `${turnBadge}<div class="tools-list">${toolsHtml}</div>`;
        } else {
            thinkingText.innerHTML = `<span class="turn-badge">Turn ${currentTurn}/${currentTurnLimit}</span> Processing...`;
        }
    } else if (progress.type === 'tool_calls' && progress.tools && progress.tools.length > 0) {
        currentTurn = progress.turn;
        
        if (progress.recentTools && progress.recentTools.length > 0) {
            currentRecentTools = progress.recentTools;
        } else {
            currentRecentTools = [...currentRecentTools, ...progress.tools].slice(-3);
        }
        
        const turnBadge = `<span class="turn-badge">Turn ${currentTurn}/${currentTurnLimit}</span>`;
        const toolsHtml = currentRecentTools.map(tool => 
            `<div class="tool-entry">🛠️ ${tool}</div>`
        ).join('');
        thinkingText.innerHTML = `${turnBadge}<div class="tools-list">${toolsHtml}</div>`;
    } else if (progress.type === 'paused') {
        thinkingText.innerHTML = `<span class="pause-badge">⏸️ Paused</span> ${progress.reason || 'tab hidden'}`;
    } else if (progress.type === 'resumed') {
        if (progress.recentTools && progress.recentTools.length > 0) {
            currentRecentTools = progress.recentTools;
        }
        
        const turnBadge = `<span class="turn-badge">Turn ${currentTurn}/${currentTurnLimit}</span>`;
        const toolsHtml = currentRecentTools.map(tool => 
            `<div class="tool-entry">🛠️ ${tool}</div>`
        ).join('');
        thinkingText.innerHTML = `${turnBadge}<div class="tools-list">${toolsHtml}</div>`;
    }
    
    scrollToBottom();
}

function removeThinkingIndicator(indicator) {
    if (indicator && indicator.isConnected) {
        indicator.remove();
    }
    currentRecentTools = [];
}
