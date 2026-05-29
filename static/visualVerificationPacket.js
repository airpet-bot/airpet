// static/visualVerificationPacket.js

export const VISUAL_VERIFICATION_PACKET_KIND = 'airpet.visual_verification_packet';
export const VISUAL_VERIFICATION_PACKET_SCHEMA_VERSION = 1;

export const DEFAULT_VISUAL_VERIFICATION_VIEW_SPECS = Object.freeze([
    Object.freeze({
        name: 'front',
        label: 'Front view',
        direction: Object.freeze({ x: 0, y: -1, z: 0 }),
        up: Object.freeze({ x: 0, y: 0, z: 1 }),
        description: 'Looks toward +Y with +Z up.',
    }),
    Object.freeze({
        name: 'side',
        label: 'Side view',
        direction: Object.freeze({ x: 1, y: 0, z: 0 }),
        up: Object.freeze({ x: 0, y: 0, z: 1 }),
        description: 'Looks toward -X with +Z up.',
    }),
    Object.freeze({
        name: 'top',
        label: 'Top view',
        direction: Object.freeze({ x: 0, y: 0, z: 1 }),
        up: Object.freeze({ x: 0, y: 1, z: 0 }),
        description: 'Looks down the +Z axis with +Y up in the image.',
    }),
    Object.freeze({
        name: 'isometric',
        label: 'Isometric view',
        direction: Object.freeze({ x: 1, y: -1, z: 0.75 }),
        up: Object.freeze({ x: 0, y: 0, z: 1 }),
        description: 'Oblique overview for relative alignment checks.',
    }),
]);

