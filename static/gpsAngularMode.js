const DIRECTED_MODE = 'beam1d';
const ISOTROPIC_MODE = 'iso';

export function normalizeGpsAngularType(value, fallback = DIRECTED_MODE) {
    const raw = String(value ?? '').trim().toLowerCase();

    if (raw === '') {
        return fallback;
    }

    if (raw === ISOTROPIC_MODE || raw === 'isotropic') {
        return ISOTROPIC_MODE;
    }

    if (
        raw === DIRECTED_MODE
        || raw === 'direction'
        || raw === 'directed'
        || raw === 'beam'
        || raw === 'mono'
        || raw === 'monodirectional'
        || raw === 'pencil'
        || raw === 'pencilbeam'
        || raw === 'pencil_beam'
    ) {
        return DIRECTED_MODE;
    }

    return fallback;
}

export function isIsotropicGpsAngularType(value) {
    return normalizeGpsAngularType(value, ISOTROPIC_MODE) === ISOTROPIC_MODE;
}

export function isDirectedGpsAngularType(value) {
    return normalizeGpsAngularType(value, DIRECTED_MODE) === DIRECTED_MODE;
}

export function parseGpsDirectionVector(value, fallback = { x: '0', y: '0', z: '1' }) {
    if (value && typeof value === 'object') {
        const x = value.x ?? fallback.x;
        const y = value.y ?? fallback.y;
        const z = value.z ?? fallback.z;
        return { x: String(x), y: String(y), z: String(z) };
    }

    const tokens = String(value ?? '')
        .replace(/,/g, ' ')
        .trim()
        .split(/\s+/)
        .filter(Boolean);

    if (tokens.length !== 3) {
        return { x: String(fallback.x), y: String(fallback.y), z: String(fallback.z) };
    }

    return { x: tokens[0], y: tokens[1], z: tokens[2] };
}

export function getNormalizedGpsDirectionVector(value, fallback = { x: 0, y: 0, z: 1 }) {
    const parsed = parseGpsDirectionVector(value, fallback);
    const x = Number(parsed.x);
    const y = Number(parsed.y);
    const z = Number(parsed.z);

    if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
        return { ...fallback };
    }

    const norm = Math.hypot(x, y, z);
    if (norm <= 1e-12) {
        return { ...fallback };
    }

    return {
        x: x / norm,
        y: y / norm,
        z: z / norm,
    };
}
