export const SCORING_OBJECT_TYPE = 'scoring';
export const SCORING_OBJECT_ID = 'scoring_state';

export const SUPPORTED_SCORING_TALLY_QUANTITIES = [
    'energy_deposit',
    'dose_deposit',
    'cell_flux',
    'passage_cell_flux',
    'track_length',
    'n_of_step',
    'n_of_track',
];

export const RUNTIME_READY_SCORING_QUANTITIES = ['energy_deposit', 'n_of_step'];

const DEFAULT_RUN_MANIFEST_DEFAULTS = {
    events: 1000,
    threads: 1,
    seed1: 0,
    seed2: 0,
    print_progress: 0,
    save_hits: true,
    save_hit_metadata: true,
    save_particles: false,
    production_cut: '1.0 mm',
    hit_energy_threshold: '1 eV',
};

function normalizeString(value, fallback = '') {
    const text = String(value ?? '').trim();
    return text || fallback;
}

function normalizeBoolean(value, fallback = true) {
    if (typeof value === 'boolean') {
        return value;
    }
    if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        if (['true', '1', 'yes', 'on'].includes(normalized)) {
            return true;
        }
        if (['false', '0', 'no', 'off'].includes(normalized)) {
            return false;
        }
    }
    return fallback;
}

function normalizeFiniteNumber(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizePositiveNumber(value, fallback = 10) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function normalizePositiveInt(value, fallback = 10) {
    const parsed = Number.parseInt(String(value ?? ''), 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function formatNumber(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) {
        return '0';
    }
    return String(Number(numericValue.toFixed(6)));
}

function pluralize(count, singular, plural = `${singular}s`) {
    return `${count} ${count === 1 ? singular : plural}`;
}

function normalizeScoringMesh(rawMesh, index = 0) {
    const mesh = rawMesh && typeof rawMesh === 'object' ? rawMesh : {};
    return {
        mesh_id: normalizeString(mesh.mesh_id, `scoring_mesh_ui_${index + 1}`),
        name: normalizeString(mesh.name, `box_mesh_${index + 1}`),
        schema_version: 1,
        enabled: normalizeBoolean(mesh.enabled, true),
        mesh_type: 'box',
        reference_frame: 'world',
        geometry: {
            center_mm: {
                x: normalizeFiniteNumber(mesh?.geometry?.center_mm?.x, 0),
                y: normalizeFiniteNumber(mesh?.geometry?.center_mm?.y, 0),
                z: normalizeFiniteNumber(mesh?.geometry?.center_mm?.z, 0),
            },
            size_mm: {
                x: normalizePositiveNumber(mesh?.geometry?.size_mm?.x, 10),
                y: normalizePositiveNumber(mesh?.geometry?.size_mm?.y, 10),
                z: normalizePositiveNumber(mesh?.geometry?.size_mm?.z, 10),
            },
        },
        bins: {
            x: normalizePositiveInt(mesh?.bins?.x, 10),
            y: normalizePositiveInt(mesh?.bins?.y, 10),
            z: normalizePositiveInt(mesh?.bins?.z, 10),
        },
    };
}

function normalizeTallyQuantity(value) {
    const quantity = normalizeString(value, 'energy_deposit');
    return SUPPORTED_SCORING_TALLY_QUANTITIES.includes(quantity) ? quantity : 'energy_deposit';
}

function normalizeScoringTally(rawTally, index = 0) {
    const tally = rawTally && typeof rawTally === 'object' ? rawTally : {};
    const quantity = normalizeTallyQuantity(tally.quantity);
    const meshRef = tally.mesh_ref && typeof tally.mesh_ref === 'object' ? tally.mesh_ref : {};
    return {
        tally_id: normalizeString(tally.tally_id, `scoring_tally_ui_${index + 1}`),
        name: normalizeString(tally.name, `${quantity}_tally_${index + 1}`),
        schema_version: 1,
        enabled: normalizeBoolean(tally.enabled, true),
        mesh_ref: {
            mesh_id: normalizeString(meshRef.mesh_id, ''),
            name: normalizeString(meshRef.name, ''),
        },
        quantity,
    };
}

export function normalizeScoringState(rawState) {
    const state = rawState && typeof rawState === 'object' ? rawState : {};
    const scoringMeshes = Array.isArray(state.scoring_meshes)
        ? state.scoring_meshes.map((mesh, index) => normalizeScoringMesh(mesh, index))
        : [];
    const tallyRequests = Array.isArray(state.tally_requests)
        ? state.tally_requests.map((tally, index) => normalizeScoringTally(tally, index))
        : [];
    const runManifestDefaults = state.run_manifest_defaults && typeof state.run_manifest_defaults === 'object'
        ? { ...DEFAULT_RUN_MANIFEST_DEFAULTS, ...state.run_manifest_defaults }
        : { ...DEFAULT_RUN_MANIFEST_DEFAULTS };

    return {
        schema_version: 1,
        scoring_meshes: scoringMeshes,
        tally_requests: tallyRequests,
        run_manifest_defaults: runManifestDefaults,
    };
}

function findNextAvailableToken(existingValues, prefix) {
    let index = 1;
    let candidate = `${prefix}${index}`;
    while (existingValues.has(candidate)) {
        index += 1;
        candidate = `${prefix}${index}`;
    }
    return candidate;
}

function buildDefaultScoringTally(scoringState, mesh, quantity = 'energy_deposit') {
    const normalizedScoring = normalizeScoringState(scoringState);
    const usedTallyIds = new Set(normalizedScoring.tally_requests.map((tally) => tally.tally_id));
    const tallyId = findNextAvailableToken(usedTallyIds, 'scoring_tally_ui_');
    return {
        tally_id: tallyId,
        name: `${mesh.name}_${quantity}`,
        schema_version: 1,
        enabled: true,
        mesh_ref: {
            mesh_id: mesh.mesh_id,
            name: mesh.name,
        },
        quantity,
    };
}

export function buildDefaultScoringMesh(rawScoringState) {
    const scoringState = normalizeScoringState(rawScoringState);
    const usedMeshIds = new Set(scoringState.scoring_meshes.map((mesh) => mesh.mesh_id));
    const usedMeshNames = new Set(scoringState.scoring_meshes.map((mesh) => mesh.name));
    const meshId = findNextAvailableToken(usedMeshIds, 'scoring_mesh_ui_');
    const meshName = findNextAvailableToken(usedMeshNames, 'box_mesh_');

    return {
        mesh_id: meshId,
        name: meshName,
        schema_version: 1,
        enabled: true,
        mesh_type: 'box',
        reference_frame: 'world',
        geometry: {
            center_mm: { x: 0, y: 0, z: 0 },
            size_mm: { x: 10, y: 10, z: 10 },
        },
        bins: { x: 10, y: 10, z: 10 },
    };
}

export function findTalliesForMesh(rawScoringState, meshId) {
    const scoringState = normalizeScoringState(rawScoringState);
    const targetMeshId = normalizeString(meshId, '');
    if (!targetMeshId) {
        return [];
    }
    return scoringState.tally_requests.filter((tally) => tally.mesh_ref.mesh_id === targetMeshId);
}

export function isMeshTallyEnabled(rawScoringState, meshId, quantity) {
    return findTalliesForMesh(rawScoringState, meshId).some(
        (tally) => tally.enabled && tally.quantity === quantity
    );
}

export function buildScoringStateWithAddedMesh(rawScoringState) {
    const scoringState = normalizeScoringState(rawScoringState);
    const mesh = buildDefaultScoringMesh(scoringState);
    return {
        ...scoringState,
        scoring_meshes: [...scoringState.scoring_meshes, mesh],
        tally_requests: [...scoringState.tally_requests, buildDefaultScoringTally(scoringState, mesh)],
    };
}

export function buildScoringStateWithRemovedMesh(rawScoringState, meshId) {
    const scoringState = normalizeScoringState(rawScoringState);
    const normalizedMeshId = normalizeString(meshId, '');
    return {
        ...scoringState,
        scoring_meshes: scoringState.scoring_meshes.filter((mesh) => mesh.mesh_id !== normalizedMeshId),
        tally_requests: scoringState.tally_requests.filter((tally) => tally.mesh_ref.mesh_id !== normalizedMeshId),
    };
}

export function replaceScoringMesh(rawScoringState, meshId, nextMesh) {
    const scoringState = normalizeScoringState(rawScoringState);
    const normalizedMeshId = normalizeString(meshId, '');
    const meshIndex = scoringState.scoring_meshes.findIndex((mesh) => mesh.mesh_id === normalizedMeshId);
    if (meshIndex === -1) {
        return scoringState;
    }

    const normalizedMesh = normalizeScoringMesh(nextMesh, meshIndex);
    const nextMeshes = scoringState.scoring_meshes.map((mesh) => (
        mesh.mesh_id === normalizedMeshId ? normalizedMesh : mesh
    ));
    const nextTallies = scoringState.tally_requests.map((tally) => {
        if (tally.mesh_ref.mesh_id !== normalizedMeshId) {
            return tally;
        }
        return {
            ...tally,
            mesh_ref: {
                mesh_id: normalizedMesh.mesh_id,
                name: normalizedMesh.name,
            },
        };
    });

    return {
        ...scoringState,
        scoring_meshes: nextMeshes,
        tally_requests: nextTallies,
    };
}

export function setMeshTallyEnabled(rawScoringState, mesh, quantity, enabled) {
    const scoringState = normalizeScoringState(rawScoringState);
    const normalizedMesh = normalizeScoringMesh(
        mesh,
        scoringState.scoring_meshes.findIndex((candidate) => candidate.mesh_id === mesh?.mesh_id),
    );
    const normalizedQuantity = normalizeTallyQuantity(quantity);
    const matchingTallies = [];
    const remainingTallies = [];

    scoringState.tally_requests.forEach((tally) => {
        if (tally.mesh_ref.mesh_id === normalizedMesh.mesh_id && tally.quantity === normalizedQuantity) {
            matchingTallies.push(tally);
            return;
        }
        remainingTallies.push(tally);
    });

    if (!enabled) {
        return {
            ...scoringState,
            tally_requests: remainingTallies,
        };
    }

    const nextTallies = [...remainingTallies];
    if (matchingTallies.length > 0) {
        const nextTally = matchingTallies[0];
        nextTallies.push({
            ...nextTally,
            enabled: true,
            mesh_ref: {
                mesh_id: normalizedMesh.mesh_id,
                name: normalizedMesh.name,
            },
        });
    } else {
        nextTallies.push(buildDefaultScoringTally(scoringState, normalizedMesh, normalizedQuantity));
    }

    return {
        ...scoringState,
        tally_requests: nextTallies,
    };
}

export function formatScoringQuantityLabel(quantity) {
    return normalizeString(quantity, 'energy_deposit').replace(/_/g, ' ');
}

export function describeScoringMesh(rawMesh, rawScoringState) {
    const mesh = normalizeScoringMesh(rawMesh);
    const meshTallies = findTalliesForMesh(rawScoringState, mesh.mesh_id);
    const enabledTallies = meshTallies.filter((tally) => tally.enabled);
    return {
        title: mesh.name,
        statusBadge: mesh.enabled ? 'enabled' : 'disabled',
        summary: `World box mesh · center ${formatNumber(mesh.geometry.center_mm.x)} x ${formatNumber(mesh.geometry.center_mm.y)} x ${formatNumber(mesh.geometry.center_mm.z)} mm · size ${formatNumber(mesh.geometry.size_mm.x)} x ${formatNumber(mesh.geometry.size_mm.y)} x ${formatNumber(mesh.geometry.size_mm.z)} mm · bins ${mesh.bins.x} x ${mesh.bins.y} x ${mesh.bins.z} · ${pluralize(enabledTallies.length, 'enabled tally')}`,
    };
}

export function describeScoringPanelState(projectState) {
    const scoringState = normalizeScoringState(projectState?.scoring);
    const enabledMeshes = scoringState.scoring_meshes.filter((mesh) => mesh.enabled);
    const enabledTallies = scoringState.tally_requests.filter((tally) => tally.enabled);

    return {
        intro: `${pluralize(enabledMeshes.length, 'enabled scoring mesh')} across ${pluralize(enabledTallies.length, 'enabled tally request')}.`,
        hint: 'energy_deposit and n_of_step tallies currently emit runtime scoring artifacts. Other saved tallies remain editable here for upcoming runtime slices.',
        empty: 'No scoring meshes saved yet. Add one world-space box mesh to start a scoring study.',
        defaultExpandedIndex: scoringState.scoring_meshes.length === 1 ? 0 : -1,
    };
}
