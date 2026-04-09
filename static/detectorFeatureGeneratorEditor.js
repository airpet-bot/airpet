import { buildDetectorFeatureGeneratorEditorModel } from './detectorFeatureGeneratorsUi.js';

const RECTANGULAR_DRILLED_HOLE_ARRAY = 'rectangular_drilled_hole_array';
const CIRCULAR_DRILLED_HOLE_ARRAY = 'circular_drilled_hole_array';

let modalElement;
let titleElement;
let confirmButton;
let cancelButton;
let nameInput;
let generatorTypeSelect;
let targetSolidSelect;
let targetSummary;
let targetLockNotice;
let rectangularFields;
let countXInput;
let countYInput;
let pitchXInput;
let pitchYInput;
let circularFields;
let circularCountInput;
let circularRadiusInput;
let circularOrientationInput;
let offsetXInput;
let offsetYInput;
let holeDiameterInput;
let holeDepthInput;

let onConfirmCallback = null;
let currentGeneratorEntry = null;
let currentTargetOptions = [];

export function initDetectorFeatureGeneratorEditor(callbacks) {
    onConfirmCallback = callbacks.onConfirm;

    modalElement = document.getElementById('detectorFeatureGeneratorModal');
    titleElement = document.getElementById('detectorFeatureGeneratorTitle');
    confirmButton = document.getElementById('detectorFeatureGeneratorConfirm');
    cancelButton = document.getElementById('detectorFeatureGeneratorCancel');
    nameInput = document.getElementById('detectorFeatureGeneratorName');
    generatorTypeSelect = document.getElementById('detectorFeatureGeneratorType');
    targetSolidSelect = document.getElementById('detectorFeatureGeneratorTargetSolid');
    targetSummary = document.getElementById('detectorFeatureGeneratorTargetSummary');
    targetLockNotice = document.getElementById('detectorFeatureGeneratorTargetLockNotice');
    rectangularFields = document.getElementById('detectorFeatureGeneratorRectangularFields');
    countXInput = document.getElementById('detectorFeatureGeneratorCountX');
    countYInput = document.getElementById('detectorFeatureGeneratorCountY');
    pitchXInput = document.getElementById('detectorFeatureGeneratorPitchX');
    pitchYInput = document.getElementById('detectorFeatureGeneratorPitchY');
    circularFields = document.getElementById('detectorFeatureGeneratorCircularFields');
    circularCountInput = document.getElementById('detectorFeatureGeneratorCircularCount');
    circularRadiusInput = document.getElementById('detectorFeatureGeneratorCircularRadius');
    circularOrientationInput = document.getElementById('detectorFeatureGeneratorCircularOrientation');
    offsetXInput = document.getElementById('detectorFeatureGeneratorOffsetX');
    offsetYInput = document.getElementById('detectorFeatureGeneratorOffsetY');
    holeDiameterInput = document.getElementById('detectorFeatureGeneratorHoleDiameter');
    holeDepthInput = document.getElementById('detectorFeatureGeneratorHoleDepth');

    cancelButton.addEventListener('click', hide);
    confirmButton.addEventListener('click', handleConfirm);
    generatorTypeSelect.addEventListener('change', updatePatternSectionVisibility);
    targetSolidSelect.addEventListener('change', updateTargetSummary);
}

export function show(generatorEntry, projectState, selectedItems = []) {
    const model = buildDetectorFeatureGeneratorEditorModel(projectState, generatorEntry, selectedItems);
    if (model.targetOptions.length === 0) {
        alert('Create a box solid before adding a patterned-hole generator.');
        return;
    }

    currentGeneratorEntry = generatorEntry && typeof generatorEntry === 'object' ? generatorEntry : null;
    currentTargetOptions = model.targetOptions;

    titleElement.textContent = model.title;
    confirmButton.textContent = model.confirmLabel;
    nameInput.value = model.name;
    generatorTypeSelect.value = model.generatorType;
    countXInput.value = String(model.countX);
    countYInput.value = String(model.countY);
    pitchXInput.value = String(model.pitchX);
    pitchYInput.value = String(model.pitchY);
    circularCountInput.value = String(model.circularCount);
    circularRadiusInput.value = String(model.circularRadius);
    circularOrientationInput.value = String(model.circularOrientation);
    offsetXInput.value = String(model.offsetX);
    offsetYInput.value = String(model.offsetY);
    holeDiameterInput.value = String(model.holeDiameter);
    holeDepthInput.value = String(model.holeDepth);

    populateTargetOptions(model.targetOptions, model.selectedTargetName);
    targetSolidSelect.disabled = model.targetLocked;
    generatorTypeSelect.disabled = model.typeLocked;
    if (targetLockNotice) {
        targetLockNotice.hidden = !(model.targetLocked || model.typeLocked);
    }

    updatePatternSectionVisibility();
    updateTargetSummary();
    modalElement.style.display = 'block';
}

