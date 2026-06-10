// static/aiAssistant.js
import * as APIService from './apiService.js?v=21';
import * as UIManager from './uiManager.js';
import { formatBackendDiagnosticsError } from './backendDiagnosticsUi.js';
import {
    runtimeConfigToFormState,
    buildRuntimeConfigPayloadFromFormState,
    getLocalRuntimeBackendIds,
} from './aiRuntimeConfigUi.js';
import {
    VISUAL_SELF_CRITIQUE_DEFAULT_CAPTURE_OPTIONS,
    VISUAL_SELF_CRITIQUE_SOURCE_LABEL,
    buildAutomaticVisualSelfCritiqueDisplayMessage,
    buildAutomaticVisualSelfCritiqueGoal,
    buildVisualSelfCritiqueDisplayMessage,
    buildVisualSelfCritiqueMetadata,
    buildVisualSelfCritiquePrompt,
} from './visualSelfCritique.js?v=2';
import {
    detectorStudySummaryText,
    normalizeDetectorStudy,
} from './detectorStudyUi.js';

let messageList, promptInput, generateButton, clearButton, modelSelect, contextStatsEl;
let attachmentInput, attachButton, visualCheckButton, autoVisualCheckToggle, attachmentTray;
let executionModeSelect, studyCard, studyTitle, studyPhase, studyProgress;
let studyGoal, studySummary, studyQuietStatus, studyRefreshButton, studyNewButton;
let studyPauseButton, studyUndoPhaseButton, studyInterpretButton;
let studyReportToggle, studyReportPanel;
let isProcessing = false;
let onGeometryUpdateCallback = () => {};
let onVisualVerificationPacketRequested = null;
let localUnsavedMessages = [];
let pendingAttachments = [];
let currentRecentTools = [];
let currentTurn = 1;
let currentTurnLimit = 50;

let runtimeConfigButton, runtimeConfigStatusEl;
let runtimeConfigModal, runtimeConfigErrorEl;
let runtimeConfigReloadBtn, runtimeConfigClearBtn, runtimeConfigCancelBtn, runtimeConfigSaveBtn;
let runtimeConfigFormEls = {};
let runtimeConfigLoaded = false;
let historyLoaded = false;
let activeDetectorStudy = null;
let detectorStudyPollTimer = null;
let detectorStudyInterpretationInFlight = false;
const detectorStudyInterpretationAttemptedIds = new Set();

const AUTO_VISUAL_CHECK_STORAGE_KEY = 'airpet_auto_visual_check_enabled';
const AI_EXECUTION_MODE_STORAGE_KEY = 'airpet_ai_execution_mode';

const VISUAL_CHECK_TRIGGER_TOOLS = new Set([
    'create_primitive_solid',
    'manage_detector_feature_generator',
    'update_property',
    'manage_define',
    'manage_material',
    'modify_solid',
    'create_boolean_solid',
    'manage_logical_volume',
    'place_volume',
    'modify_physical_volume',
    'create_detector_ring',
    'delete_objects',
    'create_parameter_registry',
    'setup_param_study',
    'apply_best_result',
    'set_volume_appearance',
    'delete_detector_ring',
    'batch_geometry_update',
    'insert_physics_template',
    'manage_optical_surface',
    'manage_surface_link',
    'manage_assembly',
    'manage_ui_group',
    'manage_particle_source',
    'configure_incident_beam',
    'set_active_source',
    'rename_ui_group',
]);