function asRecord(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function asArray(value) {
    return Array.isArray(value) ? value : [];
}

function objectValues(value) {
    return Object.values(asRecord(value));
}

function numberOrZero(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function copyVector(value, fallback = 0) {
    const record = asRecord(value);
    return {
        x: numberOrZero(record.x ?? fallback),
        y: numberOrZero(record.y ?? fallback),
        z: numberOrZero(record.z ?? fallback),
    };
}

function radiansVectorToDegrees(value) {
    const vector = copyVector(value);
    const factor = 180 / Math.PI;
    return {
        x: Number((vector.x * factor).toFixed(6)),
        y: Number((vector.y * factor).toFixed(6)),
        z: Number((vector.z * factor).toFixed(6)),
    };
}

function normalizeScale(value) {
    const record = asRecord(value);
    return {
        x: Number.isFinite(Number(record.x)) ? Number(record.x) : 1,
        y: Number.isFinite(Number(record.y)) ? Number(record.y) : 1,
        z: Number.isFinite(Number(record.z)) ? Number(record.z) : 1,
    };
}

function compactObjectRef(value) {
    if (typeof value === 'string') return value;
    const record = asRecord(value);
    return record.name || record.type || null;
}

function countRecords(value) {
    return Object.keys(asRecord(value)).length;
}

function getLogicalVolume(projectState, lvName) {
    return asRecord(projectState.logical_volumes)[lvName] || null;
}

function getSolid(projectState, solidName) {
    return asRecord(projectState.solids)[solidName] || null;
}

function summarizeVisualAttributes(visAttributes) {
    const color = asRecord(asRecord(visAttributes).color);
    if (!Object.keys(color).length) return null;
    return {
        color_rgba: {
            r: numberOrZero(color.r),
            g: numberOrZero(color.g),
            b: numberOrZero(color.b),
            a: Number.isFinite(Number(color.a)) ? Number(color.a) : 1,
        },
    };
}

function classifySceneComponent(sceneObject, logicalVolume) {
    if (sceneObject.is_source) return 'particle_source';
    if (sceneObject.is_world_volume_placement) return 'world';
    if (sceneObject.is_assembly_container) return 'assembly_container';
    if (sceneObject.is_procedural_container) return 'procedural_container';
    if (sceneObject.is_procedural_instance) return 'procedural_instance';
    if (logicalVolume) return 'physical_volume';
    return 'scene_object';
}

function summarizeComponent(sceneObject, projectState, hiddenIds) {
    const logicalVolume = getLogicalVolume(projectState, sceneObject.volume_ref);
    const solidRef = logicalVolume?.solid_ref || compactObjectRef(sceneObject.solid_ref_for_threejs);
    const solid = solidRef ? getSolid(projectState, solidRef) : null;
    const isHidden = hiddenIds.has(sceneObject.id) || hiddenIds.has(sceneObject.canonical_id);
    const isWorld = Boolean(sceneObject.is_world_volume_placement);
    const isContainer = Boolean(sceneObject.is_assembly_container || sceneObject.is_procedural_container);
    const isRenderable = !isWorld && !isContainer && !sceneObject.is_source;

    return {
        id: sceneObject.id || null,
        canonical_id: sceneObject.canonical_id || sceneObject.id || null,
        name: sceneObject.name || sceneObject.id || '(unnamed)',
        parent_id: sceneObject.parent_id || null,
        owner_pv_id: sceneObject.owner_pv_id || null,
        type: classifySceneComponent(sceneObject, logicalVolume),
        logical_volume: sceneObject.volume_ref || null,
        solid_ref: solidRef || null,
        solid_type: solid?.type || asRecord(sceneObject.solid_ref_for_threejs).type || null,
        material_ref: logicalVolume?.material_ref || null,
        is_sensitive: Boolean(logicalVolume?.is_sensitive),
        is_renderable: isRenderable,
        is_hidden: isHidden,
        is_world: isWorld,
        is_source: Boolean(sceneObject.is_source),
        is_procedural_instance: Boolean(sceneObject.is_procedural_instance),
        copy_number: sceneObject.copy_number ?? null,
        local_transform: {
            position_mm: copyVector(sceneObject.position),
            rotation_rad: copyVector(sceneObject.rotation),
            rotation_deg: radiansVectorToDegrees(sceneObject.rotation),
            scale: normalizeScale(sceneObject.scale),
        },
        visual: summarizeVisualAttributes(sceneObject.vis_attributes || logicalVolume?.vis_attributes),
        source: sceneObject.is_source ? {
            gps_commands: asRecord(sceneObject.gps_commands),
            confine_to_pv: sceneObject.confine_to_pv || null,
            volume_link_id: sceneObject.volume_link_id || null,
        } : null,
    };
}

function summarizeSources(projectState) {
    return objectValues(projectState.sources).map((source) => ({
        id: source.id || null,
        name: source.name || null,
        type: source.type || source.source_type || 'gps',
        active: asArray(projectState.active_source_ids).includes(source.id),
        confine_to_pv: source.confine_to_pv || null,
        volume_link_id: source.volume_link_id || null,
        position: source.position || null,
        rotation: source.rotation || null,
        gps_commands: asRecord(source.gps_commands),
        ion_params: source.ion_params || null,
    }));
}

function summarizeScoring(projectState) {
    const scoring = asRecord(projectState.scoring);
    const meshes = asArray(scoring.scoring_meshes);
    const tallies = asArray(scoring.tally_requests);
    return {
        schema_version: scoring.schema_version || null,
        mesh_count: meshes.length,
        enabled_mesh_count: meshes.filter((entry) => entry.enabled !== false).length,
        tally_count: tallies.length,
        enabled_tally_count: tallies.filter((entry) => entry.enabled !== false).length,
        scoring_meshes: meshes.map((entry) => ({
            mesh_id: entry.mesh_id || null,
            name: entry.name || null,
            mesh_type: entry.mesh_type || 'box',
            enabled: entry.enabled !== false,
            reference_frame: entry.reference_frame || 'world',
            geometry: entry.geometry || {},
            bins: entry.bins || {},
        })),
        tally_requests: tallies.map((entry) => ({
            tally_id: entry.tally_id || null,
            name: entry.name || null,
            enabled: entry.enabled !== false,
            quantity: entry.quantity || null,
            mesh_ref: entry.mesh_ref || null,
        })),
        run_manifest_defaults: scoring.run_manifest_defaults || {},
    };
}

function summarizeEnvironment(projectState) {
    const environment = asRecord(projectState.environment);
    return {
        global_uniform_magnetic_field: environment.global_uniform_magnetic_field || null,
        global_uniform_electric_field: environment.global_uniform_electric_field || null,
        local_uniform_magnetic_field: environment.local_uniform_magnetic_field || null,
        local_uniform_electric_field: environment.local_uniform_electric_field || null,
        region_cuts_and_limits: environment.region_cuts_and_limits || null,
        optical_physics: Boolean(environment.optical_physics),
        process_inactivation: asArray(environment.process_inactivation),
    };
}

function summarizeCadImports(projectState) {
    return asArray(projectState.cad_imports).map((entry) => ({
        import_id: entry.import_id || null,
        source: entry.source || null,
        options: entry.options || null,
        smart_import_summary: entry.smart_import_summary || null,
        reimport_diff_summary: entry.reimport_diff_summary || null,
        created_object_ids: entry.created_object_ids || null,
        created_group_names: entry.created_group_names || null,
    }));
}

function summarizeDetectorFeatureGenerators(projectState) {
    return asArray(projectState.detector_feature_generators).map((entry) => ({
        generator_id: entry.generator_id || entry.id || null,
        name: entry.name || null,
        generator_type: entry.generator_type || null,
        status: entry.status || null,
        target: entry.target || null,
        created_object_refs: entry.created_object_refs || null,
    }));
}

function buildMaterialAssignments(projectState) {
    return objectValues(projectState.logical_volumes).map((lv) => ({
        logical_volume: lv.name || null,
        solid_ref: lv.solid_ref || null,
        material_ref: lv.material_ref || null,
        is_sensitive: Boolean(lv.is_sensitive),
    }));
}

export function resolveVisualVerificationViewSpecs(requestedViews = null) {
    if (!requestedViews) return [...DEFAULT_VISUAL_VERIFICATION_VIEW_SPECS];
    const requestedList = Array.isArray(requestedViews) ? requestedViews : [requestedViews];
    const requestedNames = new Set(requestedList.map((name) => String(name)));
    return DEFAULT_VISUAL_VERIFICATION_VIEW_SPECS.filter((spec) => requestedNames.has(spec.name));
}

export function buildVisualVerificationMetadata({
    projectName = 'untitled',
    projectState = {},
    sceneDescription = [],
    hiddenPvIds = [],
    generatedAt = null,
    captureOptions = {},
    sceneBounds = null,
} = {}) {
    const hiddenIds = new Set(asArray(hiddenPvIds).map((id) => String(id)));
    const components = asArray(sceneDescription).map((sceneObject) => (
        summarizeComponent(asRecord(sceneObject), asRecord(projectState), hiddenIds)
    ));
    const sensitiveLogicalVolumes = objectValues(projectState.logical_volumes)
        .filter((lv) => Boolean(lv.is_sensitive))
        .map((lv) => ({
            name: lv.name || null,
            solid_ref: lv.solid_ref || null,
            material_ref: lv.material_ref || null,
        }));

    return {
        kind: VISUAL_VERIFICATION_PACKET_KIND,
        schema_version: VISUAL_VERIFICATION_PACKET_SCHEMA_VERSION,
        generated_at: generatedAt || new Date().toISOString(),
        project: {
            name: projectName || 'untitled',
            project_scope_id: projectState.project_scope_id || null,
            world_volume_ref: projectState.world_volume_ref || null,
        },
        coordinate_system: {
            length_unit: 'mm',
            rotation_unit: 'radians in saved transforms; degrees duplicated for readability',
            axes: {
                x: 'Three.js/GDML X axis',
                y: 'Three.js/GDML Y axis',
                z: 'Three.js/GDML Z axis',
            },
        },
        capture_request: {
            requested_views: resolveVisualVerificationViewSpecs(captureOptions.views).map((spec) => spec.name),
            include_images: captureOptions.include_images !== false,
            image_width: captureOptions.image_width || captureOptions.width || null,
            image_height: captureOptions.image_height || captureOptions.height || null,
        },
        scene_summary: {
            component_count: components.length,
            renderable_component_count: components.filter((component) => component.is_renderable).length,
            hidden_component_count: components.filter((component) => component.is_hidden).length,
            material_count: countRecords(projectState.materials),
            solid_count: countRecords(projectState.solids),
            logical_volume_count: countRecords(projectState.logical_volumes),
            sensitive_logical_volume_count: sensitiveLogicalVolumes.length,
            particle_source_count: countRecords(projectState.sources),
            cad_import_count: asArray(projectState.cad_imports).length,
            detector_feature_generator_count: asArray(projectState.detector_feature_generators).length,
            scene_bounds_mm: sceneBounds,
        },
        components,
        assignments: {
            material_assignments: buildMaterialAssignments(asRecord(projectState)),
            sensitive_logical_volumes: sensitiveLogicalVolumes,
            active_source_ids: asArray(projectState.active_source_ids),
            sources: summarizeSources(asRecord(projectState)),
            scoring: summarizeScoring(asRecord(projectState)),
            environment: summarizeEnvironment(asRecord(projectState)),
            cad_imports: summarizeCadImports(asRecord(projectState)),
            detector_feature_generators: summarizeDetectorFeatureGenerators(asRecord(projectState)),
        },
        model_guidance: {
            intended_use: 'Use the screenshots and component metadata together to check detector geometry alignment, missing pieces, scale, materials, sensitive detector assignment, sources, scoring, fields, and CAD import annotations.',
            visual_caveats: [
                'Screenshots are rendered from the current AIRPET scene graph, not from a Geant4 navigation run.',
                'Transparent or hidden components may be hard to see visually; inspect component metadata before deciding they are absent.',
                'Perspective views can make small misalignments subtle; compare front, side, top, and isometric views together.',
            ],
        },
    };
}