function hide() {
    modalElement.style.display = 'none';
    currentGeneratorEntry = null;
    currentTargetOptions = [];
    targetSolidSelect.disabled = false;
    generatorTypeSelect.disabled = false;
    if (targetLockNotice) {
        targetLockNotice.hidden = true;
    }
    updatePatternSectionVisibility();
}

function populateTargetOptions(options, selectedName) {
    targetSolidSelect.innerHTML = '';

    options.forEach((optionData) => {
        const option = document.createElement('option');
        option.value = optionData.name;
        option.textContent = optionData.name;
        option.dataset.solidId = optionData.id || '';
        targetSolidSelect.appendChild(option);
    });

    if (selectedName) {
        targetSolidSelect.value = selectedName;
    }
}

function updateTargetSummary() {
    const selectedName = targetSolidSelect.value;
    const optionData = currentTargetOptions.find((option) => option.name === selectedName);
    if (!optionData) {
        targetSummary.textContent = 'Select a box solid to target.';
        targetSummary.title = '';
        return;
    }

    const names = optionData.logicalVolumeNames || [];
    if (names.length === 0) {
        targetSummary.textContent = 'Matching logical volumes: none yet. The saved spec will still target this box solid.';
        targetSummary.title = '';
        return;
    }

    const preview = names.slice(0, 3).join(', ');
    const extraCount = names.length > 3 ? `, +${names.length - 3} more` : '';
    targetSummary.textContent = `Matching logical volumes: ${preview}${extraCount}.`;
    targetSummary.title = names.join('\n');
}

function updatePatternSectionVisibility() {
    const generatorType = String(generatorTypeSelect?.value || RECTANGULAR_DRILLED_HOLE_ARRAY).trim();
    if (rectangularFields) {
        rectangularFields.hidden = generatorType !== RECTANGULAR_DRILLED_HOLE_ARRAY;
    }
    if (circularFields) {
        circularFields.hidden = generatorType !== CIRCULAR_DRILLED_HOLE_ARRAY;
    }
}

function readPositiveInteger(input, labelText) {
    const value = Number.parseInt(input.value, 10);
    if (!Number.isFinite(value) || value <= 0) {
        throw new Error(`${labelText} must be a positive integer.`);
    }
    return value;
}

function readPositiveNumber(input, labelText) {
    const value = Number(input.value);
    if (!Number.isFinite(value) || value <= 0) {
        throw new Error(`${labelText} must be greater than 0.`);
    }
    return value;
}

function readFiniteNumber(input, labelText) {
    const value = Number(input.value);
    if (!Number.isFinite(value)) {
        throw new Error(`${labelText} must be a finite number.`);
    }
    return value;
}

function buildPatternPayload(generatorType) {
    const originOffset = {
        x: readFiniteNumber(offsetXInput, 'Offset X'),
        y: readFiniteNumber(offsetYInput, 'Offset Y'),
    };

    if (generatorType === CIRCULAR_DRILLED_HOLE_ARRAY) {
        return {
            count: readPositiveInteger(circularCountInput, 'Circular count'),
            radius_mm: readPositiveNumber(circularRadiusInput, 'Circle radius'),
            orientation_deg: readFiniteNumber(circularOrientationInput, 'Orientation'),
            origin_offset_mm: originOffset,
            anchor: 'target_center',
        };
    }

    return {
        count_x: readPositiveInteger(countXInput, 'Count X'),
        count_y: readPositiveInteger(countYInput, 'Count Y'),
        pitch_mm: {
            x: readPositiveNumber(pitchXInput, 'Pitch X'),
            y: readPositiveNumber(pitchYInput, 'Pitch Y'),
        },
        origin_offset_mm: originOffset,
        anchor: 'target_center',
    };
}

function handleConfirm() {
    if (!onConfirmCallback) {
        return;
    }

    try {
        const generatorName = String(nameInput.value || '').trim();
        if (!generatorName) {
            throw new Error('Please provide a generator name.');
        }

        const generatorType = String(generatorTypeSelect.value || RECTANGULAR_DRILLED_HOLE_ARRAY).trim();
        const targetSolidName = String(targetSolidSelect.value || '').trim();
        const selectedOption = targetSolidSelect.selectedOptions?.[0];
        const targetSolidId = String(selectedOption?.dataset?.solidId || '').trim();
        if (!targetSolidName) {
            throw new Error('Please choose a target solid.');
        }

        onConfirmCallback({
            generator_id: currentGeneratorEntry?.generator_id,
            generator_type: generatorType,
            name: generatorName,
            target: {
                solid_ref: {
                    id: targetSolidId,
                    name: targetSolidName,
                },
                logical_volume_refs: [],
            },
            pattern: buildPatternPayload(generatorType),
            hole: {
                shape: 'cylindrical',
                diameter_mm: readPositiveNumber(holeDiameterInput, 'Hole diameter'),
                depth_mm: readPositiveNumber(holeDepthInput, 'Hole depth'),
                axis: 'z',
                drill_from: 'positive_z_face',
            },
            realize_now: true,
        });
        hide();
    } catch (error) {
        alert(error.message || error);
    }
}
