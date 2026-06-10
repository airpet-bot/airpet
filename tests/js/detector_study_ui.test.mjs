import assert from 'node:assert/strict';
import test from 'node:test';

import {
    detectorStudySummaryText,
    normalizeDetectorStudy,
} from '../../static/detectorStudyUi.js';

test('normalizes running study progress from simulation events', () => {
    const study = normalizeDetectorStudy({
        study_id: 'study-1',
        phase: 'RUNNING',
        brief: { goal: 'Test detector' },
        simulation: {
            progress: 50,
            total_events: 100,
        },
    });

    assert.equal(study.phaseLabel, 'Simulating');
    assert.equal(study.progress, 81);
    assert.equal(study.terminal, false);
    assert.equal(detectorStudySummaryText(study), '50/100 events');
});

test('summarizes completed study hit analysis', () => {
    const study = normalizeDetectorStudy({
        study_id: 'study-2',
        phase: 'COMPLETE',
        status_message: 'Study complete.',
        brief: { goal: 'Test detector' },
        analysis: {
            summary: { total_hits: 64 },
        },
    });

    assert.equal(study.progress, 100);
    assert.equal(study.terminal, true);
    assert.equal(detectorStudySummaryText(study), '64 recorded hits');
});

test('exposes coordinator pause and pending interpretation state', () => {
    const study = normalizeDetectorStudy({
        study_id: 'study-3',
        phase: 'PAUSED',
        brief: { goal: 'Paused detector study' },
        coordinator: {
            status: 'paused',
            interpretation_status: 'pending',
        },
        checkpoints: [{ checkpoint_id: 'checkpoint-1' }],
        report: { warnings: [] },
    });

    assert.equal(study.paused, true);
    assert.equal(study.checkpoints.length, 1);
    assert.deepEqual(study.report, { warnings: [] });
});

test('summarizes a completed study awaiting model interpretation', () => {
    const study = normalizeDetectorStudy({
        study_id: 'study-4',
        phase: 'COMPLETE',
        brief: { goal: 'Interpret detector study' },
        coordinator: { interpretation_status: 'pending' },
        analysis: { summary: { total_hits: 12 } },
    });

    assert.equal(
        detectorStudySummaryText(study),
        '12 recorded hits - interpreting results',
    );
});