export function init(callbacks) {
    messageList = document.getElementById('ai_message_list');
    promptInput = document.getElementById('ai_prompt_input');
    generateButton = document.getElementById('ai_generate_button');
    clearButton = document.getElementById('clear_chat_btn');
    modelSelect = document.getElementById('ai_model_select');
    contextStatsEl = document.getElementById('ai_context_stats');
    attachmentInput = document.getElementById('ai_attachment_input');
    attachButton = document.getElementById('ai_attach_button');
    visualCheckButton = document.getElementById('ai_visual_check_button');
    autoVisualCheckToggle = document.getElementById('ai_auto_visual_check_toggle');
    attachmentTray = document.getElementById('ai_attachment_tray');
    executionModeSelect = document.getElementById('ai_execution_mode');
    studyCard = document.getElementById('ai_study_card');
    studyTitle = document.getElementById('ai_study_title');
    studyPhase = document.getElementById('ai_study_phase');
    studyProgress = document.getElementById('ai_study_progress');
    studyGoal = document.getElementById('ai_study_goal');
    studySummary = document.getElementById('ai_study_summary');
    studyQuietStatus = document.getElementById('ai_study_quiet_status');
    studyRefreshButton = document.getElementById('ai_study_refresh');
    studyNewButton = document.getElementById('ai_study_new');
    studyPauseButton = document.getElementById('ai_study_pause');
    studyUndoPhaseButton = document.getElementById('ai_study_undo_phase');
    studyInterpretButton = document.getElementById('ai_study_interpret');
    studyReportToggle = document.getElementById('ai_study_report_toggle');
    studyReportPanel = document.getElementById('ai_study_report_panel');

    initRuntimeConfigUi();

    if (callbacks && callbacks.onGeometryUpdate) {
        onGeometryUpdateCallback = callbacks.onGeometryUpdate;
    }
    if (callbacks && typeof callbacks.onVisualVerificationPacketRequested === 'function') {
        onVisualVerificationPacketRequested = callbacks.onVisualVerificationPacketRequested;
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

    if (attachButton && attachmentInput) {
        attachButton.addEventListener('click', () => attachmentInput.click());
        attachmentInput.addEventListener('change', handleAttachmentSelection);
    }

    if (visualCheckButton) {
        visualCheckButton.addEventListener('click', handleVisualSelfCritique);
    }

    if (autoVisualCheckToggle) {
        autoVisualCheckToggle.checked = localStorage.getItem(AUTO_VISUAL_CHECK_STORAGE_KEY) === 'true';
        autoVisualCheckToggle.addEventListener('change', () => {
            localStorage.setItem(AUTO_VISUAL_CHECK_STORAGE_KEY, autoVisualCheckToggle.checked ? 'true' : 'false');
        });
    }

    if (executionModeSelect) {
        const savedMode = localStorage.getItem(AI_EXECUTION_MODE_STORAGE_KEY);
        if (['design_only', 'build_validate', 'full_study'].includes(savedMode)) {
            executionModeSelect.value = savedMode;
        }
        executionModeSelect.addEventListener('change', () => {
            localStorage.setItem(
                AI_EXECUTION_MODE_STORAGE_KEY,
                executionModeSelect.value,
            );
            updateExecutionModeHint();
        });
        updateExecutionModeHint();
    }

    if (studyRefreshButton) {
        studyRefreshButton.addEventListener('click', () => {
            refreshActiveDetectorStudy({ scheduleNext: true });
        });
    }

    if (studyNewButton) {
        studyNewButton.addEventListener('click', async () => {
            try {
                await APIService.clearActiveDetectorStudy();
                renderActiveDetectorStudy(null);
                if (promptInput) promptInput.focus();
            } catch (err) {
                UIManager.showError(`Could not start a new study: ${err.message || err}`);
            }
        });
    }

    if (studyPauseButton) {
        studyPauseButton.addEventListener('click', handleDetectorStudyPauseToggle);
    }

    if (studyUndoPhaseButton) {
        studyUndoPhaseButton.addEventListener('click', handleDetectorStudyPhaseUndo);
    }

    if (studyReportToggle) {
        studyReportToggle.addEventListener('click', () => {
            if (!studyReportPanel) return;
            studyReportPanel.hidden = !studyReportPanel.hidden;
            studyReportToggle.textContent = studyReportPanel.hidden
                ? 'View report'
                : 'Hide report';
        });
    }

    if (studyInterpretButton) {
        studyInterpretButton.addEventListener('click', () => {
            if (!activeDetectorStudy) return;
            detectorStudyInterpretationAttemptedIds.delete(
                activeDetectorStudy.study_id,
            );
            runDetectorStudyInterpretation({ force: true });
        });
    }

    if (modelSelect) {
        modelSelect.addEventListener('change', () => {
            refreshContextStats();
            UIManager.updateAiBackendStatus?.();
        });
    }

    // Load existing history
    loadHistory();
    loadRuntimeConfigProfile({ quiet: true });
    refreshActiveDetectorStudy({ scheduleNext: true });
}

function getExecutionMode() {
    const mode = executionModeSelect?.value;
    return ['design_only', 'build_validate', 'full_study'].includes(mode)
        ? mode
        : 'build_validate';
}

function updateExecutionModeHint() {
    if (!studyQuietStatus || activeDetectorStudy) return;
    const hints = {
        design_only: 'AIRPET will design and edit, but will not create a managed study.',
        build_validate: 'AIRPET will build, visually inspect, and preflight the detector.',
        full_study: 'AIRPET will build, validate, run, monitor, and summarize the study.',
    };
    studyQuietStatus.textContent = hints[getExecutionMode()];
}

function renderActiveDetectorStudy(study) {
    activeDetectorStudy = normalizeDetectorStudy(study);
    if (!studyCard) return;
    if (!activeDetectorStudy) {
        studyCard.hidden = true;
        studyCard.classList.remove('complete', 'needs-attention');
        if (studyReportPanel) {
            studyReportPanel.hidden = true;
            studyReportPanel.textContent = '';
        }
        updateExecutionModeHint();
        return;
    }

    studyCard.hidden = false;
    studyCard.classList.toggle(
        'complete',
        activeDetectorStudy.phase === 'COMPLETE',
    );
    studyCard.classList.toggle(
        'needs-attention',
        activeDetectorStudy.phase === 'NEEDS_ATTENTION',
    );
    if (studyTitle) {
        studyTitle.textContent = activeDetectorStudy.title || 'Detector study';
    }
    if (studyPhase) {
        studyPhase.textContent = activeDetectorStudy.phaseLabel;
    }
    if (studyProgress) {
        studyProgress.style.width = `${activeDetectorStudy.progress}%`;
    }
    if (studyGoal) {
        studyGoal.textContent = activeDetectorStudy.goal;
        studyGoal.title = activeDetectorStudy.goal;
    }
    const summaryText = detectorStudySummaryText(activeDetectorStudy);
    if (studySummary) studySummary.textContent = summaryText;
    if (studyQuietStatus) {
        studyQuietStatus.textContent = `${activeDetectorStudy.phaseLabel}: ${summaryText}`;
    }
    if (studyPauseButton) {
        studyPauseButton.textContent = activeDetectorStudy.paused ? 'Resume' : 'Pause';
        studyPauseButton.disabled = ['RUNNING', 'ANALYZING', 'COMPLETE'].includes(
            activeDetectorStudy.phase,
        );
    }
    if (studyUndoPhaseButton) {
        studyUndoPhaseButton.disabled = (
            activeDetectorStudy.phase === 'RUNNING'
            || activeDetectorStudy.phase === 'ANALYZING'
            || activeDetectorStudy.checkpoints.length === 0
        );
    }
    if (studyReportToggle) {
        studyReportToggle.hidden = !activeDetectorStudy.report;
    }
    if (studyInterpretButton) {
        studyInterpretButton.hidden = (
            activeDetectorStudy.coordinator?.interpretation_status !== 'failed'
        );
    }
    if (studyReportPanel) {
        studyReportPanel.textContent = formatDetectorStudyReport(
            activeDetectorStudy.report,
        );
        if (!activeDetectorStudy.report) studyReportPanel.hidden = true;
    }
}

function formatDetectorStudyReport(report) {
    if (!report || typeof report !== 'object') return '';
    const brief = report.brief || {};
    const simulation = report.simulation || {};
    const analysis = report.analysis || {};
    const summary = analysis.summary || {};
    const criteria = Array.isArray(brief.success_criteria)
        ? brief.success_criteria
        : [];
    const warnings = Array.isArray(report.warnings) ? report.warnings : [];
    return [
        `Goal: ${brief.goal || '(not recorded)'}`,
        `Success criteria: ${criteria.length ? criteria.join('; ') : '(not recorded)'}`,
        `Simulation: ${simulation.status || 'Unknown'}`
            + (simulation.total_events ? `, ${simulation.total_events} events` : ''),
        `Recorded hits: ${Number.isFinite(Number(summary.total_hits)) ? Number(summary.total_hits) : 'unavailable'}`,
        `Warnings: ${warnings.length ? warnings.join('; ') : 'none'}`,
        '',
        'AI conclusion:',
        report.ai_conclusion || 'Pending model interpretation.',
    ].join('\n');
}

async function handleDetectorStudyPauseToggle() {
    if (!activeDetectorStudy || isProcessing) return;
    try {
        const action = activeDetectorStudy.paused ? 'resume' : 'pause';
        const response = await APIService.updateDetectorStudy(
            activeDetectorStudy.study_id,
            { action },
        );
        renderActiveDetectorStudy(response?.study || null);
        scheduleDetectorStudyPoll();
    } catch (err) {
        UIManager.showError(`Could not update study orchestration: ${err.message || err}`);
    }
}

async function handleDetectorStudyPhaseUndo() {
    if (!activeDetectorStudy || isProcessing) return;
    if (!confirm('Restore the latest AIRPET study checkpoint? Later geometry and run results will be discarded.')) {
        return;
    }
    try {
        const response = await APIService.updateDetectorStudy(
            activeDetectorStudy.study_id,
            { action: 'restore_checkpoint' },
        );
        renderActiveDetectorStudy(response?.study || null);
        if (onGeometryUpdateCallback) {
            await onGeometryUpdateCallback(response);
        }
        await loadHistory(true);
        scheduleDetectorStudyPoll();
    } catch (err) {
        UIManager.showError(`Could not restore the study checkpoint: ${err.message || err}`);
    }
}

function scheduleDetectorStudyPoll() {
    if (detectorStudyPollTimer) {
        clearTimeout(detectorStudyPollTimer);
        detectorStudyPollTimer = null;
    }
    if (!activeDetectorStudy || activeDetectorStudy.terminal) return;
    const delay = ['RUNNING', 'ANALYZING'].includes(activeDetectorStudy.phase)
        ? 1500
        : 6000;
    detectorStudyPollTimer = setTimeout(() => {
        refreshActiveDetectorStudy({ scheduleNext: true });
    }, delay);
}

async function refreshActiveDetectorStudy({ scheduleNext = false } = {}) {
    try {
        const response = await APIService.getActiveDetectorStudy();
        renderActiveDetectorStudy(response?.study || null);
        queueDetectorStudyInterpretation();
    } catch (err) {
        if (studyQuietStatus) {
            studyQuietStatus.textContent = 'Study status is temporarily unavailable.';
        }
    } finally {
        if (scheduleNext) scheduleDetectorStudyPoll();
    }
}

function queueDetectorStudyInterpretation() {
    if (
        detectorStudyInterpretationInFlight
        || isProcessing
        || activeDetectorStudy?.coordinator?.interpretation_status !== 'pending'
        || detectorStudyInterpretationAttemptedIds.has(activeDetectorStudy?.study_id)
    ) {
        return;
    }
    window.setTimeout(() => {
        runDetectorStudyInterpretation();
    }, 0);
}

async function runDetectorStudyInterpretation({ force = false } = {}) {
    const interpretationStatus = (
        activeDetectorStudy?.coordinator?.interpretation_status
    );
    if (
        detectorStudyInterpretationInFlight
        || isProcessing
        || (
            interpretationStatus !== 'pending'
            && !(force && interpretationStatus === 'failed')
        )
        || detectorStudyInterpretationAttemptedIds.has(activeDetectorStudy?.study_id)
    ) {
        return;
    }
    const model = UIManager.getAiSelectedModel();
    if (!model || model === '--export--') return;

    const studyId = activeDetectorStudy.study_id;
    detectorStudyInterpretationAttemptedIds.add(studyId);
    detectorStudyInterpretationInFlight = true;
    setLoading(true);
    if (studyQuietStatus) {
        studyQuietStatus.textContent = 'Interpreting the completed study against its success criteria...';
    }
    try {
        const prompt = [
            'Interpret the completed AIRPET detector study report.',
            'Judge the result explicitly against every recorded success criterion.',
            'Distinguish measured evidence from assumptions, mention important warnings,',
            'and give a concise conclusion plus the most useful next action.',
            'Do not call tools or claim evidence that is not present in the report.',
            '',
            JSON.stringify(activeDetectorStudy.report || {}, null, 2),
        ].join('\n');
        const result = await APIService.streamAiChatMessage(
            prompt,
            model,
            1,
            null,
            [],
            {
                detectorStudyId: studyId,
                studyInterpretationId: studyId,
                disableTools: true,
                requireJsonMode: false,
                clientDisplayMessage: 'AIRPET automatic detector study interpretation',
            },
        );
        if (result?.message) {
            addMessageToUI('model', `**Detector study conclusion**\n\n${result.message}`);
        }
    } catch (err) {
        console.warn('Automatic detector study interpretation failed:', err);
    } finally {
        detectorStudyInterpretationInFlight = false;
        setLoading(false);
        await refreshActiveDetectorStudy({ scheduleNext: false });
    }
}

async function ensureDetectorStudyForTurn(message, attachments) {
    const executionMode = getExecutionMode();
    if (executionMode === 'design_only') return null;
    const response = await APIService.ensureDetectorStudy({
        goal: message,
        execution_mode: executionMode,
        study_id: activeDetectorStudy?.study_id || null,
        continue_active: true,
        attachments: (attachments || []).map((attachment) => ({
            artifact_id: attachment.artifact_id || null,
            original_filename: attachment.original_filename || null,
            mime_type: attachment.mime_type || null,
        })),
    });
    renderActiveDetectorStudy(response?.study || null);
    scheduleDetectorStudyPoll();
    return response?.study || null;
}

function initRuntimeConfigUi() {
    runtimeConfigButton = document.getElementById('ai_runtime_config_btn');
    runtimeConfigStatusEl = document.getElementById('ai_runtime_config_status');
    runtimeConfigModal = document.getElementById('aiRuntimeConfigModal');
    runtimeConfigErrorEl = document.getElementById('ai_runtime_config_error');
    runtimeConfigReloadBtn = document.getElementById('ai_runtime_config_reload_btn');
    runtimeConfigClearBtn = document.getElementById('ai_runtime_config_clear_btn');
    runtimeConfigCancelBtn = document.getElementById('ai_runtime_config_cancel_btn');
    runtimeConfigSaveBtn = document.getElementById('ai_runtime_config_save_btn');

    runtimeConfigFormEls = {};
    getLocalRuntimeBackendIds().forEach((backendId) => {
        runtimeConfigFormEls[backendId] = {
            enabled: document.getElementById(`ai_runtime_${backendId}_enabled`),
            base_url: document.getElementById(`ai_runtime_${backendId}_base_url`),
            endpoint_path: document.getElementById(`ai_runtime_${backendId}_endpoint_path`),
            model: document.getElementById(`ai_runtime_${backendId}_model`),
            timeout_seconds: document.getElementById(`ai_runtime_${backendId}_timeout_seconds`),
            max_retries: document.getElementById(`ai_runtime_${backendId}_max_retries`),
            retry_backoff_seconds: document.getElementById(`ai_runtime_${backendId}_retry_backoff_seconds`),
            verify_tls: document.getElementById(`ai_runtime_${backendId}_verify_tls`),
            supports_vision: document.getElementById(`ai_runtime_${backendId}_supports_vision`),
            headers_json: document.getElementById(`ai_runtime_${backendId}_headers_json`),
        };
    });

    setRuntimeConfigStatus('Runtime profile: loading…', 'info');

    if (runtimeConfigButton) {
        runtimeConfigButton.addEventListener('click', () => {
            if (!runtimeConfigModal) return;
            runtimeConfigModal.style.display = 'block';
            setRuntimeConfigError('', 'neutral');
            if (!runtimeConfigLoaded) {
                loadRuntimeConfigProfile({ quiet: true });
            }
        });
    }

    if (runtimeConfigCancelBtn) {
        runtimeConfigCancelBtn.addEventListener('click', () => {
            if (runtimeConfigModal) runtimeConfigModal.style.display = 'none';
        });
    }

    if (runtimeConfigReloadBtn) {
        runtimeConfigReloadBtn.addEventListener('click', () => {
            loadRuntimeConfigProfile({ quiet: false });
        });
    }

    if (runtimeConfigSaveBtn) {
        runtimeConfigSaveBtn.addEventListener('click', handleSaveRuntimeConfigProfile);
    }

    if (runtimeConfigClearBtn) {
        runtimeConfigClearBtn.addEventListener('click', handleClearRuntimeConfigProfile);
    }
}

function setRuntimeConfigStatus(message, kind = 'info') {
    if (!runtimeConfigStatusEl) return;

    runtimeConfigStatusEl.className = 'ai-model-info ai-runtime-config-status';
    runtimeConfigStatusEl.classList?.add(`status-${kind}`);
    runtimeConfigStatusEl.textContent = message;
}

function setRuntimeConfigError(message, kind = 'error') {
    if (!runtimeConfigErrorEl) return;

    runtimeConfigErrorEl.className = `ai-runtime-feedback ${kind}`;
    runtimeConfigErrorEl.textContent = message || '';
    runtimeConfigErrorEl.style.display = message ? 'block' : 'none';
}

function setRuntimeConfigFormBusy(isBusy) {
    const fieldGroups = Object.values(runtimeConfigFormEls || {});
    fieldGroups.forEach((fields) => {
        Object.values(fields || {}).forEach((el) => {
            if (el) el.disabled = isBusy;
        });
    });

    if (runtimeConfigSaveBtn) runtimeConfigSaveBtn.disabled = isBusy;
    if (runtimeConfigReloadBtn) runtimeConfigReloadBtn.disabled = isBusy;
    if (runtimeConfigClearBtn) runtimeConfigClearBtn.disabled = isBusy;
}

function collectRuntimeConfigFormState() {
    const backends = {};

    getLocalRuntimeBackendIds().forEach((backendId) => {
        const fields = runtimeConfigFormEls[backendId] || {};
        backends[backendId] = {
            enabled: !!fields.enabled?.checked,
            base_url: fields.base_url?.value ?? '',
            endpoint_path: fields.endpoint_path?.value ?? '',
            model: fields.model?.value ?? '',
            timeout_seconds: fields.timeout_seconds?.value ?? '',
            max_retries: fields.max_retries?.value ?? '',
            retry_backoff_seconds: fields.retry_backoff_seconds?.value ?? '',
            verify_tls: !!fields.verify_tls?.checked,
            supports_vision: !!fields.supports_vision?.checked,
            headers_json: fields.headers_json?.value ?? '',
        };
    });

    return { backends };
}

function applyRuntimeConfigFormState(formState) {
    const backendForms = formState?.backends || {};

    getLocalRuntimeBackendIds().forEach((backendId) => {
        const fields = runtimeConfigFormEls[backendId] || {};
        const values = backendForms[backendId] || {};

        if (fields.enabled) fields.enabled.checked = !!values.enabled;
        if (fields.base_url) fields.base_url.value = values.base_url ?? '';
        if (fields.endpoint_path) fields.endpoint_path.value = values.endpoint_path ?? '';
        if (fields.model) fields.model.value = values.model ?? '';
        if (fields.timeout_seconds) fields.timeout_seconds.value = values.timeout_seconds ?? '';
        if (fields.max_retries) fields.max_retries.value = values.max_retries ?? '';
        if (fields.retry_backoff_seconds) fields.retry_backoff_seconds.value = values.retry_backoff_seconds ?? '';
        if (fields.verify_tls) fields.verify_tls.checked = !!values.verify_tls;
        if (fields.supports_vision) fields.supports_vision.checked = !!values.supports_vision;
        if (fields.headers_json) fields.headers_json.value = values.headers_json ?? '{}';
    });
}

function hasSessionRuntimeOverrides(runtimeConfig) {
    if (!runtimeConfig || typeof runtimeConfig !== 'object') return false;
    const backendMap = runtimeConfig.backends && typeof runtimeConfig.backends === 'object'
        ? runtimeConfig.backends
        : runtimeConfig;

    return getLocalRuntimeBackendIds().some((backendId) => {
        const value = backendMap[backendId];
        return value && typeof value === 'object' && Object.keys(value).length > 0;
    });
}

async function refreshRuntimeConfigDiagnostics() {
    try {
        const diagResponse = await APIService.getAiBackendDiagnostics(['llama_cpp', 'lm_studio']);
        if (diagResponse?.success && Array.isArray(diagResponse.diagnostics)) {
            diagResponse.diagnostics.forEach(diagnostic => {
                UIManager.upsertAiBackendDiagnostic?.(diagnostic);
            });
        }
    } catch (_diagErr) {
    }
}

async function loadRuntimeConfigProfile({ quiet = false } = {}) {
    if (!quiet) {
        setRuntimeConfigError('', 'neutral');
    }

    setRuntimeConfigFormBusy(true);
    try {
        const response = await APIService.getAiBackendRuntimeConfig();
        const runtimeConfig = response?.runtime_config || {};
        applyRuntimeConfigFormState(runtimeConfigToFormState(runtimeConfig));
        runtimeConfigLoaded = true;

        if (hasSessionRuntimeOverrides(runtimeConfig)) {
            setRuntimeConfigStatus('Runtime profile: using saved profile (session-scoped; request overrides win).', 'ok');
        } else {
            setRuntimeConfigStatus('Runtime profile: using built-in defaults (no saved session profile).', 'info');
        }

        await refreshRuntimeConfigDiagnostics();

        if (!quiet) {
            setRuntimeConfigError('Runtime profile reloaded from this session. Saved defaults are session-scoped, and request overrides still take precedence.', 'ok');
        }
    } catch (err) {
        const message = `Failed to load runtime profile: ${err.message || err}`;
        setRuntimeConfigStatus('Runtime profile: load failed.', 'error');
        setRuntimeConfigError(message, 'error');
    } finally {
        setRuntimeConfigFormBusy(false);
    }
}

async function handleSaveRuntimeConfigProfile() {
    setRuntimeConfigError('', 'neutral');

    const payloadResult = buildRuntimeConfigPayloadFromFormState(collectRuntimeConfigFormState());
    if (!payloadResult.ok) {
        setRuntimeConfigStatus('Runtime profile: validation error.', 'error');
        setRuntimeConfigError(payloadResult.error, 'error');
        return;
    }

    setRuntimeConfigFormBusy(true);
    try {
        const response = await APIService.saveAiBackendRuntimeConfig(payloadResult.runtimeConfig);
        const runtimeConfig = response?.runtime_config || {};

        applyRuntimeConfigFormState(runtimeConfigToFormState(runtimeConfig));
        runtimeConfigLoaded = true;

        setRuntimeConfigStatus('Runtime profile: using saved profile (session-scoped; request overrides win).', 'ok');
        setRuntimeConfigError('Saved. These defaults now apply to diagnostics/chat for this session unless a request sends explicit runtime overrides.', 'ok');

        await refreshRuntimeConfigDiagnostics();
    } catch (err) {
        const message = `Failed to save runtime profile: ${err.message || err}`;
        setRuntimeConfigStatus('Runtime profile: save failed.', 'error');
        setRuntimeConfigError(message, 'error');
    } finally {
        setRuntimeConfigFormBusy(false);
    }
}

async function handleClearRuntimeConfigProfile() {
    const shouldClear = confirm('Clear the saved local runtime profile for this session and revert to defaults?');
    if (!shouldClear) return;

    setRuntimeConfigError('', 'neutral');
    setRuntimeConfigFormBusy(true);

    try {
        const response = await APIService.clearAiBackendRuntimeConfig();
        const runtimeConfig = response?.runtime_config || {};

        applyRuntimeConfigFormState(runtimeConfigToFormState(runtimeConfig));
        runtimeConfigLoaded = true;

        setRuntimeConfigStatus('Runtime profile: using built-in defaults (saved session profile cleared).', 'info');
        setRuntimeConfigError('Saved session profile cleared. Built-in backend defaults are now active for diagnostics/chat.', 'ok');

        await refreshRuntimeConfigDiagnostics();
    } catch (err) {
        const message = `Failed to clear runtime profile: ${err.message || err}`;
        setRuntimeConfigStatus('Runtime profile: clear failed.', 'error');
        setRuntimeConfigError(message, 'error');
    } finally {
        setRuntimeConfigFormBusy(false);
    }
}

async function loadHistory(force = false) {
    // Prevent duplicate loading on initial page load
    if (!force && historyLoaded) {
        console.log('loadHistory: skipped (already loaded)');
        return;
    }
    
    try {
        console.log('loadHistory: fetching history...', { force, historyLoaded });
        const res = await APIService.getAiChatHistory();
        console.log('loadHistory: received history with', res.history?.length || 0, 'messages');
        const serverHistoryLength = Array.isArray(res.history) ? res.history.length : 0;
        const savedMessages = localStorage.getItem('airpet_unsaved_messages');

        if (res.history) {
            renderHistory(res.history);
            historyLoaded = true;
        }

        // Only load unsaved messages from localStorage if history is empty (no server data).
        // Once the server history is available, treat it as the source of truth and
        // clear the in-memory fallback cache so the next refresh starts clean.
        if (savedMessages && serverHistoryLength === 0) {
            try {
                localUnsavedMessages = JSON.parse(savedMessages);
                localUnsavedMessages.forEach(msg => {
                    addMessageToUI(msg.role, msg.text);
                });
                localUnsavedMessages = [];
            } catch (e) {
                console.error('Failed to parse unsaved messages:', e);
                localUnsavedMessages = [];
            } finally {
                localStorage.removeItem('airpet_unsaved_messages');
            }
        } else {
            localUnsavedMessages = [];
            if (savedMessages) {
                // Clear localStorage since messages are now on the server
                localStorage.removeItem('airpet_unsaved_messages');
            }
        }
    } catch (err) {
        console.error("Failed to load chat history:", err);
    } finally {
        refreshContextStats();
    }
}

export function reloadHistory() {
    loadHistory(true);
}

function getMessageDisplayText(msg) {
    if (!msg) return '';
    if (msg.role === 'user' && msg.metadata && msg.metadata.original_message) {
        return msg.metadata.original_message;
    }
    return msg.parts ? msg.parts.map(p => p.text || '').join('\n').trim() : (msg.content || '').trim();
}

function getMessageAttachments(msg) {
    const attachments = msg?.metadata?.ai_attachments;
    return Array.isArray(attachments) ? attachments : [];
}

function getIntermediateToolNames(msg) {
    const toolNames = [];

    if (Array.isArray(msg?.tool_calls)) {
        msg.tool_calls.forEach((toolCall) => {
            const toolName = toolCall?.function?.name || toolCall?.name;
            if (toolName) toolNames.push(toolName);
        });
    }

    if (Array.isArray(msg?.parts)) {
        msg.parts.forEach((part) => {
            const toolName = part?.function_call?.name;
            if (toolName) toolNames.push(toolName);
        });
    }

    return [...new Set(toolNames)];
}

function renderHistory(history) {
    console.log('renderHistory: called with', history.length, 'messages');
    messageList.innerHTML = '';
    // Skip the first two messages (system instructions)
    if (history.length <= 2) {
        addMessageToUI('system', "AIRPET AI", false);
        return;
    }
    
    // Group messages by turn: [user msg, intermediate msgs..., final msg]
    const turns = [];
    let currentTurn = [];
    
    history.slice(2).forEach(msg => {
        // Skip tool results and system messages
        if (msg.role === 'tool' || msg.role === 'system') return;
        
        const isUser = msg.role === 'user';
        const isIntermediate = (msg.role === 'assistant' || msg.role === 'model') && msg.metadata && msg.metadata._intermediate;
        const isFinal = (msg.role === 'assistant' || msg.role === 'model') && (!msg.metadata || !msg.metadata._intermediate);
        
        if (isUser) {
            // Start new turn with user message
            if (currentTurn.length > 0) {
                turns.push(currentTurn);
            }
            currentTurn = [{ type: 'user', msg }];
        } else if (isIntermediate) {
            // Add intermediate message to current turn
            currentTurn.push({ type: 'intermediate', msg });
        } else if (isFinal) {
            // Add final message and close turn
            currentTurn.push({ type: 'final', msg });
            turns.push(currentTurn);
            currentTurn = [];
        }
    });

    if (currentTurn.length > 0) {
        turns.push(currentTurn);
    }
    
    // Render each turn
    turns.forEach(turn => {
        const finalItem = turn.find(item => item.type === 'final');
        const intermediates = turn.filter(item => item.type === 'intermediate');
        const userItem = turn.find(item => item.type === 'user');
        const recoveredIntermediate = !finalItem
            ? [...turn]
                .reverse()
                .find(item => item.type === 'intermediate' && getMessageDisplayText(item.msg))
            : null;

        const userText = getMessageDisplayText(userItem?.msg);
        if (userText && !userText.startsWith('[System Context Update]')) {
            addMessageToUI('user', userText, false, getMessageAttachments(userItem?.msg));
        }

        if (intermediates.length > 0) {
            addThinkingDropdown(intermediates);
        }

        const finalText = getMessageDisplayText(finalItem?.msg);
        if (finalText && !finalText.startsWith('[System Context Update]')) {
            addMessageToUI('model', finalText, false);
        }

        if (!finalItem && recoveredIntermediate) {
            const recoveredText = getMessageDisplayText(recoveredIntermediate.msg);
            if (recoveredText && !recoveredText.startsWith('[System Context Update]')) {
                addMessageToUI('model', recoveredText, false);
            }
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

function isAutoVisualCheckEnabled() {
    return Boolean(autoVisualCheckToggle?.checked);
}

function shouldRunAutoVisualCheckAfterTools(toolsUsed) {
    if (!isAutoVisualCheckEnabled()) return false;
    if (typeof onVisualVerificationPacketRequested !== 'function') return false;
    return [...toolsUsed].some((toolName) => VISUAL_CHECK_TRIGGER_TOOLS.has(toolName));
}

function waitForRenderFrames(frameCount = 2) {
    let promise = Promise.resolve();
    for (let i = 0; i < frameCount; i += 1) {
        promise = promise.then(() => new Promise((resolve) => requestAnimationFrame(resolve)));
    }
    return promise;
}

function normalizeAiTurnLimit(value, fallback = 10) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.min(50, Math.max(1, parsed));
}

async function handleDynamicVisualVerificationRequest(requestPayload) {
    const requestId = requestPayload?.request_id;
    if (!requestId) {
        throw new Error('AI visual verification request is missing request_id.');
    }
    if (typeof onVisualVerificationPacketRequested !== 'function') {
        throw new Error('Visual verification capture is not available in this AIRPET session.');
    }

    UIManager.showTemporaryStatus?.('AI requested a live visual checkpoint. Updating scene...', 1800);
    if (onGeometryUpdateCallback && (requestPayload.project_state || requestPayload.scene_update)) {
        await onGeometryUpdateCallback(requestPayload);
    }
    await waitForRenderFrames(2);

    const captureOptions = {
        ...VISUAL_SELF_CRITIQUE_DEFAULT_CAPTURE_OPTIONS,
        ...(requestPayload.capture_options || {}),
    };
    const packet = await onVisualVerificationPacketRequested(captureOptions);
    const uploadedArtifacts = await uploadVisualVerificationPacketImages(packet);
    const packetMetadata = buildVisualSelfCritiqueMetadata(packet, uploadedArtifacts);
    const attachmentIds = uploadedArtifacts.map((item) => item.artifact_id).filter(Boolean);

    await APIService.completeAiVisualVerificationRequest(requestId, {
        success: true,
        reason: requestPayload.reason || null,
        questions: Array.isArray(requestPayload.questions) ? requestPayload.questions : [],
        focus_component_ids: Array.isArray(requestPayload.focus_component_ids) ? requestPayload.focus_component_ids : [],
        packet_metadata: packetMetadata,
        attachment_ids: attachmentIds,
        attachments: uploadedArtifacts.map((item) => ({
            artifact_id: item.artifact_id,
            visual_verification_view: item.visual_verification_view || null,
        })),
    });
    UIManager.showTemporaryStatus?.('AI visual checkpoint captured and returned to the model.', 1800);
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
    const turnLimit = normalizeAiTurnLimit(turnLimitInput ? turnLimitInput.value : null, 10);

    setLoading(true);
    const attachmentsForTurn = [...pendingAttachments];
    const attachmentIds = attachmentsForTurn.map(item => item.artifact_id).filter(Boolean);

    addMessageToUI('user', message, false, attachmentsForTurn);
    promptInput.value = '';
    clearPendingAttachments();
    scrollToBottom();

    currentRecentTools = [];
    currentTurn = 1;
    currentTurnLimit = turnLimit;
    const toolsUsed = new Set();

    const thinkingIndicator = createThinkingIndicator();
    
    try {
        const study = await ensureDetectorStudyForTurn(
            message,
            attachmentsForTurn,
        );
        const result = await APIService.streamAiChatMessage(message, model, turnLimit, (progress) => {
            if (progress?.type === 'tool_calls' && Array.isArray(progress.tools)) {
                progress.tools.forEach((toolName) => toolsUsed.add(toolName));
            }
            updateThinkingIndicator(thinkingIndicator, progress);
        }, attachmentIds, {
            onVisualVerificationRequest: handleDynamicVisualVerificationRequest,
            detectorStudyId: study?.study_id || null,
            executionMode: getExecutionMode(),
        });
        removeThinkingIndicator(thinkingIndicator);
        addMessageToUI('model', result.message);
        
        if (onGeometryUpdateCallback) {
            try {
                await onGeometryUpdateCallback(result);
            } catch (syncErr) {
                console.error('AI geometry refresh failed:', syncErr);
                UIManager.showError("AI response applied, but the project refresh failed: " + (syncErr.message || syncErr));
            }
        }
        await loadHistory(true);
        await refreshActiveDetectorStudy({ scheduleNext: true });
        if (shouldRunAutoVisualCheckAfterTools(toolsUsed)) {
            await runVisualSelfCritique({
                automatic: true,
                userGoal: buildAutomaticVisualSelfCritiqueGoal({
                    originalUserMessage: message,
                    toolsUsed: [...toolsUsed],
                }),
                displayMessage: buildAutomaticVisualSelfCritiqueDisplayMessage(message),
                turnLimit,
            });
        }
    } catch (err) {
        removeThinkingIndicator(thinkingIndicator);
        await handleAiChatError(err, {
            attachmentIds,
            attachmentsForTurn,
            restorePendingAttachments: true,
        });
    } finally {
        setLoading(false);
        queueDetectorStudyInterpretation();
        scrollToBottom();
        refreshContextStats();
    }
}

async function handleAiChatError(err, {
    attachmentIds = [],
    attachmentsForTurn = [],
    restorePendingAttachments = false,
} = {}) {
    if (restorePendingAttachments && attachmentIds.length > 0 && pendingAttachments.length === 0) {
        pendingAttachments = attachmentsForTurn;
        renderPendingAttachments();
    }

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
        UIManager.showError("AI Error: " + (err.message || err));
        addMessageToUI('system', "Error: " + (err.message || err));
    }
}

function visualVerificationDataUrlToFile(dataUrl, filename) {
    const parts = String(dataUrl || '').split(',');
    if (parts.length < 2 || !parts[0].startsWith('data:')) {
        throw new Error(`Visual verification view ${filename} is missing PNG image data.`);
    }

    const mimeMatch = parts[0].match(/^data:([^;]+);base64$/);
    const mimeType = mimeMatch ? mimeMatch[1] : 'image/png';
    const binary = atob(parts.slice(1).join(','));
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i);
    }

    return new File([bytes], filename, { type: mimeType });
}

async function uploadVisualVerificationPacketImages(packet) {
    const uploaded = [];
    const views = Array.isArray(packet?.views) ? packet.views : [];

    for (const view of views) {
        if (!view?.image?.data_url) continue;
        const safeViewName = String(view.name || `view_${uploaded.length + 1}`)
            .replace(/[^a-z0-9_-]+/gi, '_')
            .replace(/^_+|_+$/g, '') || `view_${uploaded.length + 1}`;
        const file = visualVerificationDataUrlToFile(
            view.image.data_url,
            `airpet_visual_verification_${safeViewName}.png`,
        );
        const response = await APIService.uploadAiArtifact(file, `${VISUAL_SELF_CRITIQUE_SOURCE_LABEL}:${safeViewName}`);
        if (response?.success && response.artifact) {
            uploaded.push({
                ...response.artifact,
                visual_verification_view: view.name || safeViewName,
            });
        }
    }

    if (uploaded.length === 0) {
        throw new Error('No visual verification screenshots were captured for AI review.');
    }

    return uploaded;
}

async function handleVisualSelfCritique() {
    if (isProcessing) return;

    const userGoal = promptInput.value.trim();
    await runVisualSelfCritique({
        automatic: false,
        userGoal,
        displayMessage: buildVisualSelfCritiqueDisplayMessage(userGoal),
    });
}

async function runVisualSelfCritique({
    automatic = false,
    userGoal = '',
    displayMessage = null,
    turnLimit = null,
} = {}) {
    if (typeof onVisualVerificationPacketRequested !== 'function') {
        UIManager.showError('Visual verification capture is not available yet.');
        return;
    }

    const model = UIManager.getAiSelectedModel();
    if (!model || model === '--export--') {
        UIManager.showError("Please select a valid vision-capable AI model for visual check.");
        return;
    }

    const turnLimitInput = document.getElementById('ai_turn_limit');
    const resolvedTurnLimit = Number.isFinite(Number(turnLimit))
        ? normalizeAiTurnLimit(turnLimit, 10)
        : normalizeAiTurnLimit(turnLimitInput ? turnLimitInput.value : null, 10);

    setLoading(true);
    setVisualCheckBusy(true);
    currentRecentTools = [];
    currentTurn = 1;
    currentTurnLimit = resolvedTurnLimit;
    let thinkingIndicator = null;

    try {
        UIManager.showTemporaryStatus?.(
            automatic
                ? 'Auto visual check: capturing current AIRPET views...'
                : 'Capturing visual verification views...',
            1800,
        );
        const packet = await onVisualVerificationPacketRequested({
            ...VISUAL_SELF_CRITIQUE_DEFAULT_CAPTURE_OPTIONS,
        });
        const uploadedArtifacts = await uploadVisualVerificationPacketImages(packet);
        const packetMetadata = buildVisualSelfCritiqueMetadata(packet, uploadedArtifacts);
        const message = buildVisualSelfCritiquePrompt({
            packetMetadata,
            userGoal,
            allowRepairs: automatic,
        });
        const messageForDisplay = displayMessage || buildVisualSelfCritiqueDisplayMessage(userGoal);
        const attachmentIds = uploadedArtifacts.map((item) => item.artifact_id).filter(Boolean);

        addMessageToUI('user', messageForDisplay, false, uploadedArtifacts);
        if (!automatic) {
            promptInput.value = '';
        }
        scrollToBottom();
        thinkingIndicator = createThinkingIndicator();

        const result = await APIService.streamAiChatMessage(
            message,
            model,
            resolvedTurnLimit,
            (progress) => updateThinkingIndicator(thinkingIndicator, progress),
            attachmentIds,
            {
                disableTools: !automatic,
                requireTools: automatic,
                requireJsonMode: automatic,
                requireVision: true,
                clientDisplayMessage: messageForDisplay,
                onVisualVerificationRequest: handleDynamicVisualVerificationRequest,
            },
        );

        removeThinkingIndicator(thinkingIndicator);
        addMessageToUI('model', result.message);

        if (onGeometryUpdateCallback) {
            try {
                await onGeometryUpdateCallback(result);
            } catch (syncErr) {
                console.error('Visual self-critique geometry refresh failed:', syncErr);
                UIManager.showError("Visual check applied, but the project refresh failed: " + (syncErr.message || syncErr));
            }
        }
        await loadHistory(true);
    } catch (err) {
        removeThinkingIndicator(thinkingIndicator);
        await handleAiChatError(err);
    } finally {
        setLoading(false);
        setVisualCheckBusy(false);
        scrollToBottom();
        refreshContextStats();
    }
}

async function handleAttachmentSelection(event) {
    const files = Array.from(event.target?.files || []);
    if (!files.length) return;

    setAttachmentUploadBusy(true);
    try {
        for (const file of files) {
            const response = await APIService.uploadAiArtifact(file, 'chat-attachment');
            if (response?.success && response.artifact) {
                pendingAttachments.push(response.artifact);
            }
        }
        renderPendingAttachments();
    } catch (err) {
        UIManager.showError(`Failed to attach file: ${err.message || err}`);
    } finally {
        if (attachmentInput) attachmentInput.value = '';
        setAttachmentUploadBusy(false);
    }
}

function setAttachmentUploadBusy(isBusy) {
    if (attachButton) {
        attachButton.disabled = isBusy || isProcessing;
        attachButton.textContent = isBusy ? 'Uploading...' : 'Attach';
    }
}

function setVisualCheckBusy(isBusy) {
    if (visualCheckButton) {
        visualCheckButton.disabled = isBusy || isProcessing;
        visualCheckButton.textContent = isBusy ? 'Checking...' : 'Visual Check';
    }
}

function renderPendingAttachments() {
    if (!attachmentTray) return;

    attachmentTray.innerHTML = '';
    attachmentTray.classList.toggle('has-attachments', pendingAttachments.length > 0);

    pendingAttachments.forEach((attachment, index) => {
        const chip = document.createElement('div');
        chip.className = 'ai-attachment-chip';

        const label = document.createElement('span');
        label.textContent = attachment.original_filename || attachment.artifact_id || 'attachment';
        label.title = `${attachment.mime_type || 'file'} ${attachment.artifact_id || ''}`.trim();

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'ai-attachment-remove';
        remove.setAttribute('aria-label', `Remove ${label.textContent}`);
        remove.textContent = 'x';
        remove.addEventListener('click', () => {
            pendingAttachments.splice(index, 1);
            renderPendingAttachments();
        });

        chip.appendChild(label);
        chip.appendChild(remove);
        attachmentTray.appendChild(chip);
    });
}

function clearPendingAttachments() {
    pendingAttachments = [];
    renderPendingAttachments();
}

async function handleClear() {
    if (!confirm("Clear AI chat history? This won't undo geometry changes.")) return;
    try {
        await APIService.clearAiChatHistory();
        messageList.innerHTML = '';
        addMessageToUI('system', "History cleared.");
        historyLoaded = false;
    } catch (err) {
        UIManager.showError("Failed to clear history: " + err.message);
    } finally {
        refreshContextStats();
    }
}

function addMessageToUI(role, text, skipSave = false, attachments = []) {
    const div = document.createElement('div');
    div.className = `chat-message ${role} markdown-content`;
    
    const formattedText = marked.marked(text);
    div.innerHTML = formattedText;
    if (Array.isArray(attachments) && attachments.length > 0) {
        const attachmentList = document.createElement('div');
        attachmentList.className = 'ai-message-attachments';
        attachments.forEach((attachment) => {
            const chip = document.createElement('span');
            chip.className = 'ai-attachment-chip';
            chip.textContent = attachment.original_filename || attachment.artifact_id || 'attachment';
            attachmentList.appendChild(chip);
        });
        div.appendChild(attachmentList);
    }
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
    if (attachButton) attachButton.disabled = loading;
    if (visualCheckButton) visualCheckButton.disabled = loading;
    if (executionModeSelect) executionModeSelect.disabled = loading;
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
    indicator.className = 'chat-message model thinking-dropdown thinking-live';
    indicator.id = 'ai-thinking-indicator';

    const toggleBtn = document.createElement('div');
    toggleBtn.className = 'thinking-toggle';
    toggleBtn.setAttribute('role', 'button');
    toggleBtn.setAttribute('tabindex', '0');
    toggleBtn.setAttribute('aria-expanded', 'false');

    const toggleMain = document.createElement('span');
    toggleMain.className = 'thinking-toggle-main';

    const toggleTitle = document.createElement('span');
    toggleTitle.className = 'thinking-toggle-title';
    toggleTitle.textContent = 'Thoughts...';

    const toggleSummary = document.createElement('span');
    toggleSummary.className = 'thinking-toggle-summary';
    toggleSummary.textContent = 'Waiting for model...';

    toggleMain.appendChild(toggleTitle);
    toggleMain.appendChild(toggleSummary);

    const toggleIcon = document.createElement('span');
    toggleIcon.className = 'thinking-toggle-icon';
    toggleIcon.textContent = '+';

    toggleBtn.appendChild(toggleMain);
    toggleBtn.appendChild(toggleIcon);
    const toggleDropdown = () => toggleThinkingDropdown(indicator);
    toggleBtn.onclick = toggleDropdown;
    toggleBtn.onkeydown = (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleDropdown();
        }
    };

    const content = document.createElement('div');
    content.className = 'thinking-content';
    content.hidden = true;

    const emptyState = document.createElement('div');
    emptyState.className = 'thinking-empty';
    emptyState.textContent = 'Tool activity will appear here while the model works.';
    content.appendChild(emptyState);

    indicator.appendChild(toggleBtn);
    indicator.appendChild(content);
    indicator._progressKeys = new Set();

    messageList.appendChild(indicator);
    scrollToBottom();
    return indicator;
}

