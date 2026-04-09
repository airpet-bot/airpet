import test from 'node:test';
import assert from 'node:assert/strict';

import {
    buildDetectorFeatureGeneratorEditorModel,
    describeDetectorFeatureGenerator,
    listDetectorFeatureGeneratorTargetOptions,
} from '../../static/detectorFeatureGeneratorsUi.js';

test('detector feature generator editor model prefers the selected box target', () => {
    const projectState = {
        solids: {
            collimator_block: { id: 'solid-box-1', name: 'collimator_block', type: 'box' },
            fixture_tube: { id: 'solid-tube-1', name: 'fixture_tube', type: 'tube' },
        },
        logical_volumes: {
            World: { id: 'lv-world', name: 'World', solid_ref: 'world_box' },
            collimator_lv: { id: 'lv-collimator', name: 'collimator_lv', solid_ref: 'collimator_block' },
        },
    };

    const options = listDetectorFeatureGeneratorTargetOptions(projectState);
    assert.deepEqual(options.map((option) => option.name), ['collimator_block']);
    assert.equal(options[0].logicalVolumeSummary, '1 logical volume');

    const model = buildDetectorFeatureGeneratorEditorModel(
        projectState,
        null,
        [{ type: 'logical_volume', id: 'collimator_lv', name: 'collimator_lv' }],
    );

    assert.equal(model.selectedTargetName, 'collimator_block');
    assert.equal(model.selectedTargetId, 'solid-box-1');
    assert.equal(model.name, 'collimator_block_holes');
    assert.deepEqual(model.selectedTargetLogicalVolumeNames, ['collimator_lv']);
    assert.equal(model.targetLocked, false);
    assert.equal(model.generatorType, 'rectangular_drilled_hole_array');
});

test('detector feature generator description stays deterministic for generated entries', () => {
    const projectState = {
        solids: {
            collimator_block: { id: 'solid-box-1', name: 'collimator_block', type: 'box' },
            collimator_block_holes__result: {
                id: 'solid-result-1',
                name: 'collimator_block_holes__result',
                type: 'boolean',
            },
            collimator_block_holes__cutter: {
                id: 'solid-cutter-1',
                name: 'collimator_block_holes__cutter',
                type: 'tube',
            },
        },
        logical_volumes: {
            collimator_lv: { id: 'lv-collimator', name: 'collimator_lv', solid_ref: 'collimator_block_holes__result' },
        },
    };

    const described = describeDetectorFeatureGenerator(
        {
            generator_id: 'dfg_rect_fixture',
            name: 'fixture_collimator_holes',
            target: {
                solid_ref: { id: 'solid-box-1', name: 'collimator_block' },
                logical_volume_refs: [],
            },
            pattern: {
                count_x: 4,
                count_y: 3,
                pitch_mm: { x: 7.5, y: 6.0 },
                origin_offset_mm: { x: 1.25, y: -2.5 },
            },
            hole: {
                diameter_mm: 1.5,
                depth_mm: 8.0,
            },
            realization: {
                status: 'generated',
                result_solid_ref: { id: 'solid-result-1', name: 'collimator_block_holes__result' },
                generated_object_refs: {
                    solid_refs: [
                        { id: 'solid-result-1', name: 'collimator_block_holes__result' },
                        { id: 'solid-cutter-1', name: 'collimator_block_holes__cutter' },
                    ],
                    logical_volume_refs: [
                        { id: 'lv-collimator', name: 'collimator_lv' },
                    ],
                },
            },
        },
        projectState,
    );

    assert.equal(
        described.summary,
        'Rectangular drilled holes on collimator_block · 4 x 3 @ 7.5 x 6 mm · dia 1.5 mm depth 8 mm',
    );
    assert.equal(described.statusBadge, 'generated');
    assert.equal(described.detailRows.find((row) => row.label === 'Result Solid').value, 'collimator_block_holes__result');
    assert.equal(
        described.detailRows.find((row) => row.label === 'Target Logical Volumes').value.text,
        'collimator_lv',
    );
    assert.equal(
        described.detailRows.find((row) => row.label === 'Generated Solids').value.text,
        'collimator_block_holes__result, collimator_block_holes__cutter',
    );
});

test('circular detector feature generator model and description stay deterministic', () => {
    const projectState = {
        solids: {
            circular_block: { id: 'solid-box-2', name: 'circular_block', type: 'box' },
            circular_holes__result: {
                id: 'solid-result-2',
                name: 'circular_holes__result',
                type: 'boolean',
            },
            circular_holes__cutter: {
                id: 'solid-cutter-2',
                name: 'circular_holes__cutter',
                type: 'tube',
            },
        },
        logical_volumes: {
            circular_lv: { id: 'lv-circular', name: 'circular_lv', solid_ref: 'circular_holes__result' },
        },
    };

    const entry = {
        generator_id: 'dfg_circular_fixture',
        generator_type: 'circular_drilled_hole_array',
        name: 'fixture_circular_holes',
        target: {
            solid_ref: { id: 'solid-box-2', name: 'circular_block' },
            logical_volume_refs: [],
        },
        pattern: {
            count: 6,
            radius_mm: 8,
            orientation_deg: 30,
            origin_offset_mm: { x: 1.5, y: -2.0 },
        },
        hole: {
            diameter_mm: 1.25,
            depth_mm: 6.0,
        },
        realization: {
            status: 'generated',
            result_solid_ref: { id: 'solid-result-2', name: 'circular_holes__result' },
            generated_object_refs: {
                solid_refs: [
                    { id: 'solid-result-2', name: 'circular_holes__result' },
                    { id: 'solid-cutter-2', name: 'circular_holes__cutter' },
                ],
                logical_volume_refs: [
                    { id: 'lv-circular', name: 'circular_lv' },
                ],
            },
        },
    };

    const model = buildDetectorFeatureGeneratorEditorModel(projectState, entry);
    assert.equal(model.generatorType, 'circular_drilled_hole_array');
    assert.equal(model.circularCount, 6);
    assert.equal(model.circularRadius, 8);
    assert.equal(model.circularOrientation, 30);
    assert.equal(model.typeLocked, true);

    const described = describeDetectorFeatureGenerator(entry, projectState);
    assert.equal(
        described.summary,
        'Circular drilled holes on circular_block · 6 holes on r 8 mm @ 30 deg · dia 1.25 mm depth 6 mm',
    );
    assert.equal(
        described.detailRows.find((row) => row.label === 'Pattern').value,
        '6 holes on radius 8 mm',
    );
    assert.equal(
        described.detailRows.find((row) => row.label === 'Orientation').value,
        '30 deg',
    );
});
