const MAX_AI_SELECTION_ITEMS = 12;

const SUPPORTED_SELECTION_TYPES = new Set([
    'define',
    'material',
    'solid',
    'logical_volume',
    'assembly',
    'particle_source',
    'physical_volume',
]);

function cleanSelectionText(value) {
    return typeof value === 'string' ? value.trim() : '';
}
export function buildAiSelectionContext(selection, maxItems = MAX_AI_SELECTION_ITEMS) {
    if (!Array.isArray(selection)) return [];

    const limit = Math.max(1, Math.min(MAX_AI_SELECTION_ITEMS, Number(maxItems) || MAX_AI_SELECTION_ITEMS));
    const normalized = [];
    const seen = new Set();

    for (const item of selection) {
        if (!item || typeof item !== 'object') continue;

        const componentType = cleanSelectionText(item.type);
        if (!SUPPORTED_SELECTION_TYPES.has(componentType)) continue;

        const canonicalId = cleanSelectionText(item.canonical_id || item.id);
        const instanceId = cleanSelectionText(item.id);
        const name = cleanSelectionText(item.name);
        const stableKey = `${componentType}:${canonicalId || name}`;
        if ((!canonicalId && !name) || seen.has(stableKey)) continue;

        const entry = {
            component_type: componentType,
            id: canonicalId || name,
            name: name || canonicalId,
        };
        if (instanceId && instanceId !== entry.id) {
            entry.ui_instance_id = instanceId;
        }

        normalized.push(entry);
        seen.add(stableKey);
        if (normalized.length >= limit) break;
    }

    return normalized;
}