function updateThinkingIndicator(indicator, progress) {
    if (!indicator || !indicator.isConnected) return;

    const toggleSummary = indicator.querySelector('.thinking-toggle-summary');
    const content = indicator.querySelector('.thinking-content');
    const emptyState = content?.querySelector('.thinking-empty');
    const progressKeys = indicator._progressKeys || new Set();

    const appendProgressEntry = (key, html, className = 'thinking-step') => {
        if (!content || !key || progressKeys.has(key)) return;
        progressKeys.add(key);
        indicator._progressKeys = progressKeys;

        if (emptyState && emptyState.isConnected) {
            emptyState.remove();
        }

        const entry = document.createElement('div');
        entry.className = className;
        entry.innerHTML = html;
        content.appendChild(entry);
    };

    if (progress.type === 'turn_start') {
        currentTurn = progress.turn;
        currentTurnLimit = progress.turnLimit;

        if (toggleSummary) {
            toggleSummary.textContent = `Turn ${currentTurn}/${currentTurnLimit} in progress`;
        }
        appendProgressEntry(
            `turn_start:${currentTurn}:${currentTurnLimit}`,
            `<strong>Turn ${currentTurn}/${currentTurnLimit}:</strong> Processing...`
        );
    } else if (progress.type === 'tool_calls' && progress.tools && progress.tools.length > 0) {
        currentTurn = progress.turn;

        if (progress.recentTools && progress.recentTools.length > 0) {
            currentRecentTools = progress.recentTools;
        } else {
            currentRecentTools = [...currentRecentTools, ...progress.tools].slice(-3);
        }

        if (toggleSummary) {
            const liveToolSummary = currentRecentTools.join(', ');
            toggleSummary.textContent = liveToolSummary
                ? `Turn ${currentTurn}/${currentTurnLimit} • ${liveToolSummary}`
                : `Turn ${currentTurn}/${currentTurnLimit} • tool activity`;
        }

        const toolList = progress.tools.join(', ');
        appendProgressEntry(
            `tool_calls:${currentTurn}:${toolList}`,
            `<strong>Turn ${currentTurn} tools:</strong> ${toolList}`,
            'thinking-tools'
        );
    } else if (progress.type === 'visual_verification_request') {
        if (toggleSummary) {
            toggleSummary.textContent = `Turn ${currentTurn}/${currentTurnLimit} • visual checkpoint`;
        }
        appendProgressEntry(
            `visual_verification_request:${progress.requestId || Date.now()}`,
            `<strong>Visual checkpoint:</strong> ${progress.reason || 'capturing AIRPET screenshots for the model.'}`,
            'thinking-tools'
        );
    } else if (progress.type === 'paused') {
        if (toggleSummary) {
            toggleSummary.textContent = `Paused: ${progress.reason || 'tab hidden'}`;
        }
        appendProgressEntry(
            `paused:${progress.reason || 'tab hidden'}`,
            `<strong>Paused:</strong> ${progress.reason || 'tab hidden'}`,
            'thinking-tools'
        );
    } else if (progress.type === 'resumed') {
        if (progress.recentTools && progress.recentTools.length > 0) {
            currentRecentTools = progress.recentTools;
        }

        if (toggleSummary) {
            toggleSummary.textContent = `Turn ${currentTurn}/${currentTurnLimit} resumed`;
        }
        appendProgressEntry(
            `resumed:${currentTurn}:${currentRecentTools.join(',')}`,
            `<strong>Resumed:</strong> continuing turn ${currentTurn}/${currentTurnLimit}.`,
            'thinking-tools'
        );
    }

    scrollToBottom();
}

