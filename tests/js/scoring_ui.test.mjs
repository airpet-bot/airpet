import test from 'node:test';
import assert from 'node:assert/strict';

import {
    buildScoringStateWithAddedMesh,
    buildScoringStateWithRemovedMesh,
    describeScoringMesh,
    describeScoringPanelState,
    formatScoringQuantityLabel,
    isMeshTallyEnabled,
    replaceScoringMesh,
    setMeshTallyEnabled,
} from '../../static/scoringUi.js';

test('adding a scoring mesh creates a default energy deposit tally and deterministic summary', () => {
    const nextState = buildScoringStateWithAddedMesh({
        scoring_meshes: [],
        tally_requests: [],
    });

    assert.equal(nextState.scoring_meshes.length, 1);
    assert.equal(nextState.tally_requests.length, 1);
    assert.equal(nextState.scoring_meshes[0].mesh_id, 'scoring_mesh_ui_1');
    assert.equal(nextState.scoring_meshes[0].name, 'box_mesh_1');
    assert.equal(nextState.tally_requests[0].mesh_ref.mesh_id, 'scoring_mesh_ui_1');
    assert.equal(nextState.tally_requests[0].mesh_ref.name, 'box_mesh_1');
    assert.equal(nextState.tally_requests[0].quantity, 'energy_deposit');

    const described = describeScoringMesh(nextState.scoring_meshes[0], nextState);
    assert.equal(
        described.summary,
        'World box mesh · center 0 x 0 x 0 mm · size 10 x 10 x 10 mm · bins 10 x 10 x 10 · 1 enabled tally',
    );

    const panelState = describeScoringPanelState({ scoring: nextState });
    assert.equal(panelState.intro, '1 enabled scoring mesh across 1 enabled tally request.');
    assert.equal(
        panelState.hint,
        'energy_deposit and n_of_step tallies currently emit runtime scoring artifacts. Other saved tallies remain editable here for upcoming runtime slices.',
    );
});

test('replacing a scoring mesh name keeps linked tally references aligned', () => {
    const initialState = buildScoringStateWithAddedMesh({
        scoring_meshes: [],
        tally_requests: [],
    });
    const mesh = initialState.scoring_meshes[0];

    const renamedState = replaceScoringMesh(initialState, mesh.mesh_id, {
        ...mesh,
        name: 'study_mesh',
        geometry: {
            ...mesh.geometry,
            size_mm: { x: 25, y: 15, z: 5 },
        },
    });

    assert.equal(renamedState.scoring_meshes[0].name, 'study_mesh');
    assert.equal(renamedState.tally_requests[0].mesh_ref.mesh_id, mesh.mesh_id);
    assert.equal(renamedState.tally_requests[0].mesh_ref.name, 'study_mesh');
    assert.equal(
        describeScoringMesh(renamedState.scoring_meshes[0], renamedState).summary,
        'World box mesh · center 0 x 0 x 0 mm · size 25 x 15 x 5 mm · bins 10 x 10 x 10 · 1 enabled tally',
    );
});

test('tally toggles add and remove per-mesh quantity requests deterministically', () => {
    const initialState = buildScoringStateWithAddedMesh({
        scoring_meshes: [],
        tally_requests: [],
    });
    const mesh = initialState.scoring_meshes[0];

    const withDose = setMeshTallyEnabled(initialState, mesh, 'dose_deposit', true);
    assert.equal(isMeshTallyEnabled(withDose, mesh.mesh_id, 'energy_deposit'), true);
    assert.equal(isMeshTallyEnabled(withDose, mesh.mesh_id, 'dose_deposit'), true);
    assert.equal(withDose.tally_requests.length, 2);

    const withStepCount = setMeshTallyEnabled(withDose, mesh, 'n_of_step', true);
    assert.equal(isMeshTallyEnabled(withStepCount, mesh.mesh_id, 'n_of_step'), true);
    assert.equal(withStepCount.tally_requests.length, 3);

    const withoutEnergyDeposit = setMeshTallyEnabled(withStepCount, mesh, 'energy_deposit', false);
    assert.equal(isMeshTallyEnabled(withoutEnergyDeposit, mesh.mesh_id, 'energy_deposit'), false);
    assert.equal(isMeshTallyEnabled(withoutEnergyDeposit, mesh.mesh_id, 'dose_deposit'), true);
    assert.equal(isMeshTallyEnabled(withoutEnergyDeposit, mesh.mesh_id, 'n_of_step'), true);
    assert.equal(withoutEnergyDeposit.tally_requests.length, 2);
    assert.equal(formatScoringQuantityLabel('passage_cell_flux'), 'passage cell flux');

    const removedMeshState = buildScoringStateWithRemovedMesh(withoutEnergyDeposit, mesh.mesh_id);
    assert.deepEqual(removedMeshState.scoring_meshes, []);
    assert.deepEqual(removedMeshState.tally_requests, []);
});
