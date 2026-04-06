import test from 'node:test';
import assert from 'node:assert/strict';

import {
    formatGlobalMagneticFieldSummary,
    formatLocalMagneticFieldSummary,
    normalizeGlobalMagneticFieldState,
    normalizeLocalMagneticFieldState,
} from '../../static/environmentFieldUi.js';

test('global magnetic field ui helpers normalize malformed values deterministically', () => {
    assert.deepEqual(
        normalizeGlobalMagneticFieldState({
            enabled: 'false',
            field_vector_tesla: {
                x: '1.25',
                y: 'bad-value',
                z: Infinity,
            },
        }),
        {
            enabled: false,
            field_vector_tesla: {
                x: 1.25,
                y: 0,
                z: 0,
            },
        },
    );
});

test('global magnetic field ui summary reflects saved enabled state and vector', () => {
    assert.equal(
        formatGlobalMagneticFieldSummary({
            enabled: true,
            field_vector_tesla: {
                x: 0,
                y: 1.5,
                z: -0.25,
            },
        }),
        'Global magnetic field: enabled (0, 1.5, -0.25) T',
    );
});

test('local magnetic field ui helpers normalize malformed target volumes and vectors deterministically', () => {
    assert.deepEqual(
        normalizeLocalMagneticFieldState({
            enabled: 'true',
            target_volume_names: 'box_LV, detector_LV; box_LV',
            field_vector_tesla: {
                x: '1.25',
                y: 'bad-value',
                z: Infinity,
            },
        }),
        {
            enabled: true,
            target_volume_names: ['box_LV', 'detector_LV'],
            field_vector_tesla: {
                x: 1.25,
                y: 0,
                z: 0,
            },
        },
    );
});

test('local magnetic field ui summary reflects saved enabled state, targets, and vector', () => {
    assert.equal(
        formatLocalMagneticFieldSummary({
            enabled: true,
            target_volume_names: ['box_LV', 'detector_LV'],
            field_vector_tesla: {
                x: 0,
                y: 1.5,
                z: -0.25,
            },
        }),
        'Local magnetic field: enabled (targets box_LV, detector_LV) (0, 1.5, -0.25) T',
    );
});