function removeThinkingIndicator(indicator) {
    if (indicator && indicator.isConnected) {
        indicator.remove();
    }
    currentRecentTools = [];
}

function addThinkingDropdown(intermediates) {
    const dropdown = document.createElement('div');
    dropdown.className = 'chat-message model thinking-dropdown';

    const toolNames = [...new Set(intermediates.flatMap(item => getIntermediateToolNames(item.msg)))];
    const summaryParts = [`${intermediates.length} step${intermediates.length > 1 ? 's' : ''}`];
    if (toolNames.length > 0) {
        summaryParts.push(toolNames.slice(0, 3).join(', '));
        if (toolNames.length > 3) {
            summaryParts.push(`+${toolNames.length - 3} more`);
        }
    }
    const summaryText = summaryParts.join(' • ');

    const toggleBtn = document.createElement('div');
    toggleBtn.className = 'thinking-toggle';
    toggleBtn.setAttribute('role', 'button');
    toggleBtn.setAttribute('tabindex', '0');
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.dataset.summary = summaryText;

    const toggleMain = document.createElement('span');
    toggleMain.className = 'thinking-toggle-main';

    const toggleTitle = document.createElement('span');
    toggleTitle.className = 'thinking-toggle-title';
    toggleTitle.textContent = 'Thoughts...';

    const toggleSummary = document.createElement('span');
    toggleSummary.className = 'thinking-toggle-summary';
    toggleSummary.textContent = summaryText;

    toggleMain.appendChild(toggleTitle);
    toggleMain.appendChild(toggleSummary);

    const toggleIcon = document.createElement('span');
    toggleIcon.className = 'thinking-toggle-icon';
    toggleIcon.textContent = '+';

    toggleBtn.appendChild(toggleMain);
    toggleBtn.appendChild(toggleIcon);
    const toggleDropdown = () => toggleThinkingDropdown(dropdown);
    toggleBtn.onclick = toggleDropdown;
    toggleBtn.onkeydown = (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleDropdown();
        }
    };
    
    const content = document.createElement('div');
    content.className = 'thinking-content';
    content.hidden = true;
    
    intermediates.forEach((item, idx) => {
        const text = item.msg.parts ? item.msg.parts.map(p => p.text || '').join('\n').trim() : (item.msg.content || '').trim();
        if (text && !text.startsWith('[System Context Update]')) {
            const step = document.createElement('div');
            step.className = 'thinking-step';
            step.innerHTML = `<strong>Step ${idx + 1}:</strong> ${marked.marked.parse(text)}`;
            content.appendChild(step);
        }
        
        const toolNamesForStep = getIntermediateToolNames(item.msg);
        if (toolNamesForStep.length > 0) {
            const toolDiv = document.createElement('div');
            toolDiv.className = 'thinking-tools';
            toolDiv.innerHTML = `<strong>Tools called:</strong> ${toolNamesForStep.join(', ')}`;
            content.appendChild(toolDiv);
        }
    });

    if (content.childElementCount === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'thinking-empty';
        emptyState.textContent = 'Tool activity was recorded, but no intermediate text was saved for this turn.';
        content.appendChild(emptyState);
    }
    
    dropdown.appendChild(toggleBtn);
    dropdown.appendChild(content);
    messageList.appendChild(dropdown);
    scrollToBottom();
}

function toggleThinkingDropdown(dropdown) {
    const content = dropdown.querySelector('.thinking-content');
    const toggleBtn = dropdown.querySelector('.thinking-toggle');
    const toggleIcon = dropdown.querySelector('.thinking-toggle-icon');
    const isExpanded = !content.hidden;

    content.hidden = isExpanded;
    toggleBtn.setAttribute('aria-expanded', isExpanded ? 'false' : 'true');
    if (toggleIcon) {
        toggleIcon.textContent = isExpanded ? '+' : '−';
    }
}
