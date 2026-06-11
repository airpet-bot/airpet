import test from 'node:test';
import assert from 'node:assert/strict';

import { buildAiSelectionContext } from '../../static/aiSelectionContext.js';


test('selection context preserves canonical ids and distinguishes scene instances', () => {
    const selection = buildAiSelectionContext([
        {
            type: 'physical_volume',
            id: 'scene-instance-7',
            canonical_id: 'pv-full-stable-id',
            name: 'SensorPV',
            selData: { position: { x: '10', y: '0', z: '0' } },
        },
    ]);

    assert.deepEqual(selection, [{
        component_type: 'physical_volume',
        id: 'pv-full-stable-id',
        name: 'SensorPV',
        ui_instance_id: 'scene-instance-7',
    }]);
});


test('selection context is bounded, deduplicated, and drops unsupported objects', () => {
    const selection = buildAiSelectionContext([
        { type: 'solid', id: 'SensorSolid', name: 'SensorSolid' },
        { type: 'solid', id: 'SensorSolid', name: 'SensorSolid' },
        { type: 'unknown', id: 'ignored', name: 'ignored' },
        { type: 'logical_volume', id: 'SensorLV', name: 'SensorLV' },
    ], 1);

    assert.deepEqual(selection, [{
        component_type: 'solid',
        id: 'SensorSolid',
        name: 'SensorSolid',
    }]);
});
