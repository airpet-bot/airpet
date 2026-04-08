function normalizeString(value, fallback = '') {
    const text = String(value ?? '').trim();
    return text || fallback;
}

function normalizeObjectRef(rawRef) {
    const ref = rawRef && typeof rawRef === 'object' ? rawRef : {};
    const id = normalizeString(ref.id, '');
    const name = normalizeString(ref.name, '');

    return {
        id,
        name,
    };
}

function resolveObjectName(rawRef, objectsByName) {
    const ref = normalizeObjectRef(rawRef);
    const registry = objectsByName && typeof objectsByName === 'object' ? objectsByName : {};

    if (ref.name && Object.prototype.hasOwnProperty.call(registry, ref.name)) {
        return ref.name;
    }

    if (ref.id) {
        for (const [candidateName, candidate] of Object.entries(registry)) {
            if (candidate && normalizeString(candidate.id, '') === ref.id) {
                return candidateName;
            }
        }
    }

    return ref.name || ref.id || '';
}

function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) {
        return normalizeString(value, '0');
    }
    return String(Number(number.toFixed(6)));
}

function pluralize(count, singular, plural = `${singular}s`) {
    return `${count} ${count === 1 ? singular : plural}`;
}

function buildListValue(items, emptyText = 'None') {
    const normalized = Array.isArray(items)
        ? items.map((item) => normalizeString(item, '')).filter(Boolean)
        : [];

    if (normalized.length === 0) {
        return { text: emptyText, title: emptyText };
    }

    const preview = normalized.slice(0, 3).join(', ');
    return {
        text: normalized.length > 3 ? `${preview}, +${normalized.length - 3} more` : preview,
        title: normalized.join('\n'),
    };
}

function getLogicalVolumeNamesForSolid(projectState, solidName) {
    const logicalVolumes = projectState?.logical_volumes || {};
    return Object.values(logicalVolumes)
        .filter((lv) => lv && normalizeString(lv.solid_ref, '') === solidName)
        .map((lv) => normalizeString(lv.name, ''))
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b));
}

function buildDefaultGeneratorName(targetSolidName) {
    const base = normalizeString(targetSolidName, 'patterned_holes').replace(/[^\w]+/g, '_');
    return `${base}_holes`;
}

function normalizeSelectedItems(selectedItems) {
    return Array.isArray(selectedItems) ? selectedItems.filter((item) => item && typeof item === 'object') : [];
}

function resolveSelectedTargetSolidName(projectState, selectedItems) {
    const solids = projectState?.solids || {};
    const logicalVolumes = projectState?.logical_volumes || {};

    for (const item of normalizeSelectedItems(selectedItems)) {
        if (item.type === 'solid') {
            const solidName = normalizeString(item.name || item.id, '');
            if (solidName && solids[solidName]?.type === 'box') {
                return solidName;
            }
        }

        if (item.type === 'logical_volume') {
            const lvName = normalizeString(item.name || item.id, '');
            const lv = logicalVolumes[lvName];
            const solidName = normalizeString(lv?.solid_ref, '');
            if (solidName && solids[solidName]?.type === 'box') {
                return solidName;
            }
        }
    }

    return '';
}

export function listDetectorFeatureGeneratorTargetOptions(projectState) {
    const solids = projectState?.solids || {};

    return Object.values(solids)
        .filter((solid) => solid && solid.type === 'box')
        .map((solid) => {
            const solidName = normalizeString(solid.name, '');
            const logicalVolumeNames = getLogicalVolumeNamesForSolid(projectState, solidName);
            return {
                id: normalizeString(solid.id, ''),
                name: solidName,
                logicalVolumeNames,
                logicalVolumeSummary: logicalVolumeNames.length > 0
                    ? pluralize(logicalVolumeNames.length, 'logical volume')
                    : 'no matching logical volumes yet',
            };
        })
        .sort((a, b) => a.name.localeCompare(b.name));
}

export function buildDetectorFeatureGeneratorEditorModel(projectState, generatorEntry = null, selectedItems = []) {
    const targetOptions = listDetectorFeatureGeneratorTargetOptions(projectState);
    const fallbackTargetName = targetOptions[0]?.name || '';
    const existingTargetName = generatorEntry
        ? resolveObjectName(generatorEntry.target?.solid_ref, projectState?.solids || {})
        : '';
    const selectedTargetName = existingTargetName
        || resolveSelectedTargetSolidName(projectState, selectedItems)
        || fallbackTargetName;
    const selectedTarget = targetOptions.find((option) => option.name === selectedTargetName) || targetOptions[0] || null;

    const pattern = generatorEntry?.pattern || {};
    const pitch = pattern.pitch_mm || {};
    const originOffset = pattern.origin_offset_mm || {};
    const hole = generatorEntry?.hole || {};

    return {
        isEdit: Boolean(generatorEntry),
        generatorId: normalizeString(generatorEntry?.generator_id, ''),
        title: generatorEntry ? 'Edit Patterned-Hole Generator' : 'New Patterned-Hole Generator',
        confirmLabel: generatorEntry ? 'Save & Generate' : 'Create & Generate',
        targetOptions,
        selectedTargetName: selectedTarget?.name || '',
        selectedTargetId: selectedTarget?.id || '',
        selectedTargetLogicalVolumeNames: selectedTarget?.logicalVolumeNames || [],
        selectedTargetLogicalVolumeSummary: selectedTarget?.logicalVolumeSummary || 'No eligible box solids.',
        targetLocked: Boolean(generatorEntry),
        name: normalizeString(generatorEntry?.name, buildDefaultGeneratorName(selectedTarget?.name || 'patterned_holes')),
        countX: Number.isFinite(Number(pattern.count_x)) ? Number(pattern.count_x) : 3,
        countY: Number.isFinite(Number(pattern.count_y)) ? Number(pattern.count_y) : 3,
        pitchX: Number.isFinite(Number(pitch.x)) ? Number(pitch.x) : 5,
        pitchY: Number.isFinite(Number(pitch.y)) ? Number(pitch.y) : 5,
        offsetX: Number.isFinite(Number(originOffset.x)) ? Number(originOffset.x) : 0,
        offsetY: Number.isFinite(Number(originOffset.y)) ? Number(originOffset.y) : 0,
        holeDiameter: Number.isFinite(Number(hole.diameter_mm)) ? Number(hole.diameter_mm) : 2,
        holeDepth: Number.isFinite(Number(hole.depth_mm)) ? Number(hole.depth_mm) : 5,
    };
}

