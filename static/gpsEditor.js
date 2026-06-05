// static/gpsEditor.js
import * as ExpressionInput from './expressionInput.js';
import * as APIService from './apiService.js';
import {
    normalizeGpsAngularType,
    isIsotropicGpsAngularType,
    parseGpsDirectionVector,
} from './gpsAngularMode.js';

let modalElement, titleElement, nameInput, confirmButton, cancelButton;
let particleSelect, energyContainer, shapeSelect, shapeParamsContainer;
let linkedCheckbox, linkedSelect;
let sourceTypeSelect, gpsParticleControls, ionControls;
let ionZInput, ionAInput, ionQInput, ionEInput, ionLevelInput;
let advancedGpsPanel, advancedGpsEnabledInput, advancedGpsControls;
let onConfirmCallback = null;
let isEditMode = false;
let editingSourceId = null;
let currentAvailableVolumes = [];
let currentSourceCommands = {};

const ADVANCED_GPS_SOURCE_LIST_FIELDS = [
    { key: 'multiple_vertex', label: 'Multiple Vertex', type: 'bool', help: '/gps/source/multiplevertex' },
    { key: 'flat_sampling', label: 'Flat Sampling', type: 'bool', help: '/gps/source/flatsampling' },
];

const ADVANCED_GPS_SECTION_DEFINITIONS = [
    {
        id: 'control',
        title: 'Control',
        fields: [
            { key: 'verbose', label: 'Verbose', placeholder: '1' },
            { key: 'number', label: 'Particles / Vertex', placeholder: '1' },
            { key: 'time', label: 'Time', placeholder: '5 ns' },
            { key: 'polarization', label: 'Polarization', placeholder: '0 1 0' },
            { key: 'checkVolume', label: 'Check Volume', type: 'bool' },
        ],
    },
    {
        id: 'position',
        title: 'Position Distribution',
        fields: [
            { key: 'pos/type', label: 'Type', type: 'select', options: ['Point', 'Beam', 'Plane', 'Surface', 'Volume'] },
            { key: 'pos/shape', label: 'Shape', type: 'select', options: ['Circle', 'Annulus', 'Ellipse', 'Square', 'Rectangle', 'Sphere', 'Ellipsoid', 'Cylinder', 'EllipticCylinder', 'Para'] },
            { key: 'pos/centre', label: 'Centre', placeholder: '0 0 0 mm' },
            { key: 'pos/rot1', label: 'Rotation Axis 1', placeholder: '1 0 0' },
            { key: 'pos/rot2', label: 'Rotation Axis 2', placeholder: '0 1 0' },
            { key: 'pos/halfx', label: 'Half X', placeholder: '10 mm' },
            { key: 'pos/halfy', label: 'Half Y', placeholder: '10 mm' },
            { key: 'pos/halfz', label: 'Half Z', placeholder: '10 mm' },
            { key: 'pos/radius', label: 'Radius', placeholder: '10 mm' },
            { key: 'pos/inner_radius', label: 'Inner Radius', placeholder: '2 mm' },
            { key: 'pos/sigma_r', label: 'Sigma R', placeholder: '1 mm' },
            { key: 'pos/sigma_x', label: 'Sigma X', placeholder: '1 mm' },
            { key: 'pos/sigma_y', label: 'Sigma Y', placeholder: '1 mm' },
            { key: 'pos/paralp', label: 'Para Alpha', placeholder: '0 deg' },
            { key: 'pos/parthe', label: 'Para Theta', placeholder: '0 deg' },
            { key: 'pos/parphi', label: 'Para Phi', placeholder: '0 deg' },
            { key: 'pos/confine', label: 'Confine Volume', placeholder: 'DetectorPV' },
        ],
    },
    {
        id: 'angular',
        title: 'Angular Distribution',
        fields: [
            { key: 'ang/type', label: 'Type', type: 'select', options: ['iso', 'cos', 'planar', 'beam1d', 'beam2d', 'focused', 'user'] },
            { key: 'direction', label: 'Direction', placeholder: '0 0 1' },
            { key: 'ang/rot1', label: 'Rotation Axis 1', placeholder: '1 0 0' },
            { key: 'ang/rot2', label: 'Rotation Axis 2', placeholder: '0 1 0' },
            { key: 'ang/mintheta', label: 'Min Theta', placeholder: '0 deg' },
            { key: 'ang/maxtheta', label: 'Max Theta', placeholder: '180 deg' },
            { key: 'ang/minphi', label: 'Min Phi', placeholder: '0 deg' },
            { key: 'ang/maxphi', label: 'Max Phi', placeholder: '360 deg' },
            { key: 'ang/sigma_r', label: 'Sigma R', placeholder: '0.01 rad' },
            { key: 'ang/sigma_x', label: 'Sigma X', placeholder: '0.01 rad' },
            { key: 'ang/sigma_y', label: 'Sigma Y', placeholder: '0.01 rad' },
            { key: 'ang/focuspoint', label: 'Focus Point', placeholder: '0 0 100 mm' },
            { key: 'ang/user_coor', label: 'User Coordinates', type: 'bool' },
            { key: 'ang/surfnorm', label: 'Surface Normal', type: 'bool' },
        ],
    },
    {
        id: 'energy',
        title: 'Energy Distribution',
        fields: [
            { key: 'ene/type', label: 'Type', type: 'select', options: ['Mono', 'Lin', 'Pow', 'Exp', 'CPow', 'Gauss', 'Brem', 'Bbody', 'Cdg', 'User', 'Arb', 'Epn', 'LW'] },
            { key: 'ene/min', label: 'Minimum', placeholder: '1 keV' },
            { key: 'ene/max', label: 'Maximum', placeholder: '10 MeV' },
            { key: 'ene/mono', label: 'Mono Energy', placeholder: '511 keV' },
            { key: 'ene/sigma', label: 'Sigma', placeholder: '5 keV' },
            { key: 'ene/alpha', label: 'Alpha', placeholder: '-1' },
            { key: 'ene/temp', label: 'Temperature', placeholder: '2.7' },
            { key: 'ene/ezero', label: 'E Zero', placeholder: '1 MeV' },
            { key: 'ene/gradient', label: 'Gradient', placeholder: '1' },
            { key: 'ene/intercept', label: 'Intercept', placeholder: '0' },
            { key: 'ene/biasAlpha', label: 'Bias Alpha', placeholder: '1' },
            { key: 'ene/calculate', label: 'Calculate', type: 'bool' },
            { key: 'ene/emspec', label: 'Emission Spectrum', type: 'bool' },
            { key: 'ene/diffspec', label: 'Differential Spectrum', type: 'bool' },
            { key: 'ene/applyEneWeight', label: 'Apply Energy Weight', type: 'bool' },
        ],
    },
    {
        id: 'ion',
        title: 'Advanced Ion',
        fields: [
            { key: 'excitation_level', label: 'Excitation Level', placeholder: '0-9' },
        ],
    },
];

