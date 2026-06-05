import test from 'node:test';
import assert from 'node:assert/strict';

import { buildAdvancedGpsPayloadFromSections } from '../../static/gpsEditor.js';

test('advanced GPS editor payload keeps explicit booleans and trims empty fields', () => {
    const payload = buildAdvancedGpsPayloadFromSections({
        airpet_transform_mode: 'structured',
        source_list: {
            multiple_vertex: 'true',
            flat_sampling: '',
        },
        control: {
            verbose: ' 1 ',
            checkVolume: 'false',
            time: '',
        },
        position: {
            'pos/type': 'Beam',
            'pos/centre': ' 0 0 5 mm ',
            'pos/radius': '',
        },
        angular: {
            'ang/type': 'focused',
            'ang/focuspoint': '0 0 100 mm',
            'ang/surfnorm': 'true',
        },
        energy: {
            'ene/type': 'Arb',
            'ene/applyEneWeight': 'true',
        },
    });

    assert.deepEqual(payload.advanced_gps, {
        airpet_transform_mode: 'structured',
        source_list: {
            multiple_vertex: true,
        },
        control: {
            verbose: '1',
            checkVolume: false,
        },
        position: {
            'pos/type': 'Beam',
            'pos/centre': '0 0 5 mm',
        },
        angular: {
            'ang/type': 'focused',
            'ang/focuspoint': '0 0 100 mm',
            'ang/surfnorm': true,
        },
        energy: {
            'ene/type': 'Arb',
            'ene/applyEneWeight': true,
        },
    });
    assert.deepEqual(payload.gps_command_sequence, []);
});

test('advanced GPS editor payload supports histograms and ordered raw commands', () => {
    const payload = buildAdvancedGpsPayloadFromSections({
        histograms: [
            {
                type: 'energy',
                enabled: true,
                reset: true,
                points: '1 keV 0.2\n\n10 keV 1.0',
                interpolation: 'Lin',
            },
            {
                type: '',
                points: 'ignored',
            },
            {
                type: 'biasx',
                enabled: false,
                points: [[0, 0.5], [1, 1.0]],
            },
        ],
        gps_command_sequence: [
            '/gps/hist/point 1 keV 0.2',
            { command: '/gps/hist/point', value: '10 keV 1.0', enabled: false },
            { command: '', value: 'ignored' },
        ],
    });

    assert.deepEqual(payload.advanced_gps.histograms, [
        {
            type: 'energy',
            enabled: true,
            reset: true,
            points: ['1 keV 0.2', '10 keV 1.0'],
            interpolation: 'Lin',
        },
        {
            type: 'biasx',
            enabled: false,
            points: ['0 0.5', '1 1'],
        },
    ]);
    assert.deepEqual(payload.gps_command_sequence, [
        { command: 'hist/point', value: '1 keV 0.2', enabled: true },
        { command: 'hist/point', value: '10 keV 1.0', enabled: false },
    ]);
});