export function describeDetectorFeatureGenerator(rawEntry, projectState) {
    const entry = rawEntry && typeof rawEntry === 'object' ? rawEntry : {};
    const target = entry.target && typeof entry.target === 'object' ? entry.target : {};
    const pattern = entry.pattern && typeof entry.pattern === 'object' ? entry.pattern : {};
    const pitch = pattern.pitch_mm && typeof pattern.pitch_mm === 'object' ? pattern.pitch_mm : {};
    const originOffset = pattern.origin_offset_mm && typeof pattern.origin_offset_mm === 'object' ? pattern.origin_offset_mm : {};
    const hole = entry.hole && typeof entry.hole === 'object' ? entry.hole : {};
    const realization = entry.realization && typeof entry.realization === 'object' ? entry.realization : {};
    const generatedRefs = realization.generated_object_refs && typeof realization.generated_object_refs === 'object'
        ? realization.generated_object_refs
        : {};

    const targetSolidName = resolveObjectName(target.solid_ref, projectState?.solids || {}) || 'unknown_target';
    const resultSolidName = realization.result_solid_ref
        ? resolveObjectName(realization.result_solid_ref, projectState?.solids || {})
        : '';

    const targetedLogicalVolumeNames = Array.isArray(target.logical_volume_refs) && target.logical_volume_refs.length > 0
        ? target.logical_volume_refs.map((ref) => resolveObjectName(ref, projectState?.logical_volumes || {})).filter(Boolean)
        : (Array.isArray(generatedRefs.logical_volume_refs) && generatedRefs.logical_volume_refs.length > 0
            ? generatedRefs.logical_volume_refs.map((ref) => resolveObjectName(ref, projectState?.logical_volumes || {})).filter(Boolean)
            : getLogicalVolumeNamesForSolid(projectState, targetSolidName));

    const generatedSolidNames = Array.isArray(generatedRefs.solid_refs)
        ? generatedRefs.solid_refs.map((ref) => resolveObjectName(ref, projectState?.solids || {})).filter(Boolean)
        : [];

    const generatorName = normalizeString(entry.name, 'patterned_holes');
    const generatorId = normalizeString(entry.generator_id, 'unknown_generator');
    const status = normalizeString(realization.status, 'spec_only');
    const countX = Number.isFinite(Number(pattern.count_x)) ? Number(pattern.count_x) : 0;
    const countY = Number.isFinite(Number(pattern.count_y)) ? Number(pattern.count_y) : 0;
    const pitchX = formatNumber(pitch.x);
    const pitchY = formatNumber(pitch.y);
    const offsetX = formatNumber(originOffset.x);
    const offsetY = formatNumber(originOffset.y);
    const holeDiameter = formatNumber(hole.diameter_mm);
    const holeDepth = formatNumber(hole.depth_mm);

    return {
        title: generatorName,
        summary: `Rectangular drilled holes on ${targetSolidName} · ${countX} x ${countY} @ ${pitchX} x ${pitchY} mm · dia ${holeDiameter} mm depth ${holeDepth} mm`,
        statusBadge: status === 'generated' ? 'generated' : 'spec only',
        detailRows: [
            { label: 'Generator ID', value: generatorId },
            { label: 'Status', value: status === 'generated' ? 'Generated geometry is current.' : 'Saved spec only.' },
            { label: 'Target Solid', value: targetSolidName },
            { label: 'Target Logical Volumes', value: buildListValue(targetedLogicalVolumeNames, 'All matching logical volumes') },
            { label: 'Pattern', value: `${countX} x ${countY} holes @ ${pitchX} x ${pitchY} mm` },
            { label: 'Origin Offset', value: `${offsetX}, ${offsetY} mm` },
            { label: 'Hole', value: `cylindrical dia ${holeDiameter} mm, depth ${holeDepth} mm` },
            { label: 'Result Solid', value: resultSolidName || 'Not generated yet' },
            { label: 'Generated Solids', value: buildListValue(generatedSolidNames, 'No generated solids recorded') },
        ],
    };
}