const ADVANCED_GPS_HISTOGRAM_TYPES = ['biasx', 'biasy', 'biasz', 'biast', 'biasp', 'biase', 'biaspt', 'biaspp', 'theta', 'phi', 'energy', 'arb', 'epn'];
const ADVANCED_GPS_HISTOGRAM_INTERPOLATIONS = ['Lin', 'Log', 'Exp', 'Spline'];

function isPointSourceShape(shape) {
    return (shape || 'Point') === 'Point';
}

function getObjectKeys(obj) {
    return obj && typeof obj === 'object' && !Array.isArray(obj) ? Object.keys(obj) : [];
}

function hasAdvancedGpsContent(advancedGps, sequence = []) {
    return getObjectKeys(advancedGps).some((key) => key !== 'schema_version') || (Array.isArray(sequence) && sequence.length > 0);
}

function trimSingleLine(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[\r\n]+/g, ' ').trim();
}

function coerceOptionalBool(value) {
    if (value === null || value === undefined || value === '') return undefined;
    if (typeof value === 'boolean') return value;
    const normalized = String(value).trim().toLowerCase();
    if (['true', '1', 'yes', 'on'].includes(normalized)) return true;
    if (['false', '0', 'no', 'off'].includes(normalized)) return false;
    return undefined;
}

function boolSelectValue(value) {
    const coerced = coerceOptionalBool(value);
    if (coerced === undefined) return '';
    return coerced ? 'true' : 'false';
}

function isObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value);
}

function getNestedValue(source, sectionId, key) {
    if (!isObject(source)) return '';
    const section = source[sectionId];
    if (!isObject(section)) return '';
    if (Object.prototype.hasOwnProperty.call(section, key)) {
        return section[key];
    }

    const bareKey = key.includes('/') ? key.split('/').pop() : key;
    const snakeKey = bareKey.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
    const aliases = [bareKey, snakeKey];
    for (const alias of aliases) {
        if (Object.prototype.hasOwnProperty.call(section, alias)) {
            return section[alias];
        }
    }
    return '';
}

function normalizeInputValue(value) {
    if (Array.isArray(value)) {
        return value.map((entry) => trimSingleLine(entry)).filter(Boolean).join(' ');
    }
    if (isObject(value)) {
        const unit = trimSingleLine(value.unit);
        if (['x', 'y', 'z'].every((axis) => Object.prototype.hasOwnProperty.call(value, axis))) {
            const vector = ['x', 'y', 'z'].map((axis) => trimSingleLine(value[axis])).join(' ');
            return unit ? `${vector} ${unit}` : vector;
        }
    }
    return trimSingleLine(value);
}

function normalizeSectionPayload(rawSection, fields) {
    const normalized = {};
    if (!isObject(rawSection)) return normalized;
    for (const field of fields) {
        const rawValue = rawSection[field.key];
        if (field.type === 'bool') {
            const coerced = coerceOptionalBool(rawValue);
            if (coerced !== undefined) {
                normalized[field.key] = coerced;
            }
            continue;
        }
        const value = normalizeInputValue(rawValue);
        if (value) {
            normalized[field.key] = value;
        }
    }
    return normalized;
}

function normalizeHistogramPoints(points) {
    if (Array.isArray(points)) {
        return points.map((point) => normalizeInputValue(point)).filter(Boolean);
    }
    return String(points || '')
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
}

function normalizeAdvancedGpsHistograms(rawHistograms) {
    if (!Array.isArray(rawHistograms)) return [];
    return rawHistograms
        .map((rawEntry) => {
            if (!isObject(rawEntry)) return null;
            const type = trimSingleLine(rawEntry.type || rawEntry.hist_type);
            if (!type) return null;
            const entry = {
                type,
                enabled: coerceOptionalBool(rawEntry.enabled) !== false,
            };
            const reset = coerceOptionalBool(rawEntry.reset);
            if (reset !== undefined) entry.reset = reset;
            const file = trimSingleLine(rawEntry.file);
            if (file) entry.file = file;
            const points = normalizeHistogramPoints(rawEntry.points);
            if (points.length > 0) entry.points = points;
            const interpolation = trimSingleLine(rawEntry.interpolation || rawEntry.inter);
            if (interpolation) entry.interpolation = interpolation;
            return entry;
        })
        .filter(Boolean);
}

