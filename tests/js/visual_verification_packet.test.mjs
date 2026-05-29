import test from 'node:test';
import assert from 'node:assert/strict';

import {
    DEFAULT_VISUAL_VERIFICATION_VIEW_SPECS,
    VISUAL_VERIFICATION_PACKET_KIND,
    buildVisualVerificationMetadata,
    resolveVisualVerificationViewSpecs,
} from '../../static/visualVerificationPacket.js';

const projectState = {
    project_scope_id: 'scope-123',
    world_volume_ref: 'World',
    materials: {
        Air: { name: 'Air' },
        Silicon: { name: 'Silicon' },
    },
    solids: {
        world_solid: { name: 'world_solid', type: 'box' },
        sensor_solid: { name: 'sensor_solid', type: 'box' },
    },
    logical_volumes: {
        World: {
            name: 'World',
            solid_ref: 'world_solid',
            material_ref: 'Air',
            is_sensitive: false,
        },
        SensorLV: {
            name: 'SensorLV',
            solid_ref: 'sensor_solid',
            material_ref: 'Silicon',
            is_sensitive: true,
            vis_attributes: { color: { r: 0.2, g: 0.6, b: 0.9, a: 0.7 } },
        },
    },
    sources: {
        beam: {
            id: 'source-1',
            name: 'beam',
            source_type: 'gps',
            gps_commands: {
                particle: 'gamma',
                'ang/type': 'beam1d',
                'ang/dir1': '0 0 1',
            },
        },
    },
    active_source_ids: ['source-1'],
    scoring: {
        schema_version: 1,
        scoring_meshes: [
            {
                mesh_id: 'mesh-1',
                name: 'dose_mesh',
                mesh_type: 'box',
                enabled: true,
                geometry: { center_mm: { x: 0, y: 0, z: 0 } },
                bins: { x: 10, y: 10, z: 10 },
            },
        ],
        tally_requests: [
            {
                tally_id: 'tally-1',
                name: 'edep',
                quantity: 'energy_deposit',
                mesh_ref: { mesh_id: 'mesh-1', name: 'dose_mesh' },
            },
        ],
        run_manifest_defaults: { events: 1000, threads: 1 },
    },
    environment: {
        optical_physics: true,
        global_uniform_magnetic_field: { enabled: true, vector_tesla: { x: 0, y: 0, z: 1 } },
    },
    cad_imports: [
        {
            import_id: 'step_import_1',
            source: { filename: 'detector.step', format: 'step' },
            created_object_ids: { logical_volume_ids: ['SensorLV'] },
        },
    ],
    detector_feature_generators: [
        {
            generator_id: 'gen-1',
            name: 'holes',
            generator_type: 'rectangular_hole_array',
            status: 'applied',
        },
    ],
};

const sceneDescription = [
    {
        id: 'WORLD_PV_ID',
        name: 'World',
        parent_id: null,
        is_world_volume_placement: true,
        volume_ref: 'World',
        position: { x: 0, y: 0, z: 0 },
        rotation: { x: 0, y: 0, z: 0 },
        scale: { x: 1, y: 1, z: 1 },
    },
    {
        id: 'pv-sensor',
        canonical_id: 'pv-sensor',
        name: 'sensor_pv',
        parent_id: 'WORLD_PV_ID',
        volume_ref: 'SensorLV',
        solid_ref_for_threejs: 'sensor_solid',
        position: { x: 1, y: 2, z: 3 },
        rotation: { x: Math.PI / 4, y: 0, z: 0 },
        scale: { x: 1, y: 1, z: 1 },
        vis_attributes: { color: { r: 0.2, g: 0.6, b: 0.9, a: 0.7 } },
    },
    {
        id: 'source-1',
        name: 'beam',
        parent_id: 'WORLD_PV_ID',
        is_source: true,
        position: { x: 0, y: 0, z: -25 },
        rotation: { x: 0, y: 0, z: 0 },
        gps_commands: { particle: 'gamma' },
    },
];

test('visual verification metadata summarizes scene and assignments for AI review', () => {
    const metadata = buildVisualVerificationMetadata({
        projectName: 'visual-test',
        projectState,
        sceneDescription,
        hiddenPvIds: ['pv-sensor'],
        generatedAt: '2026-05-29T12:00:00.000Z',
        captureOptions: {
            views: ['front', 'top'],
            include_images: true,
            image_width: 640,
            image_height: 480,
        },
        sceneBounds: {
            min: { x: -3, y: -3, z: -3 },
            max: { x: 3, y: 3, z: 3 },
        },
    });

    assert.equal(metadata.kind, VISUAL_VERIFICATION_PACKET_KIND);
    assert.equal(metadata.schema_version, 1);
    assert.equal(metadata.project.name, 'visual-test');
    assert.equal(metadata.project.project_scope_id, 'scope-123');
    assert.deepEqual(metadata.capture_request.requested_views, ['front', 'top']);
    assert.equal(metadata.capture_request.image_width, 640);
    assert.equal(metadata.scene_summary.component_count, 3);
    assert.equal(metadata.scene_summary.renderable_component_count, 1);
    assert.equal(metadata.scene_summary.hidden_component_count, 1);
    assert.equal(metadata.scene_summary.sensitive_logical_volume_count, 1);

    const sensorComponent = metadata.components.find((component) => component.id === 'pv-sensor');
    assert.equal(sensorComponent.type, 'physical_volume');
    assert.equal(sensorComponent.logical_volume, 'SensorLV');
    assert.equal(sensorComponent.material_ref, 'Silicon');
    assert.equal(sensorComponent.is_sensitive, true);
    assert.equal(sensorComponent.is_hidden, true);
    assert.deepEqual(sensorComponent.local_transform.position_mm, { x: 1, y: 2, z: 3 });
    assert.equal(sensorComponent.local_transform.rotation_deg.x, 45);
    assert.deepEqual(sensorComponent.visual.color_rgba, { r: 0.2, g: 0.6, b: 0.9, a: 0.7 });

    assert.deepEqual(metadata.assignments.sensitive_logical_volumes, [
        { name: 'SensorLV', solid_ref: 'sensor_solid', material_ref: 'Silicon' },
    ]);
    assert.equal(metadata.assignments.sources[0].active, true);
    assert.equal(metadata.assignments.scoring.enabled_mesh_count, 1);
    assert.equal(metadata.assignments.environment.optical_physics, true);
    assert.equal(metadata.assignments.cad_imports[0].import_id, 'step_import_1');
    assert.equal(metadata.assignments.detector_feature_generators[0].name, 'holes');
});

test('visual verification view resolver keeps canonical order and filters invalid names', () => {
    assert.deepEqual(
        resolveVisualVerificationViewSpecs(['top', 'front', 'not-a-view']).map((view) => view.name),
        ['front', 'top'],
    );
    assert.deepEqual(
        resolveVisualVerificationViewSpecs('side').map((view) => view.name),
        ['side'],
    );
    assert.deepEqual(
        resolveVisualVerificationViewSpecs().map((view) => view.name),
        DEFAULT_VISUAL_VERIFICATION_VIEW_SPECS.map((view) => view.name),
    );
});
