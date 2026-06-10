export const DETECTOR_STUDY_TERMINAL_PHASES = new Set([
    'COMPLETE',
    'NEEDS_ATTENTION',
]);

const PHASE_LABELS = {
    INTAKE: 'Intake',
    PLANNED: 'Planning',
    BUILDING: 'Building',
    VISUAL_CHECK: 'Visual check',
    PREFLIGHT: 'Preflight',
    READY: 'Ready to run',
    RUNNING: 'Simulating',
    ANALYZING: 'Analyzing',
    COMPLETE: 'Complete',
    NEEDS_ATTENTION: 'Needs attention',
    PAUSED: 'Paused',
};

const PHASE_PROGRESS = {
    INTAKE: 8,
    PLANNED: 16,
    BUILDING: 38,
    VISUAL_CHECK: 52,
    PREFLIGHT: 64,
    READY: 72,
    RUNNING: 82,
    ANALYZING: 94,
    COMPLETE: 100,
    NEEDS_ATTENTION: 100,
    PAUSED: 50,
};

export function normalizeDetectorStudy(study) {
    if (!study || typeof study !== 'object') return null;
    const phase = String(study.phase || 'INTAKE').toUpperCase();
    const simulation = study.simulation && typeof study.simulation === 'object'
        ? study.simulation
        : null;
    const analysis = study.analysis && typeof study.analysis === 'object'
        ? study.analysis
        : null;
    const brief = study.brief && typeof study.brief === 'object'
        ? study.brief
        : {};
    const coordinator = study.coordinator && typeof study.coordinator === 'object'
        ? study.coordinator
        : {};
    const report = study.report && typeof study.report === 'object'
        ? study.report
        : null;

    let progress = PHASE_PROGRESS[phase] ?? 0;
    if (phase === 'RUNNING' && simulation) {
        const completed = Number(simulation.progress || 0);
        const total = Number(simulation.total_events || 0);
        if (total > 0) {
            progress = 72 + Math.round(Math.min(1, completed / total) * 18);
        }
    }

    return {
        ...study,
        phase,
        phaseLabel: PHASE_LABELS[phase] || phase,
        progress: Math.max(0, Math.min(100, progress)),
        terminal: DETECTOR_STUDY_TERMINAL_PHASES.has(phase),
        goal: String(brief.goal || ''),
        simulation,
        analysis,
        coordinator,
        report,
        checkpoints: Array.isArray(study.checkpoints) ? study.checkpoints : [],
        paused: phase === 'PAUSED' || coordinator.status === 'paused',
    };
}

export function detectorStudySummaryText(study) {
    const normalized = normalizeDetectorStudy(study);
    if (!normalized) return '';
    if (normalized.phase === 'RUNNING' && normalized.simulation) {
        const completed = Number(normalized.simulation.progress || 0);
        const total = Number(normalized.simulation.total_events || 0);
        return total > 0
            ? `${completed}/${total} events`
            : 'Simulation running';
    }
    const totalHits = normalized.analysis?.summary?.total_hits;
    if (normalized.phase === 'COMPLETE' && Number.isFinite(Number(totalHits))) {
        const interpretationStatus = normalized.coordinator?.interpretation_status;
        const suffix = interpretationStatus === 'pending'
            ? ' - interpreting results'
            : interpretationStatus === 'failed'
                ? ' - interpretation available for retry'
                : '';
        return `${Number(totalHits)} recorded hits${suffix}`;
    }
    return String(normalized.status_message || normalized.phaseLabel);
}