function normalizeGpsCommandSequence(rawSequence) {
    if (!Array.isArray(rawSequence)) return [];
    return rawSequence
        .map((entry) => {
            if (typeof entry === 'string') {
                const stripped = entry.trim().replace(/^\/gps\//, '');
                const [rawCommand, ...rest] = stripped.split(/\s+/);
                const command = trimSingleLine(rawCommand);
                if (!command) return null;
                return {
                    command,
                    value: trimSingleLine(rest.join(' ')),
                    enabled: true,
                };
            }
            if (!isObject(entry)) return null;
            const command = trimSingleLine(entry.command || entry.cmd);
            if (!command) return null;
            const normalizedCommand = command.replace(/^\/gps\//, '');
            if (!normalizedCommand) return null;
            return {
                command: normalizedCommand,
                value: trimSingleLine(entry.value),
                enabled: coerceOptionalBool(entry.enabled) !== false,
            };
        })
        .filter(Boolean);
}

export function buildAdvancedGpsPayloadFromSections(rawState = {}) {
    const advancedGps = {};
    const transformMode = trimSingleLine(rawState.airpet_transform_mode || rawState.transform_mode);
    if (transformMode && transformMode !== 'airpet') {
        advancedGps.airpet_transform_mode = transformMode;
    }

    const sourceList = normalizeSectionPayload(
        rawState.source_list,
        ADVANCED_GPS_SOURCE_LIST_FIELDS,
    );
    if (getObjectKeys(sourceList).length > 0) {
        advancedGps.source_list = sourceList;
    }

    for (const sectionDef of ADVANCED_GPS_SECTION_DEFINITIONS) {
        const sectionPayload = normalizeSectionPayload(rawState[sectionDef.id], sectionDef.fields);
        if (getObjectKeys(sectionPayload).length > 0) {
            advancedGps[sectionDef.id] = sectionPayload;
        }
    }

    const histograms = normalizeAdvancedGpsHistograms(rawState.histograms);
    if (histograms.length > 0) {
        advancedGps.histograms = histograms;
    }

    return {
        advanced_gps: advancedGps,
        gps_command_sequence: normalizeGpsCommandSequence(rawState.gps_command_sequence),
    };
}

function createOption(value, label = value) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    return option;
}

function fieldInputId(sectionId, key) {
    return `gpsAdvanced_${sectionId}_${key.replace(/[^a-zA-Z0-9]/g, '_')}`;
}

function createAdvancedField(sectionId, field, value = '') {
    const wrapper = document.createElement('div');
    wrapper.className = 'gps-advanced-field';

    const label = document.createElement('label');
    const inputId = fieldInputId(sectionId, field.key);
    label.htmlFor = inputId;
    label.textContent = field.label;
    wrapper.appendChild(label);

    let input;
    if (field.type === 'select') {
        input = document.createElement('select');
        input.appendChild(createOption('', 'Unspecified'));
        for (const optionValue of field.options || []) {
            input.appendChild(createOption(optionValue));
        }
        input.value = trimSingleLine(value);
    } else if (field.type === 'bool') {
        input = document.createElement('select');
        input.appendChild(createOption('', 'Unspecified'));
        input.appendChild(createOption('true', 'true'));
        input.appendChild(createOption('false', 'false'));
        input.value = boolSelectValue(value);
    } else {
        input = document.createElement('input');
        input.type = 'text';
        input.placeholder = field.placeholder || '';
        input.value = normalizeInputValue(value);
    }
    input.id = inputId;
    input.dataset.gpsAdvancedSection = sectionId;
    input.dataset.gpsAdvancedKey = field.key;
    input.dataset.gpsAdvancedType = field.type || 'text';
    if (field.help) input.title = field.help;
    wrapper.appendChild(input);
    return wrapper;
}

export function initGpsEditor(callbacks) {
    onConfirmCallback = callbacks.onConfirm;

    modalElement = document.getElementById('gpsEditorModal');
    titleElement = document.getElementById('gpsEditorTitle');
    nameInput = document.getElementById('gpsEditorName');
    particleSelect = document.getElementById('gpsEditorParticle');
    energyContainer = document.getElementById('gps-energy-params');
    shapeSelect = document.getElementById('gpsEditorShape');
    shapeParamsContainer = document.getElementById('gps-shape-params');
    confirmButton = document.getElementById('gpsEditorConfirm');
    cancelButton = document.getElementById('gpsEditorCancel');

    linkedCheckbox = document.getElementById('gpsLinkedVolumeEnabled');
    linkedSelect = document.getElementById('gpsLinkedVolumeSelect'); // This is now an Input

    sourceTypeSelect = document.getElementById('gpsEditorSourceType');
    gpsParticleControls = document.getElementById('gps-particle-controls');
    ionControls = document.getElementById('gps-ion-controls');
    ionZInput = document.getElementById('gpsIonZ');
    ionAInput = document.getElementById('gpsIonA');
    ionQInput = document.getElementById('gpsIonQ');
    ionEInput = document.getElementById('gpsIonE');
    ionLevelInput = document.getElementById('gpsIonLevel');
    advancedGpsPanel = document.getElementById('gpsAdvancedGpsPanel');
    advancedGpsEnabledInput = document.getElementById('gpsAdvancedGpsEnabled');
    advancedGpsControls = document.getElementById('gps-advanced-gps-controls');

    // Wire up events
    cancelButton.addEventListener('click', hide);
    confirmButton.addEventListener('click', handleConfirm);
    shapeSelect.addEventListener('change', () => renderShapeParamsUI());
    linkedCheckbox.addEventListener('change', toggleLinkedMode);
    sourceTypeSelect.addEventListener('change', toggleSourceType);
    advancedGpsEnabledInput?.addEventListener('change', toggleAdvancedGpsControls);

    console.log("GPS Editor Initialized.");
}

// handleAutoFill function is removed as per instructions.

function toggleAdvancedGpsControls() {
    if (!advancedGpsControls || !advancedGpsEnabledInput) return;
    advancedGpsControls.style.display = advancedGpsEnabledInput.checked ? 'flex' : 'none';
}

function appendAdvancedSectionCard(parent, sectionDef, advancedGps) {
    const card = document.createElement('section');
    card.className = 'gps-advanced-card';

    const title = document.createElement('h5');
    title.textContent = sectionDef.title;
    card.appendChild(title);

    const grid = document.createElement('div');
    grid.className = 'gps-advanced-grid';
    for (const field of sectionDef.fields) {
        grid.appendChild(createAdvancedField(
            sectionDef.id,
            field,
            getNestedValue(advancedGps, sectionDef.id, field.key),
        ));
    }
    card.appendChild(grid);
    parent.appendChild(card);
}

function appendTransformAndSourceListCard(parent, advancedGps) {
    const card = document.createElement('section');
    card.className = 'gps-advanced-card';

    const title = document.createElement('h5');
    title.textContent = 'Runtime Transform and Source List';
    card.appendChild(title);

    const grid = document.createElement('div');
    grid.className = 'gps-advanced-grid';

    const transformField = document.createElement('div');
    transformField.className = 'gps-advanced-field';
    const transformLabel = document.createElement('label');
    transformLabel.htmlFor = 'gpsAdvanced_airpet_transform_mode';
    transformLabel.textContent = 'AIRPET Transform Mode';
    transformField.appendChild(transformLabel);
    const transformSelect = document.createElement('select');
    transformSelect.id = 'gpsAdvanced_airpet_transform_mode';
    transformSelect.dataset.gpsAdvancedRoot = 'airpet_transform_mode';
    transformSelect.appendChild(createOption('airpet', 'airpet: use source transform'));
    transformSelect.appendChild(createOption('structured', 'structured: use /gps pos/ang commands'));
    transformSelect.appendChild(createOption('none', 'none: no automatic transform'));
    transformSelect.value = advancedGps?.airpet_transform_mode || 'airpet';
    transformField.appendChild(transformSelect);
    grid.appendChild(transformField);

    for (const field of ADVANCED_GPS_SOURCE_LIST_FIELDS) {
        grid.appendChild(createAdvancedField(
            'source_list',
            field,
            getNestedValue(advancedGps, 'source_list', field.key),
        ));
    }

    card.appendChild(grid);

    const note = document.createElement('p');
    note.className = 'gps-advanced-note';
    note.textContent = "Default 'airpet' writes the source transform after structured GPS commands. Use 'structured' when pos/centre or angular rotation should come only from this panel.";
    card.appendChild(note);

    parent.appendChild(card);
}

function formatHistogramPoints(points) {
    if (!Array.isArray(points)) return '';
    return points.map((point) => normalizeInputValue(point)).filter(Boolean).join('\n');
}

function appendHistogramRow(tbody, histogram = {}) {
    const row = document.createElement('tr');
    row.dataset.gpsAdvancedHistogramRow = 'true';

    const enabledCell = document.createElement('td');
    const enabled = document.createElement('input');
    enabled.type = 'checkbox';
    enabled.dataset.gpsAdvancedHistogramField = 'enabled';
    enabled.checked = histogram.enabled !== false;
    enabledCell.appendChild(enabled);
    row.appendChild(enabledCell);

    const typeCell = document.createElement('td');
    const typeSelect = document.createElement('select');
    typeSelect.dataset.gpsAdvancedHistogramField = 'type';
    typeSelect.appendChild(createOption('', 'Type'));
    for (const histType of ADVANCED_GPS_HISTOGRAM_TYPES) {
        typeSelect.appendChild(createOption(histType));
    }
    typeSelect.value = trimSingleLine(histogram.type);
    typeCell.appendChild(typeSelect);
    row.appendChild(typeCell);

    const resetCell = document.createElement('td');
    const reset = document.createElement('input');
    reset.type = 'checkbox';
    reset.dataset.gpsAdvancedHistogramField = 'reset';
    reset.checked = histogram.reset === true;
    resetCell.appendChild(reset);
    row.appendChild(resetCell);

    const fileCell = document.createElement('td');
    const fileInput = document.createElement('input');
    fileInput.type = 'text';
    fileInput.placeholder = 'hist.dat';
    fileInput.dataset.gpsAdvancedHistogramField = 'file';
    fileInput.value = trimSingleLine(histogram.file);
    fileCell.appendChild(fileInput);
    row.appendChild(fileCell);

    const pointsCell = document.createElement('td');
    const pointsArea = document.createElement('textarea');
    pointsArea.placeholder = 'one point per line, e.g.\n1 keV 0.2\n10 keV 1.0';
    pointsArea.dataset.gpsAdvancedHistogramField = 'points';
    pointsArea.value = formatHistogramPoints(histogram.points);
    pointsCell.appendChild(pointsArea);
    row.appendChild(pointsCell);

    const interpolationCell = document.createElement('td');
    const interpolationSelect = document.createElement('select');
    interpolationSelect.dataset.gpsAdvancedHistogramField = 'interpolation';
    interpolationSelect.appendChild(createOption('', 'None'));
    for (const interpolation of ADVANCED_GPS_HISTOGRAM_INTERPOLATIONS) {
        interpolationSelect.appendChild(createOption(interpolation));
    }
    interpolationSelect.value = trimSingleLine(histogram.interpolation);
    interpolationCell.appendChild(interpolationSelect);
    row.appendChild(interpolationCell);

    const actionCell = document.createElement('td');
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'gps-advanced-small-button';
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', () => row.remove());
    actionCell.appendChild(removeButton);
    row.appendChild(actionCell);

    tbody.appendChild(row);
}

function appendHistogramsCard(parent, histograms = []) {
    const card = document.createElement('section');
    card.className = 'gps-advanced-card';
    const title = document.createElement('h5');
    title.textContent = 'Histograms and Biasing';
    card.appendChild(title);

    const table = document.createElement('table');
    table.className = 'gps-advanced-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>On</th>
                <th>Type</th>
                <th>Reset</th>
                <th>File</th>
                <th>Points</th>
                <th>Interpolation</th>
                <th></th>
            </tr>
        </thead>
    `;
    const tbody = document.createElement('tbody');
    table.appendChild(tbody);
    for (const histogram of histograms || []) {
        appendHistogramRow(tbody, histogram);
    }
    card.appendChild(table);

    const actions = document.createElement('div');
    actions.className = 'gps-advanced-row-actions';
    const addButton = document.createElement('button');
    addButton.type = 'button';
    addButton.className = 'gps-advanced-small-button';
    addButton.textContent = 'Add Histogram';
    addButton.addEventListener('click', () => appendHistogramRow(tbody, { enabled: true }));
    actions.appendChild(addButton);
    card.appendChild(actions);
    parent.appendChild(card);
}

function appendCommandSequenceRow(tbody, entry = {}) {
    const row = document.createElement('tr');
    row.dataset.gpsCommandSequenceRow = 'true';

    const enabledCell = document.createElement('td');
    const enabled = document.createElement('input');
    enabled.type = 'checkbox';
    enabled.dataset.gpsCommandSequenceField = 'enabled';
    enabled.checked = entry.enabled !== false;
    enabledCell.appendChild(enabled);
    row.appendChild(enabledCell);

    const commandCell = document.createElement('td');
    const commandInput = document.createElement('input');
    commandInput.type = 'text';
    commandInput.placeholder = 'hist/point';
    commandInput.dataset.gpsCommandSequenceField = 'command';
    commandInput.value = trimSingleLine(entry.command).replace(/^\/gps\//, '');
    commandCell.appendChild(commandInput);
    row.appendChild(commandCell);

    const valueCell = document.createElement('td');
    const valueInput = document.createElement('input');
    valueInput.type = 'text';
    valueInput.placeholder = '1 keV 0.2';
    valueInput.dataset.gpsCommandSequenceField = 'value';
    valueInput.value = trimSingleLine(entry.value);
    valueCell.appendChild(valueInput);
    row.appendChild(valueCell);

    const actionCell = document.createElement('td');
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'gps-advanced-small-button';
    removeButton.textContent = 'Remove';
    removeButton.addEventListener('click', () => row.remove());
    actionCell.appendChild(removeButton);
    row.appendChild(actionCell);

    tbody.appendChild(row);
}

function appendCommandSequenceCard(parent, sequence = []) {
    const card = document.createElement('section');
    card.className = 'gps-advanced-card';
    const title = document.createElement('h5');
    title.textContent = 'Ordered Raw /gps Commands';
    card.appendChild(title);

    const note = document.createElement('p');
    note.className = 'gps-advanced-note';
    note.textContent = 'Use this escape hatch for repeated or order-sensitive GPS commands not covered above. Enter commands without the /gps/ prefix.';
    card.appendChild(note);

    const table = document.createElement('table');
    table.className = 'gps-advanced-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>On</th>
                <th>Command</th>
                <th>Value</th>
                <th></th>
            </tr>
        </thead>
    `;
    const tbody = document.createElement('tbody');
    table.appendChild(tbody);
    for (const entry of sequence || []) {
        appendCommandSequenceRow(tbody, entry);
    }
    card.appendChild(table);

    const actions = document.createElement('div');
    actions.className = 'gps-advanced-row-actions';
    const addButton = document.createElement('button');
    addButton.type = 'button';
    addButton.className = 'gps-advanced-small-button';
    addButton.textContent = 'Add Command';
    addButton.addEventListener('click', () => appendCommandSequenceRow(tbody, { enabled: true }));
    actions.appendChild(addButton);
    card.appendChild(actions);
    parent.appendChild(card);
}

function renderAdvancedGpsUI(sourceData = null) {
    if (!advancedGpsPanel || !advancedGpsControls || !advancedGpsEnabledInput) return;

    const advancedGps = sourceData?.advanced_gps || {};
    const commandSequence = Array.isArray(sourceData?.gps_command_sequence) ? sourceData.gps_command_sequence : [];
    const hasAdvanced = hasAdvancedGpsContent(advancedGps, commandSequence);

    advancedGpsPanel.open = hasAdvanced;
    advancedGpsEnabledInput.checked = hasAdvanced;
    advancedGpsControls.innerHTML = '';

    appendTransformAndSourceListCard(advancedGpsControls, advancedGps);
    for (const sectionDef of ADVANCED_GPS_SECTION_DEFINITIONS) {
        appendAdvancedSectionCard(advancedGpsControls, sectionDef, advancedGps);
    }
    appendHistogramsCard(advancedGpsControls, advancedGps.histograms || []);
    appendCommandSequenceCard(advancedGpsControls, commandSequence);
    toggleAdvancedGpsControls();
}

export function show(sourceData = null, availableVolumes = []) {
    currentAvailableVolumes = availableVolumes || [];

    // Populate Linked Volume Datalist
    const dataList = document.getElementById('gpsLinkedVolumeList');
    dataList.innerHTML = ''; // Clear previous options

    // With datalist and search, we can probably afford to add all of them,
    // as browsers optimize datalists better than selects for rendering.
    // We populate the options with names.
    currentAvailableVolumes.forEach(vol => {
        const option = document.createElement('option');
        option.value = vol.name; // User learns/types by Name
        // We can't consistently rely on 'label' or innerText being shown across browsers
        // But we store the ID in a way we can lookup later? No, we have the map.
        dataList.appendChild(option);
    });

    if (sourceData) { // EDIT MODE
        isEditMode = true;
        editingSourceId = sourceData.id;
        currentSourceCommands = { ...(sourceData.gps_commands || {}) };
        titleElement.textContent = `Edit Particle Source: ${sourceData.name} `;
        nameInput.value = sourceData.name;
        nameInput.disabled = false;
        confirmButton.textContent = "Update Source";

        const commands = sourceData.gps_commands || {};
        particleSelect.value = commands['particle'] || 'e+';

        energyContainer.innerHTML = '';
        energyContainer.appendChild(ExpressionInput.create('gps_energy', 'Energy (keV)', commands['energy'] || '0'));

        let activityVal = '1.0';
        if (sourceData.activity !== undefined && sourceData.activity !== null) {
            activityVal = sourceData.activity;
        }
        energyContainer.appendChild(ExpressionInput.create('gps_activity', 'Activity (Bq)', activityVal));

        const shape = commands['pos/type'] || 'Point';
        shapeSelect.value = shape;

        // Restore Linked State
        linkedCheckbox.checked = !!sourceData.volume_link_id;
        if (sourceData.volume_link_id) {
            // Find the volume helper to get the Name
            const vol = currentAvailableVolumes.find(v => v.id === sourceData.volume_link_id);
            if (vol) {
                linkedSelect.value = vol.name;
            } else {
                // Fallback if the volume was deleted?
                linkedSelect.value = "";
            }
        } else {
            linkedSelect.value = "";
        }

        sourceTypeSelect.value = sourceData.type || 'gps';
        const ion = sourceData.ion_params || {};
        if (ionZInput) ionZInput.value = ion.Z ?? 6;
        if (ionAInput) ionAInput.value = ion.A ?? 14;
        if (ionQInput) ionQInput.value = ion.Q ?? 4;
        if (ionEInput) ionEInput.value = ion.excitation_energy_keV ?? 0;
        if (ionLevelInput) ionLevelInput.value = ion.excitation_level ?? ion.level ?? sourceData.advanced_gps?.ion?.excitation_level ?? '';

        renderShapeParamsUI(shape, commands, sourceData.position, sourceData.rotation, sourceData.confine_to_pv);

    } else { // CREATE MODE
        isEditMode = false;
        editingSourceId = null;
        currentSourceCommands = {};
        titleElement.textContent = "Create New Particle Source";
        nameInput.value = '';
        nameInput.disabled = false;
        confirmButton.textContent = "Create Source";

        particleSelect.value = 'e+';
        energyContainer.innerHTML = '';
        energyContainer.appendChild(ExpressionInput.create('gps_energy', 'Energy (keV)', '0'));
        energyContainer.appendChild(ExpressionInput.create('gps_activity', 'Activity (Bq)', '1000.0'));

        shapeSelect.value = 'Point';
        linkedCheckbox.checked = false;
        linkedSelect.value = "";

        sourceTypeSelect.value = 'gps';
        if (ionZInput) ionZInput.value = 6;
        if (ionAInput) ionAInput.value = 14;
        if (ionQInput) ionQInput.value = 4;
        if (ionEInput) ionEInput.value = 0;
        if (ionLevelInput) ionLevelInput.value = '';

        renderShapeParamsUI('Point', {}, { x: '0', y: '0', z: '0' }, { x: '0', y: '0', z: '0' }, null);
    }
    renderAdvancedGpsUI(sourceData);
    toggleLinkedMode(); // Apply Linked UI state
    toggleSourceType();
    modalElement.style.display = 'block';
}


function hide() {
    modalElement.style.display = 'none';
}

function toggleLinkedMode() {
    const isLinked = linkedCheckbox.checked;
    linkedSelect.style.display = isLinked ? 'block' : 'none';

    // Controls to disable/hide
    if (isLinked) {
        // Disable Manual Params
        shapeSelect.disabled = true;
        shapeParamsContainer.style.opacity = '0.3';
        shapeParamsContainer.style.pointerEvents = 'none';
    } else {
        // Enable Manual Params
        shapeSelect.disabled = false;
        shapeParamsContainer.style.opacity = '1.0';
        shapeParamsContainer.style.pointerEvents = 'auto';
    }
}

function toggleSourceType() {
    const isIon = sourceTypeSelect.value === 'ion';
    if (gpsParticleControls) {
        gpsParticleControls.style.display = isIon ? 'none' : 'block';
    }
    if (ionControls) {
        ionControls.style.display = isIon ? 'block' : 'none';
    }
}

function renderShapeParamsUI(shapeType = null, commands = {}, position = {}, rotation = {}, confineToPv = null) {
    const shape = shapeType || shapeSelect.value;
    shapeParamsContainer.innerHTML = ''; // Clear previous params

    // --- Position Editor ---
    const posGroup = document.createElement('div');
    posGroup.className = 'transform-group';
    posGroup.innerHTML = `<span>Position (mm)</span>`;
    shapeParamsContainer.appendChild(posGroup);
    ['x', 'y', 'z'].forEach(axis => {
        posGroup.appendChild(ExpressionInput.create(
            `gps_pos_${axis}`, axis.toUpperCase(), position[axis] || '0'
        ));
    });

    // --- Shape Parameters ---
    if (shape === 'Volume' || shape === 'Surface') {
        const subShapeContainer = document.createElement('div');
        subShapeContainer.className = 'property_item';
        subShapeContainer.innerHTML = `
        <label for="gpsVolumeShape">Shape:</label>
        <select id="gpsVolumeShape">
            <option value="Sphere">Sphere</option>
            <option value="Cylinder">Cylinder</option>
            <option value="Box">Box</option>
        </select>`;
        shapeParamsContainer.appendChild(subShapeContainer);

        const subShapeSelect = subShapeContainer.querySelector('#gpsVolumeShape');
        subShapeSelect.value = commands['pos/shape'] || 'Sphere';

        const shapeParamsDiv = document.createElement('div');
        shapeParamsDiv.id = 'gps-subshape-params';
        shapeParamsContainer.appendChild(shapeParamsDiv);

        const renderSubParams = () => {
            const subShape = subShapeSelect.value;
            shapeParamsDiv.innerHTML = '';
            const cleanVal = (val, def) => val ? val.replace(' mm', '') : def;

            if (subShape === 'Sphere') {
                shapeParamsDiv.appendChild(ExpressionInput.create('gps_radius', 'Radius (mm)', cleanVal(commands['pos/radius'], '10')));
            } else if (subShape === 'Cylinder') {
                shapeParamsDiv.appendChild(ExpressionInput.create('gps_radius', 'Radius (mm)', cleanVal(commands['pos/radius'], '10')));
                shapeParamsDiv.appendChild(ExpressionInput.create('gps_halfz', 'Half-Z (mm)', cleanVal(commands['pos/halfz'], '10')));
            } else if (subShape === 'Box') {
                shapeParamsDiv.appendChild(ExpressionInput.create('gps_halfx', 'Half-X (mm)', cleanVal(commands['pos/halfx'], '10')));
                shapeParamsDiv.appendChild(ExpressionInput.create('gps_halfy', 'Half-Y (mm)', cleanVal(commands['pos/halfy'], '10')));
                shapeParamsDiv.appendChild(ExpressionInput.create('gps_halfz', 'Half-Z (mm)', cleanVal(commands['pos/halfz'], '10')));
            }
        };

        subShapeSelect.addEventListener('change', renderSubParams);
        renderSubParams();
    }

    // --- Angular Distribution ---
    shapeParamsContainer.appendChild(document.createElement('hr'));
    const angGroup = document.createElement('div');
    angGroup.className = 'property_item';
    angGroup.innerHTML = `
        <label for="gpsAngType">Distribution:</label>
        <select id="gpsAngType">
            <option value="iso">Isotropic (Random)</option>
            <option value="beam1d">Beam (Directed)</option>
        </select>
    `;
    shapeParamsContainer.appendChild(angGroup);
    const angTypeSelect = angGroup.querySelector('#gpsAngType');
    angTypeSelect.value = normalizeGpsAngularType(commands['ang/type'], 'iso');

    // --- Beam Direction ---
    const directionGroup = document.createElement('div');
    directionGroup.className = 'transform-group';
    directionGroup.innerHTML = `<span>Beam Direction (unit vector)</span>`;
    shapeParamsContainer.appendChild(directionGroup);
    const directionVector = parseGpsDirectionVector(commands['ang/dir1'], { x: '0', y: '0', z: '1' });
    ['x', 'y', 'z'].forEach(axis => {
        directionGroup.appendChild(ExpressionInput.create(
            `gps_dir_${axis}`, axis.toUpperCase(), directionVector[axis] || '0'
        ));
    });

    // --- Rotation ---
    const rotGroup = document.createElement('div');
    rotGroup.className = 'transform-group';
    rotGroup.innerHTML = `<span>Shape Orientation (rad)</span>`;
    shapeParamsContainer.appendChild(rotGroup);
    ['x', 'y', 'z'].forEach(axis => {
        rotGroup.appendChild(ExpressionInput.create(
            `gps_rot_${axis}`, axis.toUpperCase(), rotation[axis] || '0'
        ));
    });

    const syncAngularUi = () => {
        const isIso = isIsotropicGpsAngularType(angTypeSelect.value);
        const isPointShape = isPointSourceShape(shape);
        directionGroup.style.display = isIso ? 'none' : 'block';
        rotGroup.style.display = isPointShape ? 'none' : 'block';
    };
    angTypeSelect.addEventListener('change', syncAngularUi);
    syncAngularUi();
}

function collectAdvancedSection(sectionId) {
    const section = {};
    if (!advancedGpsControls) return section;
    const inputs = advancedGpsControls.querySelectorAll(`[data-gps-advanced-section="${sectionId}"]`);
    inputs.forEach((input) => {
        const key = input.dataset.gpsAdvancedKey;
        if (!key) return;
        section[key] = input.value;
    });
    return section;
}

function collectAdvancedHistograms() {
    if (!advancedGpsControls) return [];
    return Array.from(advancedGpsControls.querySelectorAll('[data-gps-advanced-histogram-row="true"]'))
        .map((row) => {
            const entry = {};
            row.querySelectorAll('[data-gps-advanced-histogram-field]').forEach((input) => {
                const field = input.dataset.gpsAdvancedHistogramField;
                if (!field) return;
                if (input.type === 'checkbox') {
                    entry[field] = input.checked;
                } else {
                    entry[field] = input.value;
                }
            });
            return entry;
        });
}

function collectCommandSequence() {
    if (!advancedGpsControls) return [];
    return Array.from(advancedGpsControls.querySelectorAll('[data-gps-command-sequence-row="true"]'))
        .map((row) => {
            const entry = {};
            row.querySelectorAll('[data-gps-command-sequence-field]').forEach((input) => {
                const field = input.dataset.gpsCommandSequenceField;
                if (!field) return;
                if (input.type === 'checkbox') {
                    entry[field] = input.checked;
                } else {
                    entry[field] = input.value;
                }
            });
            return entry;
        });
}

function collectAdvancedGpsPayload() {
    if (!advancedGpsEnabledInput?.checked) {
        return {
            advanced_gps: {},
            gps_command_sequence: [],
        };
    }

    const rawState = {
        airpet_transform_mode: document.getElementById('gpsAdvanced_airpet_transform_mode')?.value || 'airpet',
        source_list: collectAdvancedSection('source_list'),
        histograms: collectAdvancedHistograms(),
        gps_command_sequence: collectCommandSequence(),
    };
    for (const sectionDef of ADVANCED_GPS_SECTION_DEFINITIONS) {
        rawState[sectionDef.id] = collectAdvancedSection(sectionDef.id);
    }
    return buildAdvancedGpsPayloadFromSections(rawState);
}


function handleConfirm() {
    const name = nameInput.value.trim();
    if (!name && !isEditMode) {
        alert("Please provide a name for the source.");
        return;
    }

    const sourceType = sourceTypeSelect ? sourceTypeSelect.value : 'gps';

    // Collect all GPS commands into a dictionary
    const gpsCommands = {};
    if (sourceType === 'ion') {
        gpsCommands['particle'] = 'ion';
    } else {
        gpsCommands['particle'] = particleSelect.value;
    }
    // For e+, the energy spectrum is usually handled by the physics list,
    // so we set a monoenergetic energy of 0 keV by default unless specified otherwise.
    const energyValue = document.getElementById('gps_energy').value.trim();
    if (particleSelect.value === 'e+' && energyValue === '') {
        gpsCommands['energy'] = '0';
    } else {
        gpsCommands['energy'] = `${energyValue} `;
    }

    gpsCommands['ene/type'] = 'Mono'; // For simplicity, always Mono for now

    const shape = shapeSelect.value;
    gpsCommands['pos/type'] = shape;

    if (shape === 'Volume' || shape === 'Surface') {
        const subShape = document.getElementById('gpsVolumeShape').value;
        gpsCommands['pos/shape'] = subShape;
        if (subShape === 'Sphere') {
            gpsCommands['pos/radius'] = document.getElementById('gps_radius').value + ' mm';
        } else if (subShape === 'Cylinder') {
            gpsCommands['pos/radius'] = document.getElementById('gps_radius').value + ' mm';
            gpsCommands['pos/halfz'] = document.getElementById('gps_halfz').value + ' mm';
        } else if (subShape === 'Box') {
            gpsCommands['pos/halfx'] = document.getElementById('gps_halfx').value + ' mm';
            gpsCommands['pos/halfy'] = document.getElementById('gps_halfy').value + ' mm';
            gpsCommands['pos/halfz'] = document.getElementById('gps_halfz').value + ' mm';
        }
    }

    // Also collect the position
    const position = {
        x: document.getElementById('gps_pos_x').value,
        y: document.getElementById('gps_pos_y').value,
        z: document.getElementById('gps_pos_z').value
    };

    // Collect angular commands
    const angType = normalizeGpsAngularType(document.getElementById('gpsAngType').value, 'iso');
    gpsCommands['ang/type'] = angType;
    if (angType === 'beam1d') {
        gpsCommands['ang/dir1'] = [
            document.getElementById('gps_dir_x').value.trim() || '0',
            document.getElementById('gps_dir_y').value.trim() || '0',
            document.getElementById('gps_dir_z').value.trim() || '1',
        ].join(' ');
    }

    // Collect rotation
    const rotation = isPointSourceShape(shape)
        ? { x: '0', y: '0', z: '0' }
        : {
            x: document.getElementById('gps_rot_x').value,
            y: document.getElementById('gps_rot_y').value,
            z: document.getElementById('gps_rot_z').value
        };

    // Collect Confinement
    let confineToPv = "";
    let volumeLinkId = null;

    if (linkedCheckbox.checked) {
        // Linked Mode: The input value is the Name. We need to look up the ID.
        confineToPv = linkedSelect.value; // The backend uses the name for `confine_to_pv`

        // Find the corresponding ID for tracking
        const vol = currentAvailableVolumes.find(v => v.name === confineToPv);
        if (vol) {
            volumeLinkId = vol.id;
        } else {
            // Set link to null if not found.
            volumeLinkId = null;
        }
    } else {
        // Free Mode: No confinement allows
        confineToPv = null;
    }

    let ionParams = null;
    if (sourceType === 'ion') {
        const ionLevel = ionLevelInput ? ionLevelInput.value.trim() : '';
        ionParams = {
            Z: parseInt(ionZInput ? ionZInput.value : 6, 10) || 6,
            A: parseInt(ionAInput ? ionAInput.value : 14, 10) || 14,
            Q: parseInt(ionQInput ? ionQInput.value : 4, 10) || 4,
            excitation_energy_keV: parseFloat(ionEInput ? ionEInput.value : 0) || 0.0
        };
        if (ionLevel !== '') {
            ionParams.excitation_level = parseInt(ionLevel, 10) || 0;
        }
    }

    const advancedPayload = collectAdvancedGpsPayload();

    onConfirmCallback({
        isEdit: isEditMode,
        id: isEditMode ? editingSourceId : name,
        name: name,
        source_type: sourceType,
        gps_commands: gpsCommands,
        ion_params: ionParams,
        gps_command_sequence: advancedPayload.gps_command_sequence,
        advanced_gps: advancedPayload.advanced_gps,
        position: position,
        rotation: rotation,
        activity: document.getElementById('gps_activity').value,
        confine_to_pv: confineToPv,
        volume_link_id: volumeLinkId
    });

    hide();
}
