// static/main.js
import * as THREE from 'three';

import * as APIService from './apiService.js';
import * as AssemblyEditor from './assemblyEditor.js';
import * as BorderSurfaceEditor from './borderSurfaceEditor.js';
import * as DefineEditor from './defineEditor.js';
import * as GpsEditor from './gpsEditor.js';
import * as InteractionManager from './interactionManager.js';
import * as IsotopeEditor from './isotopeEditor.js';
import * as LVEditor from './logicalVolumeEditor.js';
import * as ElementEditor from './elementEditor.js';
import * as MaterialEditor from './materialEditor.js';
import * as OpticalSurfaceEditor from './opticalSurfaceEditor.js';
import * as PVEditor from './physicalVolumeEditor.js';
import * as DetectorFeatureGeneratorEditor from './detectorFeatureGeneratorEditor.js';
import * as RingArrayEditor from './ringArrayEditor.js';
import * as SceneManager from './sceneManager.js';
import * as SkinSurfaceEditor from './skinSurfaceEditor.js';
import * as SolidEditor from './solidEditor.js';
import { buildCadImportBatchContext } from './cadImportUi.js';
import * as StepImportEditor from './stepImportEditor.js';
import * as ParameterRegistryEditor from './parameterRegistryEditor.js';
import * as ParamStudyEditor from './paramStudyEditor.js';
import {
    LOCAL_UNIFORM_ELECTRIC_FIELD_OBJECT_ID,
    LOCAL_UNIFORM_ELECTRIC_FIELD_OBJECT_TYPE,
    LOCAL_UNIFORM_MAGNETIC_FIELD_OBJECT_ID,
    LOCAL_UNIFORM_MAGNETIC_FIELD_OBJECT_TYPE,
    setTargetVolumeMembership,
} from './environmentFieldUi.js';
import {
    buildHistoryDeleteConfirmationMessage,
    normalizeHistoryDeleteSelection,
} from './historyDeleteFlow.js';
import * as UIManager from './uiManager.js';
import * as AIAssistant from './aiAssistant.js';
import { mergeProjectStateWithExclusions } from './projectStateMerge.js';
import {
    buildResolvedSimulationOptions,
    buildSimulationOptionOverrides,
} from './scoringUi.js';
import {
    getNormalizedGpsDirectionVector,
    isDirectedGpsAngularType,
} from './gpsAngularMode.js';

// --- Global Application State (Keep this minimal) ---
const AppState = {
    currentProjectState: null,    // Full state dict from backend (defines, materials, solids, LVs, world_ref)
    currentProjectScene: null,    // Full scene dict from backend (THREE.js objects to be rendered)
    currentProjectName: "untitled",
    activeSourceIds: [],
    currentSimJobId: null,
    simStatusPoller: null,
    selectedHierarchyItems: [],   // array of { type, id, name, data (raw from projectState) }
    selectedThreeObjects: [],     // Managed by SceneManager, but AppState might need to know for coordination
    simConsoleLineCount: 0,
    lastSimVersionId: null,
    lastSimJobId: null,
    currentReconShape: null,
    simStatusPoller: null,
    lorStatusPoller: null,

    selectedPVContext: {
        pvId: null,
        positionDefineName: null,
        rotationDefineName: null,
    },

    simOptions: {
        save_tracks_range: "0-99", // Default to saving the first 100 tracks
        physics_list: 'FTFP_BERT',
    },
        {
            includeInField: localFieldAssignments.include_in_local_electric_field,
            objectType: LOCAL_UNIFORM_ELECTRIC_FIELD_OBJECT_TYPE,
            objectId: LOCAL_UNIFORM_ELECTRIC_FIELD_OBJECT_ID,
            stateKey: 'local_uniform_electric_field',
        },
    ];

    let nextResult = result;

    for (const update of updates) {
        const currentTargets = nextResult.project_state?.environment?.[update.stateKey]?.target_volume_names || [];
        const nextTargets = setTargetVolumeMembership(currentTargets, lvName, update.includeInField);
        if (areStringArraysEqual(currentTargets, nextTargets)) {
            continue;
        }

        nextResult = await APIService.updateProperty(
            update.objectType,
            update.objectId,
            'target_volume_names',
            nextTargets
        );
    }

    return nextResult;
}

async function handleLVEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    const previousProjectState = AppState.currentProjectState;
    let result = null;
    let selectionForSync = selectionContext;
    if (data.isEdit) {
        UIManager.showLoading("Updating Logical Volume...");
        try {
            result = await APIService.updateLogicalVolume(data.id, data.solid_ref, data.material_ref, data.vis_attributes, data.is_sensitive, data.content_type, data.content);
            result = await applyLocalFieldMembershipChanges(result, data.id, data.local_field_assignments);
            syncUIWithState(result, selectionForSync);
        } catch (error) {
            if (result) {
                syncUIWithState(result, selectionForSync);
            }
            UIManager.showError("Error updating LV: " + (error.message || error));
        } finally {
            UIManager.hideLoading();
        }
    } else {
        UIManager.showLoading("Creating Logical Volume...");
        try {
            result = await APIService.addLogicalVolume(data.name, data.solid_ref, data.material_ref, data.vis_attributes, data.is_sensitive, data.content_type, data.content);
            const createdLvName = resolveCreatedLogicalVolumeName(data.name, previousProjectState, result.project_state);
            selectionForSync = [{
                type: 'logical_volume',
                id: createdLvName,
                name: createdLvName,
                data: result.project_state.logical_volumes[createdLvName],
            }];
            result = await applyLocalFieldMembershipChanges(result, createdLvName, data.local_field_assignments);
            selectionForSync[0].data = result.project_state.logical_volumes[createdLvName];
            syncUIWithState(result, selectionForSync);
        } catch (error) {
            if (result) {
                syncUIWithState(result, selectionForSync);
            }
            UIManager.showError("Error creating LV: " + (error.message || error));
        }
        finally { UIManager.hideLoading(); }
    }
}

function handleAddPV() {
    let parentContext = UIManager.getSelectedParentContext();

    // If nothing is selected, default to the World volume
    if (!parentContext) {
        if (AppState.currentProjectState && AppState.currentProjectState.world_volume_ref) {
            parentContext = { name: AppState.currentProjectState.world_volume_ref };
            console.log("No parent selected, defaulting to World.");
        } else {
            UIManager.showError("No world volume found to place object into.");
            return;
        }
    }

    PVEditor.show(null, null, AppState.currentProjectState, parentContext);
}

function handleEditPV(pvData, lvData) {
    PVEditor.show(pvData, lvData, AppState.currentProjectState);
}

async function handlePVEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    if (data.isEdit) {
        UIManager.showLoading("Updating Physical Volume...");
        try {
            const result = await APIService.updatePhysicalVolume(data.id, data.name, data.position, data.rotation, data.scale);
            syncUIWithState(result, selectionContext);
        } catch (error) { UIManager.showError("Error updating PV: " + (error.message || error)); }
        finally { UIManager.hideLoading(); }
    } else {
        UIManager.showLoading("Placing Physical Volume...");
        try {
            const result = await APIService.addPhysicalVolume(data.parent_lv_name, data.name, data.volume_ref, data.position, data.rotation, data.scale);

            // After placement, we want the PARENT LV to remain selected
            syncUIWithState(result, [{ type: 'logical_volume', id: data.parent_lv_name, name: data.parent_lv_name }]);
        } catch (error) { UIManager.showError("Error placing PV: " + (error.message || error)); }
        finally { UIManager.hideLoading(); }
    }
}

function handleAddRingArray() {
    RingArrayEditor.show(AppState.currentProjectState);
}

async function handleCreateRingArray(params) {
    UIManager.showLoading("Creating detector ring...");
    try {
        const result = await APIService.createDetectorRing(params);
        syncUIWithState(result); // This will update everything
    } catch (error) {
        UIManager.showError("Failed to create ring array: " + error.message);
    } finally {
        UIManager.hideLoading();
    }
}

function handleAddDetectorFeatureGenerator() {
    DetectorFeatureGeneratorEditor.show(
        null,
        AppState.currentProjectState,
        AppState.selectedHierarchyItems,
    );
}

function handleEditDetectorFeatureGenerator(generatorEntry) {
    DetectorFeatureGeneratorEditor.show(
        generatorEntry,
        AppState.currentProjectState,
        AppState.selectedHierarchyItems,
    );
}

async function handleSaveDetectorFeatureGenerator(payload) {
    UIManager.showLoading('Saving detector generator...');
    try {
        const result = await APIService.upsertDetectorFeatureGenerator(payload);
        syncUIWithState(result);
    } catch (error) {
        UIManager.showError('Failed to save detector generator: ' + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

async function handleRealizeDetectorFeatureGenerator(generatorEntry) {
    const generatorId = String(generatorEntry?.generator_id || '').trim();
    if (!generatorId) {
        UIManager.showError('Could not determine which detector feature generator to regenerate.');
        return;
    }

    UIManager.showLoading('Regenerating detector geometry...');
    try {
        const result = await APIService.realizeDetectorFeatureGenerator(generatorId);
        syncUIWithState(result);
    } catch (error) {
        UIManager.showError('Failed to regenerate detector geometry: ' + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

function handleAddDefine() {
    DefineEditor.show(null, AppState.currentProjectState);
}

function handleEditDefine(defineData) {
    DefineEditor.show(defineData, AppState.currentProjectState);
}

async function handleDefineEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    if (data.isEdit) {
        UIManager.showLoading("Updating Define...");
        try {
            const result = await APIService.updateDefine(data.id, data.raw_expression, data.unit, data.category);
            syncUIWithState(result, selectionContext);
        } catch (error) {
            UIManager.showError("Error updating define: " + (error.message || error));
        } finally { UIManager.hideLoading(); }
    } else {
        UIManager.showLoading("Creating Define...");
        try {
            const result = await APIService.addDefine(data.name, data.type, data.raw_expression, data.unit, data.category);

            const newDefineName = result.project_state.defines[data.name] ? data.name : Object.keys(result.project_state.defines).find(k => k.startsWith(data.name));
            syncUIWithState(result, [{ type: 'define', id: newDefineName, name: newDefineName }]);
        } catch (error) {
            UIManager.showError("Error creating define: " + (error.message || error));
        } finally { UIManager.hideLoading(); }
    }
}

function handleAddMaterial() {
    MaterialEditor.show(null, AppState.currentProjectState);
}
function handleEditMaterial(matData) {
    MaterialEditor.show(matData, AppState.currentProjectState);
}

async function handleMaterialEditorConfirm(data) {

    if (data.isEdit) {
        UIManager.showLoading("Updating Material...");
        try {
            const result = await APIService.updateMaterial(data.id, data.params);
            syncUIWithState(result);
        } catch (error) { /* ... */ }
        finally { UIManager.hideLoading(); }
    } else {
        UIManager.showLoading("Creating Material...");
        try {
            const result = await APIService.addMaterial(data.name, data.params);

            // After creating, set the selection to the newly created material
            syncUIWithState(result, [{ type: 'material', id: data.name, name: data.name }]);
        } catch (error) {
            UIManager.showError("Error creating material: " + (error.message || error));
        } finally {
            UIManager.hideLoading();
        }
    }
}

function handleAddIsotope() {
    IsotopeEditor.show(null);
}

function handleEditIsotope(isoData) {
    IsotopeEditor.show(isoData);
}

async function handleIsotopeEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    const apiCall = data.isEdit
        ? APIService.updateIsotope(data.id, data)
        : APIService.addIsotope(data.name, data);

    const loadingMessage = data.isEdit ? "Updating Isotope..." : "Creating Isotope...";
    UIManager.showLoading(loadingMessage);
    try {
        const result = await apiCall;

        // Find the final name in case the backend had to make it unique
        const newIsotopeName = Object.keys(result.project_state.isotopes).find(k => k.startsWith(data.name)) || data.name;

        const newSelection = [{
            type: 'isotope',
            id: newIsotopeName,
            name: newIsotopeName,
            data: result.project_state.isotopes[newIsotopeName]
        }];

        syncUIWithState(result, data.isEdit ? selectionContext : newSelection);
    } catch (error) {
        UIManager.showError("Error processing Isotope: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

function handlePVVisibilityToggle(pvId, isVisible, isRecursive = false) {
    // 1. Get the DOM element for the primary PV
    const pvElement = document.querySelector(`#structure_tree_root li[data-instance-id="${pvId}"]`);
    if (!pvElement) return;

    // 2. Toggle visibility for selected element
    SceneManager.setPVVisibility(pvId, isVisible);
    UIManager.setTreeItemVisibility(pvId, isVisible);

    // 3. Find all descendant PV IDs
    let descendantIds = UIManager.getDescendantPvIds(pvElement); // Use the new helper

    // 4. If recursive, toggle visibility of all descendants.
    const pvContext = findItemInScene(pvId);
    const isAssemblyContainer = pvContext.selData.is_assembly_container;
    const isProceduralContainer = pvContext.selData.is_procedural_container;
    if (isRecursive || isAssemblyContainer || isProceduralContainer) {
        descendantIds.forEach(id => {
            // Update the 3D scene
            SceneManager.setPVVisibility(id, isVisible);
            // Update the hierarchy UI (the eye icon and dimmed text)
            UIManager.setTreeItemVisibility(id, isVisible);
        });
    }
}

function handleHideSelected() {
    if (!document.getElementById('hideSelBtn')) return;
    // This now works for multi-select as well
    const selection = AppState.selectedHierarchyItems;
    if (selection.length > 0) {
        selection.forEach(item => {
            if (item.type === 'physical_volume') {
                handlePVVisibilityToggle(item.id, false, false);
            }
        });
    } else {
        UIManager.showNotification("Please select one or more Physical Volumes to hide.");
    }
}

function handleShowSelected() {
    if (!document.getElementById('showSelBtn')) return;
    // This now works for multi-select as well
    const selection = AppState.selectedHierarchyItems;
    if (selection.length > 0) {
        selection.forEach(item => {
            if (item.type === 'physical_volume') {
                handlePVVisibilityToggle(item.id, true, false);
            }
        });
    } else {
        UIManager.showNotification("Please select one or more Physical Volumes to show.");
    }
}

function handleHideAll() {
    if (!document.getElementById('hideAllBtn')) return;
    // 1. Tell the SceneManager to hide all 3D objects.
    SceneManager.setAllPVVisibility(false, AppState.currentProjectState);
    // 2. Tell the UIManager to update the visual state of all hierarchy items.
    UIManager.setAllTreeItemVisibility(false);
}

function handleShowAll() {
    if (!document.getElementById('showAllBtn')) return;
    // 1. Tell the SceneManager to show all 3D objects.
    SceneManager.setAllPVVisibility(true, AppState.currentProjectState);
    // 2. Tell the UIManager to update the visual state of all hierarchy items.
    UIManager.setAllTreeItemVisibility(true);
}

/**
 * Checks the AI service status and updates the UI accordingly.
 */
async function checkAndSetAiStatus() {
    // Disable the panel by default while checking
    UIManager.setAiPanelState('disabled', "Checking AI service connection...");
    console.log("Checking AI service status...");

    try {
        const status = await APIService.checkAiServiceStatus();
        if (status.success) {
            let localBackendDiagnostics = status.local_backend_diagnostics || {};

            try {
                const diagnosticsResponse = await APIService.getAiBackendDiagnostics(['llama_cpp', 'lm_studio']);
                if (diagnosticsResponse?.success && Array.isArray(diagnosticsResponse.diagnostics)) {
                    localBackendDiagnostics = diagnosticsResponse.diagnostics.reduce((acc, item) => {
                        if (item && typeof item === 'object' && item.backend_id) {
                            acc[item.backend_id] = item;
                        }
                        return acc;
                    }, {});
                }
            } catch (diagError) {
                console.warn("Failed to refresh local backend diagnostics, using ai_health_check payload:", diagError.message || diagError);
            }

            UIManager.populateAiModelSelector(status.models, localBackendDiagnostics);
            UIManager.setAiPanelState('idle', "Generate with AI");
            console.log("AI service is online.");
        } else {
            UIManager.setAiPanelState('disabled', `AI service is offline: ${status.error}`);
            console.error("AI service check failed:", status.error);
        }
    } catch (error) {
        UIManager.setAiPanelState('disabled', `AI service is offline: ${error.message}`);
        console.error("Failed to check AI service status:", error.message);
    }
}

async function handleAiGenerate(promptText) {

    // Get selected model.
    const selectedModel = UIManager.getAiSelectedModel();
    if (!selectedModel || selectedModel === "No models found") {
        UIManager.showError("No AI model is selected or available.");
        return;
    }

    if (selectedModel.startsWith('llama_cpp::') || selectedModel.startsWith('lm_studio::')) {
        UIManager.showError("This action currently supports Gemini/Ollama models only. For llama.cpp/LM Studio, use the AI Assistant chat panel.");
        return;
    }

    if (selectedModel === '--export--') {
        // --- NEW: Call backend to get the prompt ---
        UIManager.showLoading("Building prompt for export...");
        try {
            const fullPromptText = await APIService.getFullAiPrompt(promptText);
            downloadTextFile('ai_prompt.md', fullPromptText);
            UIManager.showNotification("Prompt exported to ai_prompt.md!");
        } catch (error) {
            UIManager.showError("Failed to build prompt: " + (error.message || error));
        } finally {
            UIManager.hideLoading();
        }
        return; // Stop execution here
    }

    // If not exporting, proceed with the API call
    UIManager.setAiPanelState('loading'); // Set loading state

    try {
        const result = await APIService.processAiPrompt(promptText, selectedModel);
        syncUIWithState(result);
        UIManager.clearAiPrompt();
        UIManager.showNotification("AI command processed successfully!");
    } catch (error) {
        UIManager.showError("AI Assistant Error: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
        // Set state back to idle, regardless of success or failure
        UIManager.setAiPanelState('idle');
    }
}

// Find existing CAD import record by filename (case-insensitive)
function findExistingCadImportByFilename(filename) {
    const state = AppState.currentProjectState || {};
    const cadImports = state.cad_imports || [];
    const target = filename.toLowerCase().trim();
    for (const record of cadImports) {
        const sourceFilename = (record.source && record.source.filename) || '';
        if (sourceFilename.toLowerCase().trim() === target) {
            return record;
        }
    }
    return null;
}

// Handler for STEP file import and supported reimport
async function handleImportStep(file, importRecord = null) {
    if (!file) return;

    // If no explicit import record, check for existing import with same filename
    let effectiveRecord = importRecord;
    if (!effectiveRecord) {
        effectiveRecord = findExistingCadImportByFilename(file.name);
        if (effectiveRecord) {
            const sourceFilename = effectiveRecord.source?.filename || file.name;
            const answer = window.confirm(
                `A STEP import from "${sourceFilename}" already exists in this project.\n\n` +
                `Press OK to reimport (replace existing geometry in-place).\n` +
                `Press Cancel to import as new (creates duplicate assemblies).`
            );
            if (!answer) {
                // User chose "import as new", proceed without import record
                effectiveRecord = null;
            }
            // else: user chose reimport, keep effectiveRecord
        }
    }

    StepImportEditor.show(file, AppState.currentProjectState, effectiveRecord);
}

async function handleReimportStepImport(file, importRecord) {
    await handleImportStep(file, importRecord);
}

function getImportedCadLogicalVolumeIdSet(importRecord) {
    const batchContext = buildCadImportBatchContext(importRecord);
    return new Set(batchContext.logicalVolumeIds);
}

function getImportedCadMaterialSuggestion(importRecord) {
    const logicalVolumeIdSet = getImportedCadLogicalVolumeIdSet(importRecord);
    const projectState = AppState.currentProjectState || {};
    const logicalVolumes = projectState.logical_volumes || {};
    const materialRefs = [];

    for (const lv of Object.values(logicalVolumes)) {
        if (!lv || !logicalVolumeIdSet.has(lv.id)) continue;
        const materialRef = typeof lv.material_ref === 'string' ? lv.material_ref.trim() : '';
        if (materialRef) materialRefs.push(materialRef);
    }

    if (materialRefs.length === 0) {
        const materialNames = Object.keys(projectState.materials || {});
        return materialNames.length > 0 ? materialNames[0] : '';
    }

    return materialRefs[0];
}

function buildCadImportLogicalVolumeBatchUpdates(importRecord, partialUpdate) {
    const batchContext = buildCadImportBatchContext(importRecord);
    return batchContext.logicalVolumeIds.map((id) => ({
        id,
        ...partialUpdate,
    }));
}

async function handleCadImportBatchAction(action, importRecord) {
    const batchContext = buildCadImportBatchContext(importRecord);
    if (!batchContext.hasLogicalVolumes) {
        UIManager.showError("This STEP import did not record any logical volumes for batch editing.");
        return;
    }

    const selectionContext = getSelectionContext();
    const projectState = AppState.currentProjectState || {};

    if (action === 'material') {
        const availableMaterials = Object.keys(projectState.materials || {});
        if (availableMaterials.length === 0) {
            UIManager.showError("Create a material before applying one to imported logical volumes.");
            return;
        }

        const suggestedMaterial = getImportedCadMaterialSuggestion(importRecord) || availableMaterials[0];
        const promptMessage = `Assign a material to ${batchContext.logicalVolumeSummary}:`;
        const materialName = prompt(promptMessage, suggestedMaterial || '');
        if (materialName == null) {
            return;
        }

        const materialRef = materialName.trim();
        if (!materialRef) {
            return;
        }

        if (!projectState.materials || !projectState.materials[materialRef]) {
            UIManager.showError(`Material '${materialRef}' was not found.`);
            return;
        }

        const updates = buildCadImportLogicalVolumeBatchUpdates(importRecord, {
            material_ref: materialRef,
        });

        UIManager.showLoading(`Applying material to ${batchContext.logicalVolumeSummary}...`);
        try {
            const result = await APIService.updateLogicalVolumeBatch(updates);
            syncUIWithState(result, selectionContext);
        } catch (error) {
            UIManager.showError("Error applying material to imported CAD geometry: " + (error.message || error));
        } finally {
            UIManager.hideLoading();
        }
        return;
    }

    if (action === 'sensitive') {
        if (!UIManager.confirmAction(`Mark ${batchContext.logicalVolumeSummary} as sensitive?`)) {
            return;
        }

        const updates = buildCadImportLogicalVolumeBatchUpdates(importRecord, {
            is_sensitive: true,
        });

        UIManager.showLoading(`Marking ${batchContext.logicalVolumeSummary} sensitive...`);
        try {
            const result = await APIService.updateLogicalVolumeBatch(updates);
            syncUIWithState(result, selectionContext);
        } catch (error) {
            UIManager.showError("Error marking imported CAD geometry sensitive: " + (error.message || error));
        } finally {
            UIManager.hideLoading();
        }
        return;
    }

    UIManager.showError(`Unknown CAD import batch action '${action}'.`);
}

// NEW Handlers for the Assembly Definition Editor
function handleAddAssembly() {
    AssemblyEditor.show(null, AppState.currentProjectState);
}

function handleEditAssembly(assemblyData) {
    AssemblyEditor.show(assemblyData, AppState.currentProjectState);
}

async function handleAssemblyEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    if (data.isEdit) {
        UIManager.showLoading("Updating Assembly...");
        try {
            const result = await APIService.updateAssembly(data.id, data.placements);
            syncUIWithState(result, selectionContext);
        } catch (error) { UIManager.showError("Error updating assembly: " + error.message); }
        finally { UIManager.hideLoading(); }
    } else {
        UIManager.showLoading("Creating Assembly...");
        try {
            const result = await APIService.addAssembly(data.name, data.placements);
            const newSelection = [{ type: 'assembly', id: data.name, name: data.name }];
            syncUIWithState(result, newSelection);
        } catch (error) { UIManager.showError("Error creating assembly: " + error.message); }
        finally { UIManager.hideLoading(); }
    }
}

async function handleAddGroup(groupType, groupName) {
    UIManager.showLoading(`Creating group '${groupName}' of type '${groupType}'...`);
    try {
        const result = await APIService.createGroup(groupType, groupName);
        syncUIWithState(result); // This will now correctly redraw the hierarchy
    } catch (error) {
        UIManager.showError("Failed to create group: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

async function handleRenameGroup(groupType, oldName, newName) {
    UIManager.showLoading(`Renaming group...`);
    try {
        const result = await APIService.renameGroup(groupType, oldName, newName);
        syncUIWithState(result);
    } catch (error) {
        UIManager.showError("Failed to rename group: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

async function handleDeleteGroup(groupType, groupName) {
    UIManager.showLoading(`Deleting group '${groupName}'...`);
    try {
        const result = await APIService.deleteGroup(groupType, groupName);
        syncUIWithState(result);
    } catch (error) {
        UIManager.showError("Failed to delete group: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

async function handleMoveItemsToGroup(groupType, itemIds, targetGroupName) {
    const selectionContext = getSelectionContext();
    UIManager.showLoading(`Moving ${itemIds.length} item(s)...`);
    try {
        const result = await APIService.moveItemsToGroup(groupType, itemIds, targetGroupName);
        syncUIWithState(result, selectionContext); // Restore selection after move
    } catch (error) {
        UIManager.showError("Failed to move items: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

// Assembly functions
async function handleGroupIntoAssembly() {
    const selectionContexts = getSelectionContext();
    if (!selectionContexts || selectionContexts.length === 0) {
        UIManager.showError("Please select one or more Physical Volumes to group into an assembly.");
        return;
    }

    // Ensure all selected items are physical volumes
    const pvItems = selectionContexts.filter(item => item.type === 'physical_volume');
    if (pvItems.length !== selectionContexts.length) {
        UIManager.showError("You can only group Physical Volumes into an assembly. Please adjust your selection.");
        return;
    }

    const parentContext = UIManager.getSelectedParentContext();
    if (!parentContext) {
        UIManager.showError("Could not determine a parent volume for the new assembly. Please select the items from within a single parent volume.");
        return;
    }
    const parentLvName = parentContext.data.name || parentContext.name;

    const assemblyName = prompt("Enter a name for the new assembly:", "MyAssembly");
    if (!assemblyName || !assemblyName.trim()) {
        return; // User cancelled
    }

    const pvIds = pvItems.map(item => item.id);

    UIManager.showLoading("Creating assembly...");
    try {
        const result = await APIService.createAssemblyFromPVs(pvIds, assemblyName.trim(), parentLvName);
        // After creation, we want to select the new assembly's placement
        const newAssemblyPV = findPlacementOfVolume(result.project_state, assemblyName.trim());
        syncUIWithState(result, newAssemblyPV ? [newAssemblyPV] : []);
    } catch (error) {
        UIManager.showError("Failed to create assembly: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

// Helper to find the new assembly's PV after creation
function findPlacementOfVolume(projectState, volumeRefName) {
    for (const lv of Object.values(projectState.logical_volumes)) {
        if (lv.content_type === 'physvol') {
            for (const pv of lv.content) {
                if (pv.volume_ref === volumeRefName) {
                    return { type: 'physical_volume', id: pv.id, name: pv.name, data: pv };
                }
            }
        }
    }
    return null;
}

async function handleMovePvToAssembly(pvId, assemblyName) {
    UIManager.showLoading(`Moving PV to assembly '${assemblyName}'...`);
    try {
        const result = await APIService.movePvToAssembly(pvId, assemblyName);
        syncUIWithState(result); // This redraws everything
    } catch (error) {
        UIManager.showError("Failed to move PV: " + error.message);
    } finally {
        UIManager.hideLoading();
    }
}

async function handleMovePvToLv(pvId, lvName) {
    UIManager.showLoading(`Moving PV to volume '${lvName}'...`);
    try {
        const result = await APIService.movePvToLv(pvId, lvName);
        syncUIWithState(result);
    } catch (error) {
        UIManager.showError("Failed to move PV: " + error.message);
    } finally {
        UIManager.hideLoading();
    }
}

function handleAddOpticalSurface() {
    OpticalSurfaceEditor.show(null, AppState.currentProjectState);
}

function handleEditOpticalSurface(osData) {
    OpticalSurfaceEditor.show(osData, AppState.currentProjectState);
}

async function handleOpticalSurfaceEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    // These API functions don't exist yet, but we are setting up the frontend for them
    const apiCall = data.isEdit
        ? APIService.updateOpticalSurface(data.id, data)
        : APIService.addOpticalSurface(data.name, data);

    const loadingMessage = data.isEdit ? "Updating Optical Surface..." : "Creating Optical Surface...";
    UIManager.showLoading(loadingMessage);
    try {
        const result = await apiCall;
        const newSelection = [{ type: 'optical_surface', id: data.name, name: data.name, data: result.project_state.optical_surfaces[data.name] }];
        syncUIWithState(result, data.isEdit ? selectionContext : newSelection);
    } catch (error) {
        UIManager.showError("Error processing Optical Surface: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

function handleAddSkinSurface() {
    SkinSurfaceEditor.show(null, AppState.currentProjectState);
}

function handleEditSkinSurface(ssData) {
    SkinSurfaceEditor.show(ssData, AppState.currentProjectState);
}

async function handleSkinSurfaceEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    // These API functions will be created in the next step
    const apiCall = data.isEdit
        ? APIService.updateSkinSurface(data.id, data)
        : APIService.addSkinSurface(data.name, data);

    const loadingMessage = data.isEdit ? "Updating Skin Surface..." : "Creating Skin Surface...";
    UIManager.showLoading(loadingMessage);
    try {
        const result = await apiCall;
        const newSelection = [{ type: 'skin_surface', id: data.name, name: data.name, data: result.project_state.skin_surfaces[data.name] }];
        syncUIWithState(result, data.isEdit ? selectionContext : newSelection);
    } catch (error) {
        UIManager.showError("Error processing Skin Surface: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

function handleAddBorderSurface() {
    BorderSurfaceEditor.show(null, AppState.currentProjectState);
}

function handleEditBorderSurface(bsData) {
    BorderSurfaceEditor.show(bsData, AppState.currentProjectState);
}

async function handleBorderSurfaceEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    // These API functions will be created in the next step
    const apiCall = data.isEdit
        ? APIService.updateBorderSurface(data.id, data)
        : APIService.addBorderSurface(data.name, data);

    const loadingMessage = data.isEdit ? "Updating Border Surface..." : "Creating Border Surface...";
    UIManager.showLoading(loadingMessage);
    try {
        const result = await apiCall;
        const newSelection = [{ type: 'border_surface', id: data.name, name: data.name, data: result.project_state.border_surfaces[data.name] }];
        syncUIWithState(result, data.isEdit ? selectionContext : newSelection);
    } catch (error) {
        UIManager.showError("Error processing Border Surface: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

function handleAddElement() {
    ElementEditor.show(null, AppState.currentProjectState);
}

function handleEditElement(elData) {
    ElementEditor.show(elData, AppState.currentProjectState);
}

async function handleElementEditorConfirm(data) {
    const selectionContext = getSelectionContext();
    const apiCall = data.isEdit
        ? APIService.updateElement(data.id, data)
        : APIService.addElement(data.name, data);

    const loadingMessage = data.isEdit ? "Updating Element..." : "Creating Element...";
    UIManager.showLoading(loadingMessage);
    try {
        const result = await apiCall;
        const newElementName = Object.keys(result.project_state.elements).find(k => k.startsWith(data.name)) || data.name;
        const newSelection = [{ type: 'element', id: newElementName, name: newElementName, data: result.project_state.elements[newElementName] }];
        syncUIWithState(result, data.isEdit ? selectionContext : newSelection);
    } catch (error) {
        UIManager.showError("Error processing Element: " + (error.message || error));
    } finally {
        UIManager.hideLoading();
    }
}

/**
 * Checks if a given item from a selection context still exists in a new project state.
 * @param {object} itemContext - The item to check { type, id, name, data }.
 * @param {object} newState - The full project state object to check against.
 * @returns {boolean} - True if the item exists, false otherwise.
 */
function doesItemExistInState(itemContext, newState) {
    const { type, id, name } = itemContext; // 'name' and 'id' are often the same
    if (!newState || !type || !id) return false;

    switch (type) {
        case 'physical_volume':
            // Must search all possible parents for the PV's ID
            for (const lv of Object.values(newState.logical_volumes || {})) {
                if (lv.content_type === 'physvol' && lv.content.some(pv => pv.id === id)) {
                    return true;
                }
            }
            for (const asm of Object.values(newState.assemblies || {})) {
                if (asm.placements.some(pv => pv.id === id)) {
                    return true;
                }
            }
            return false; // Not found in any LV or Assembly

        // For all other types, the ID is the name, so we can do a direct lookup.
        case 'logical_volume':
            return !!newState.logical_volumes?.[name];
        case 'assembly':
            return !!newState.assemblies?.[name];
        case 'solid':
            return !!newState.solids?.[name];
        case 'material':
            return !!newState.materials?.[name];
        case 'element':
            return !!newState.elements?.[name];
        case 'isotope':
            return !!newState.isotopes?.[name];
        case 'define':
            return !!newState.defines?.[name];
        case 'optical_surface':
            return !!newState.optical_surfaces?.[name];
        case 'skin_surface':
            return !!newState.skin_surfaces?.[name];
        case 'border_surface':
            return !!newState.border_surfaces?.[name];

        default:
            return false;
    }
}

function handleCameraModeChange(mode) {
    if (mode === 'origin') {
        // Center the camera on the world origin
        SceneManager.centerCameraOn(null); // Passing null resets to (0,0,0)
        UIManager.setActiveCameraModeButton('origin');
    } else if (mode === 'selected') {
        const selection = AppState.selectedThreeObjects;

        if (selection && selection.length > 0) {
            let target; // This will be either a single object or a Vector3 for the center

            if (selection.length === 1) {
                // If only one object is selected, target it directly.
                target = selection[0];
            } else {
                // --- NEW ROBUST LOGIC for MULTI-SELECT ---
                // If multiple objects are selected, calculate their collective center.
                // This works regardless of the current mode or if the gizmo is visible.
                const multiSelectBox = new THREE.Box3();

                selection.forEach(obj => {
                    // Important: Ensure the object's bounding box is up-to-date with its world matrix
                    const box = new THREE.Box3().setFromObject(obj);
                    multiSelectBox.union(box); // Expand the main box to include this object's box
                });

                // The target is now the center of this combined bounding box.
                target = new THREE.Vector3();
                multiSelectBox.getCenter(target);
            }

            // Set the new camera center.
            SceneManager.centerCameraOn(target);

            // Update the menu buttons.
            UIManager.setActiveCameraModeButton('selected');
        } else {
            UIManager.showNotification("Please select an object to center the camera on.");
        }
    }
}

function formatStepImportReportMessage(report, smartImportRequested = false, isReimport = false) {
    const actionLabel = isReimport ? 'reimport' : 'import';
    if (!report) {
        return smartImportRequested
            ? `STEP file ${actionLabel}ed. Smart CAD report unavailable.`
            : `STEP file ${actionLabel}ed successfully.`;
    }

    if (!report.enabled) {
        return `STEP file ${actionLabel}ed successfully (smart import disabled).`;
    }

    const summary = report.summary || {};
    const total = summary.total || 0;
    const modeCounts = summary.selected_mode_counts || {};
    const primitiveSelected = modeCounts.primitive || 0;
    const tessSelected = modeCounts.tessellated || 0;

    const ratioPct = total > 0
        ? ((summary.selected_primitive_ratio || 0) * 100).toFixed(1)
        : "0.0";

    const fallbackReasonCounts = {};
    (report.candidates || []).forEach(c => {
        if (c?.selected_mode === 'tessellated' && c?.fallback_reason) {
            fallbackReasonCounts[c.fallback_reason] = (fallbackReasonCounts[c.fallback_reason] || 0) + 1;
        }
    });

    const topReasons = Object.entries(fallbackReasonCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([reason, count]) => `${reason}: ${count}`);

    const lines = [
        `STEP ${actionLabel} complete (Smart CAD).`,
        `Total solids: ${total}`,
        `Selected primitives: ${primitiveSelected} (${ratioPct}%)`,
        `Selected tessellated fallback: ${tessSelected}`,
    ];

    if (topReasons.length > 0) {
        lines.push(`Top fallback reasons: ${topReasons.join(', ')}`);
    }

    return lines.join("\n");
}

async function handleConfirmStepImport(options) {
    if (!options || !options.file) return;

    UIManager.showLoading(`Importing ${options.file.name}... This may take a moment.`);

    try {
        const formData = new FormData();
        formData.append('stepFile', options.file);

        // We send the rest of the options, but remove the file object itself
        // as it's already been appended.
        const optionsForJson = { ...options };
        delete optionsForJson.file;
        formData.append('options', JSON.stringify(optionsForJson));

        const result = await APIService.importStepWithOptions(formData);
        syncUIWithState(result);
        UIManager.hideLoading();

        const reportMessage = formatStepImportReportMessage(
            result.step_import_report,
            optionsForJson.smartImport,
            Boolean(optionsForJson.reimportTargetImportId)
        );
        if (reportMessage) {
            UIManager.showNotification(reportMessage);
        }

        if (result.step_import_report && result.step_import_report.enabled) {
            StepImportEditor.showImportReport(result.step_import_report, options.file?.name || '');
        }
    } catch (error) {
        UIManager.hideLoading();
        UIManager.showError("Failed to import STEP file: " + error.message);
    } finally {
        document.getElementById('stepFile').value = null;
    }
}

async function handleParameterRegistryRefresh() {
    const result = await APIService.getParameterRegistry();
    return result.parameter_registry || {};
}

async function handleParameterRegistrySave(payload) {
    UIManager.showLoading("Saving parameter...");
    try {
        const result = await APIService.upsertParameterRegistry(payload);
        syncUIWithState(result);
        UIManager.showNotification(`Parameter '${payload.name}' saved.`);
    } catch (error) {
        UIManager.showError("Failed to save parameter: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParameterRegistryDelete(name) {
    UIManager.showLoading("Deleting parameter...");
    try {
        const result = await APIService.deleteParameterRegistry(name);
        syncUIWithState(result);
        UIManager.showNotification(`Parameter '${name}' deleted.`);
    } catch (error) {
        UIManager.showError("Failed to delete parameter: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleOpenParameterRegistry() {
    ensureParameterRegistryEditorInit();
    try {
        const result = await APIService.getParameterRegistry();
        await ParameterRegistryEditor.show(result.parameter_registry || {});
    } catch (error) {
        UIManager.showError("Failed to open parameter registry: " + error.message);
    }
}

async function handleParamStudyRefresh() {
    const result = await APIService.getParamStudies();
    return result.param_studies || {};
}

async function handleParamStudySave(payload) {
    UIManager.showLoading("Saving param study...");
    try {
        const result = await APIService.upsertParamStudy(payload);
        syncUIWithState(result);
        UIManager.showNotification(`Param study '${payload.name}' saved.`);
    } catch (error) {
        UIManager.showError("Failed to save param study: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParamStudyDelete(name) {
    UIManager.showLoading("Deleting param study...");
    try {
        const result = await APIService.deleteParamStudy(name);
        syncUIWithState(result);
        UIManager.showNotification(`Param study '${name}' deleted.`);
    } catch (error) {
        UIManager.showError("Failed to delete param study: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParamStudyRun(name, maxRuns = null) {
    UIManager.showLoading(`Running parameter sweep (no simulation) for '${name}'...`);
    try {
        const result = await APIService.runParamStudy(name, maxRuns);
        UIManager.showNotification(`Parameter sweep completed for '${name}' (no simulation).`);
        return result.study_result || result;
    } catch (error) {
        UIManager.showError("Failed to run parameter sweep: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParamStudyRunOptimizer(payload) {
    UIManager.showLoading(`Running optimizer for '${payload.study_name}'...`);
    try {
        const result = await APIService.runParamOptimizer(payload);
        UIManager.showNotification(`Optimizer run complete for '${payload.study_name}'.`);
        return result.optimizer_result || result;
    } catch (error) {
        UIManager.showError("Failed to run optimizer: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParamStudyApplyCandidate(studyName, values) {
    UIManager.showLoading('Applying candidate to geometry...');
    try {
        const result = await APIService.applyParamStudyCandidate(studyName, values);
        syncUIWithState(result);
        UIManager.showNotification('Geometry updated from selected parameter set.');
        return result;
    } catch (error) {
        UIManager.showError('Failed to apply selected candidate: ' + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

// --- Wizard Handlers ---

function handleWizardGetGeometryState() {
    return AppState.currentProjectState || {};
}

async function handleWizardGetSimulationMetrics() {
    try {
        const result = await APIService.getSimulationMetrics();
        return result.metrics || [];
    } catch (error) {
        UIManager.showError('Failed to load simulation metrics: ' + error.message);
        return [];
    }
}

async function handleParamOptimizerGetActiveRunStatus() {
    try {
        return await APIService.getActiveParamOptimizerRunStatus();
    } catch (error) {
        throw error;
    }
}

async function handleParamOptimizerStopActiveRun(reason = 'user_requested_stop') {
    try {
        const result = await APIService.stopActiveParamOptimizerRun(reason);
        if (result?.active && result?.stop_requested) {
            UIManager.showNotification('Stop requested for active run. Current candidate will finish before termination.');
        } else {
            UIManager.showNotification('No active run to stop.');
        }
        return result;
    } catch (error) {
        UIManager.showError("Failed to request stop: " + error.message);
        throw error;
    }
}

async function handleParamOptimizerReplayBest(runId, options = {}) {
    const opts = (options && typeof options === 'object') ? options : { applyToProject: !!options };
    UIManager.showLoading(`Replaying best candidate (${runId})...`);
    try {
        const result = await APIService.replayParamOptimizerBest(runId, opts);
        if (opts.applyToProject !== false) {
            syncUIWithState(result);
        }
        UIManager.showNotification('Best candidate replay completed.');
        return result;
    } catch (error) {
        UIManager.showError("Failed to replay best candidate: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParamOptimizerVerifyBest(runId, options = {}) {
    const opts = (options && typeof options === 'object') ? options : { repeats: options };
    UIManager.showLoading(`Verifying best candidate (${runId})...`);
    try {
        const result = await APIService.verifyParamOptimizerBest(runId, opts);
        UIManager.showNotification('Best candidate verification completed.');
        return result;
    } catch (error) {
        UIManager.showError("Failed to verify best candidate: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParamOptimizerGetApplyAuditHistory(limit = 20) {
    try {
        const result = await APIService.getParamOptimizerApplyAuditHistory(limit);
        return result;
    } catch (error) {
        UIManager.showError("Failed to load apply audit history: " + error.message);
        throw error;
    }
}

async function handleParamOptimizerRollbackLastApply(auditId = null) {
    UIManager.showLoading('Rolling back apply action...');
    try {
        const result = await APIService.rollbackLastParamOptimizerApply(auditId);
        syncUIWithState(result);
        UIManager.showNotification('Rollback completed.');
        return result;
    } catch (error) {
        UIManager.showError("Failed to rollback apply action: " + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleParamOptimizerGetApplyAuditDiagnostics() {
    try {
        const result = await APIService.getParamOptimizerApplyAuditDiagnostics();
        return result;
    } catch (error) {
        UIManager.showError("Failed to load apply audit diagnostics: " + error.message);
        throw error;
    }
}

async function handleOpenParamStudies() {
    ensureParamStudyEditorInit();
    try {
        const result = await APIService.getParamStudies();
        await ParamStudyEditor.show(result.param_studies || {});
    } catch (error) {
        UIManager.showError("Failed to open param studies: " + error.message);
    }
}

async function handleObjectiveBuilderSchema() {
    const result = await APIService.getObjectiveBuilderSchema();
    return result.schema || {};
}

async function handleObjectiveBuilderExample(template = 'weighted_tradeoff') {
    const result = await APIService.getObjectiveBuilderExample(template);
    return result.payload || {};
}

async function handleObjectiveBuilderValidate(payload) {
    UIManager.showLoading('Validating objective builder payload...');
    try {
        const result = await APIService.validateObjectiveBuilder(payload);
        return result;
    } catch (error) {
        UIManager.showError('Objective builder validation failed: ' + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleObjectiveBuilderBuild(payload) {
    UIManager.showLoading('Building objective payload...');
    try {
        const result = await APIService.buildObjectiveBuilder(payload);
        return result;
    } catch (error) {
        UIManager.showError('Objective builder build failed: ' + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleObjectiveBuilderUpsert(payload) {
    UIManager.showLoading('Upserting objective builder study...');
    try {
        const result = await APIService.upsertObjectiveBuilderStudy(payload);
        if (!result?.dry_run) {
            UIManager.showNotification(`Objective builder study '${result?.study_name || payload?.study_name || ''}' ${result?.action || 'saved'}.`);
        }
        return result;
    } catch (error) {
        UIManager.showError('Objective builder upsert failed: ' + error.message);
        throw error;
    } finally {
        UIManager.hideLoading();
    }
}

async function handleObjectiveBuilderLaunch(payload) {
    const isDryRun = !!payload?.dry_run;
    if (isDryRun) {
        UIManager.showLoading('Preparing objective builder launch (dry run)...');
    }
    try {
        const result = await APIService.launchObjectiveBuilder(payload);
        if (!result?.dry_run && result?.optimizer_result) {
            UIManager.showNotification('Simulation-in-loop optimization completed.');
        }
        return result;
    } catch (error) {
        UIManager.showError('Objective builder launch failed: ' + error.message);
        throw error;
    } finally {
        if (isDryRun) UIManager.hideLoading();
    }
}

async function handleObjectiveBuilderLaunchStatus(runControlId) {
    const result = await APIService.getObjectiveBuilderLaunchStatus(runControlId);
    return result || {};
}

function getAvailableVolumes() {
    if (!AppState.currentProjectState) return [];
    const volumes = [];

    // Collect from Logical Volumes
    Object.values(AppState.currentProjectState.logical_volumes || {}).forEach(lv => {
        if (lv.content_type === 'physvol' && lv.content) {
            lv.content.forEach(pv => volumes.push(pv));
        }
    });

    // Collect from Assemblies
    Object.values(AppState.currentProjectState.assemblies || {}).forEach(asm => {
        if (asm.placements) {
            asm.placements.forEach(pv => volumes.push(pv));
        }
    });

    // Sort by name
    return volumes.sort((a, b) => a.name.localeCompare(b.name));
}

async function handleAddGps() {
    // Show empty editor
    const availableVolumes = getAvailableVolumes();
    GpsEditor.show(null, availableVolumes);
}

function handleEditGps(sourceData) {
    // Ensure we send the latest state to the editor, as the UI tree node might be stale
    let dataToUse = sourceData;
    if (sourceData && sourceData.name && AppState.currentProjectState && AppState.currentProjectState.sources) {
        const freshSource = AppState.currentProjectState.sources[sourceData.name];
        if (freshSource) {
            dataToUse = freshSource;
        }
    }
    GpsEditor.show(dataToUse, getAvailableVolumes());
}

async function handleGpsEditorConfirm(data) {
    // This handles both creating and editing sources
    const selectionContext = getSelectionContext();
    if (data.isEdit) {

        UIManager.showLoading("Updating Particle Source...");
        try {
            // Note: data.id is the source's name. We need the unique ID from the selection.
            const sourceId = (selectionContext && selectionContext[0]) ? selectionContext[0].id : null;
            if (!sourceId) {
                throw new Error("Could not determine the unique ID of the source to update.");
            }
            const result = await APIService.updateParticleSource(sourceId, data.name, data.gps_commands, data.position, data.rotation, data.activity, data.confine_to_pv, data.volume_link_id);
            syncUIWithState(result, selectionContext);
        } catch (error) {
            UIManager.showError("Error updating source: " + (error.message || error));
        } finally {
            UIManager.hideLoading();
        }

    } else {
        UIManager.showLoading("Creating Particle Source...");
        try {
            const result = await APIService.addParticleSource(data.name, data.gps_commands, data.position, data.rotation, data.activity, data.confine_to_pv, data.volume_link_id);
            // After creating, find the new source in the response to select it
            const newSource = Object.values(result.project_state.sources).find(s => s.name === data.name);
            const newSelection = newSource ? [{
                type: 'particle_source',
                id: newSource.id,
                name: newSource.name,
                data: newSource,
                selData: { is_source: true }
            }] : [];
            syncUIWithState(result, newSelection);
        } catch (error) {
            UIManager.showError("Error creating source: " + (error.message || error));
        } finally {
            UIManager.hideLoading();
        }
    }
}

// --- Simulation functions ---
function formatPreflightIssues(issues, limit = 5) {
    if (!issues || issues.length === 0) return "";
    return issues.slice(0, limit).map(issue => {
        const hint = issue.hint ? ` (hint: ${issue.hint})` : '';
        return `- [${issue.severity}] ${issue.message}${hint}`;
    }).join('\n');
}

function formatPreflightScopeLabel(scope) {
    if (!scope || !scope.type || !scope.name) return '';
    const typeLabel = scope.type === 'logical_volume'
        ? 'LV'
        : (scope.type === 'assembly' ? 'Assembly' : scope.type);
    return `${typeLabel} \"${scope.name}\"`;
}

function resolveScopedPreflightCandidateFromVolumeRef(volumeRef) {
    const volumeRefNorm = String(volumeRef || '').trim();
    if (!volumeRefNorm) return null;

    const state = AppState.currentProjectState || {};
    const assemblies = state.assemblies || {};
    if (Object.prototype.hasOwnProperty.call(assemblies, volumeRefNorm)) {
        return { type: 'assembly', name: volumeRefNorm };
    }

    const logicalVolumes = state.logical_volumes || {};
    if (Object.prototype.hasOwnProperty.call(logicalVolumes, volumeRefNorm)) {
        return { type: 'logical_volume', name: volumeRefNorm };
    }

    return null;
}

function resolveScopedPreflightCandidateFromSelectionItem(item) {
    if (!item || !item.type) return null;

    if (item.type === 'logical_volume' || item.type === 'assembly') {
        const nameNorm = String(item.name || '').trim();
        if (!nameNorm) return null;
        return { type: item.type, name: nameNorm };
    }

    if (item.type === 'physical_volume') {
        const volumeRef = item?.selData?.volume_ref ?? item?.data?.volume_ref;
        return resolveScopedPreflightCandidateFromVolumeRef(volumeRef);
    }

    return null;
}

function buildScopedPreflightRequestFromSelection() {
    const selection = getSelectionContext();
    if (!Array.isArray(selection) || selection.length === 0) {
        return { candidate: null, reason: 'no_selection', candidateCount: 0 };
    }

    const candidates = [];
    const seen = new Set();

    selection.forEach(item => {
        const candidate = resolveScopedPreflightCandidateFromSelectionItem(item);
        if (!candidate) return;
        const key = `${candidate.type}:${candidate.name}`;
        if (!seen.has(key)) {
            seen.add(key);
            candidates.push(candidate);
        }
    });

    if (candidates.length === 0) {
        return { candidate: null, reason: 'selection_not_scopeable', candidateCount: 0 };
    }
    if (candidates.length > 1) {
        return { candidate: null, reason: 'ambiguous_selection', candidateCount: candidates.length };
    }

    return { candidate: candidates[0], reason: 'resolved', candidateCount: 1 };
}

async function runAndRenderPreflight({
    enforceRunBlocking = false,
    confirmWarnings = false,
    showNotification = false,
    preferScopedSelection = false,
} = {}) {
    UIManager.setPreflightState('running');

    let report = null;
    let scopedReport = null;
    let scope = null;
    let summaryDelta = null;
    let issueFamilyCorrelations = null;
    let usedScopedPreflight = false;
    let scopedSelectionReason = null;
    let scopedSelectionCandidateCount = 0;
    let scopedFallbackError = null;

    try {
        const scopedSelectionResult = preferScopedSelection
            ? buildScopedPreflightRequestFromSelection()
            : { candidate: null, reason: null, candidateCount: 0 };
        const scopedSelection = scopedSelectionResult?.candidate || null;
        scopedSelectionReason = scopedSelectionResult?.reason || null;
        scopedSelectionCandidateCount = scopedSelectionResult?.candidateCount || 0;

        if (scopedSelection) {
            try {
                const scopedPayload = await APIService.runScopedPreflightChecks(scopedSelection.type, scopedSelection.name);
                report = scopedPayload?.preflight_report || {};
                scopedReport = scopedPayload?.scoped_preflight_report || {};
                scope = scopedPayload?.scope || scopedSelection;
                summaryDelta = scopedPayload?.summary_delta || null;
                issueFamilyCorrelations = scopedPayload?.issue_family_correlations || null;
                usedScopedPreflight = true;
            } catch (scopeError) {
                scopedFallbackError = String(scopeError?.message || scopeError || 'unknown_error');
                console.warn('Scoped preflight failed; falling back to global preflight:', scopeError);
            }
        }

        if (!report) {
            const preflight = await APIService.runPreflightChecks();
            report = preflight.preflight_report || {};
        }

        const summary = report.summary || {};
        UIManager.renderPreflightReport(report, {
            scope,
            scopedReport,
            summaryDelta,
            issueFamilyCorrelations,
            usedScopedPreflight,
            preferScopedSelection,
            scopedSelectionReason,
            scopedSelectionCandidateCount,
            scopedFallbackError,
        });

        const errors = summary.errors || 0;
        const warnings = summary.warnings || 0;
        const infos = summary.infos || 0;

        if (showNotification) {
            if (usedScopedPreflight && scopedReport?.summary) {
                const scopedSummary = scopedReport.summary || {};
                const scopeErrors = scopedSummary.errors || 0;
                const scopeWarnings = scopedSummary.warnings || 0;
                const scopeInfos = scopedSummary.infos || 0;
                UIManager.showNotification(
                    `Scoped preflight (${formatPreflightScopeLabel(scope)}): ` +
                    `${scopeErrors} error(s), ${scopeWarnings} warning(s), ${scopeInfos} info. ` +
                    `Full geometry: ${errors}/${warnings}/${infos}.`
                );
            } else {
                UIManager.showNotification(`Preflight complete: ${errors} error(s), ${warnings} warning(s), ${infos} info.`);
            }
        }

        if (enforceRunBlocking && !summary.can_run) {
            const errorIssues = (report.issues || []).filter(i => i.severity === 'error');
            UIManager.showError(
                "Preflight checks failed.\n" +
                formatPreflightIssues(errorIssues, 8)
            );
            return {
                ok: false,
                report,
                scope,
                scopedReport,
                summaryDelta,
                issueFamilyCorrelations,
                usedScopedPreflight,
                scopedSelectionReason,
                scopedSelectionCandidateCount,
                scopedFallbackError,
            };
        }

        if (enforceRunBlocking && warnings > 0 && confirmWarnings) {
            const warningIssues = (report.issues || []).filter(i => i.severity === 'warning');
            const proceed = UIManager.confirmAction(
                "Preflight warnings detected:\n\n" +
                formatPreflightIssues(warningIssues, 8) +
                "\n\nContinue anyway?"
            );
            if (!proceed) {
                return {
                    ok: false,
                    report,
                    scope,
                    scopedReport,
                    summaryDelta,
                    issueFamilyCorrelations,
                    usedScopedPreflight,
                    scopedSelectionReason,
                    scopedSelectionCandidateCount,
                    scopedFallbackError,
                };
            }
        }

        return {
            ok: true,
            report,
            scope,
            scopedReport,
            summaryDelta,
            issueFamilyCorrelations,
            usedScopedPreflight,
            scopedSelectionReason,
            scopedSelectionCandidateCount,
            scopedFallbackError,
        };
    } catch (error) {
        UIManager.showError("Failed to run preflight checks: " + error.message);
        return {
            ok: false,
            report: null,
            scope: null,
            scopedReport: null,
            summaryDelta: null,
            issueFamilyCorrelations: null,
            usedScopedPreflight: false,
            scopedSelectionReason: null,
            scopedSelectionCandidateCount: 0,
            scopedFallbackError: String(error?.message || error || 'unknown_error'),
        };
    } finally {
        UIManager.setPreflightState('idle');
    }
}

async function handleRunPreflight() {
    await runAndRenderPreflight({
        enforceRunBlocking: false,
        confirmWarnings: false,
        showNotification: true,
        preferScopedSelection: true,
    });
}

async function handleRunSimulation(simSettings) {
    console.log("Checking active sources before run...");
    console.log("AppState.activeSourceIds:", AppState.activeSourceIds);

    // Fallback: Check the DOM if AppState seems empty but user claims to have selected something
    if (!AppState.activeSourceIds || AppState.activeSourceIds.length === 0) {
        console.warn("AppState.activeSourceIds is empty. Checking DOM for checked boxes...");
        const checkedBoxes = document.querySelectorAll('.active-source-checkbox:checked');
        if (checkedBoxes.length > 0) {
            const domIds = Array.from(checkedBoxes).map(cb => cb.value);
            console.log("Found active sources in DOM:", domIds);
            AppState.activeSourceIds = domIds;
        }
    }

    if (!AppState.activeSourceIds || AppState.activeSourceIds.length === 0) {
        UIManager.showError("Please select an active particle source in the hierarchy.");
        return;
    }

    // Get the number of events from the UI
    const numEvents = parseInt(document.getElementById('simEventsInput').value, 10);
    if (numEvents <= 0) {
        UIManager.showError("Please enter a valid number of events.");
        return;
    }

    // Preflight checks before simulation start.
    const preflightResult = await runAndRenderPreflight({
        enforceRunBlocking: true,
        confirmWarnings: true,
        showNotification: false,
    });
    if (!preflightResult.ok) {
        return;
    }

    // Prepare the final parameters to send to the backend
    const sim_params = {
        ...buildResolvedSimulationOptions(AppState.currentProjectState, AppState.simOptions),
        events: numEvents,
    };

    try {
        UIManager.setSimulationState('running');
        UIManager.clearSimConsole();
        AppState.simConsoleLineCount = 0;
        UIManager.appendToSimConsole("Starting simulation...");

        const result = await APIService.runSimulation(sim_params);
        AppState.currentSimJobId = result.job_id;
        AppState.lastSimVersionId = result.version_id;

        // When a new simulation starts, the old LORs and reconstruction are invalid
        UIManager.setReconstructionButtonEnabled(false);
        UIManager.setLorStatus("No LORs processed for this new run.", false);

        // Start polling for status updates
        AppState.simStatusPoller = setInterval(pollSimStatus, 2000); // Poll every 2 seconds

    } catch (error) {
        UIManager.showError("Failed to start simulation: " + error.message);
        UIManager.setSimulationState('idle');
    }
}

async function pollSimStatus() {
    if (!AppState.currentSimJobId) return;

    try {
        // Let's ask for new lines since our last check
        const result = await APIService.getSimulationStatus(AppState.currentSimJobId, AppState.simConsoleLineCount);

        if (result.success) {
            const status = result.status;

            // Append any new stdout/stderr lines to the console
            if (status.new_stdout) {
                status.new_stdout.forEach(line => UIManager.appendToSimConsole(line));
            }
            if (status.new_stderr) {
                status.new_stderr.forEach(line => {
                    const isWarning = typeof line === 'string' && line.trim().toLowerCase().startsWith('warning:');
                    const prefix = isWarning ? '[WARNING]' : '[ERROR]';
                    UIManager.appendToSimConsole(`${prefix} ${line}`);
                });
            }

            // Update the line count
            AppState.simConsoleLineCount = status.total_lines;

            if (status.status === 'Completed' || status.status === 'Error') {
                clearInterval(AppState.simStatusPoller);
                AppState.simStatusPoller = null;
                if (status.status === 'Completed') {
                    AppState.lastSimJobId = AppState.currentSimJobId;
                    // Enable the reconstruction and download buttons **
                    UIManager.setAnalysisModalButtonEnabled(true);
                    UIManager.setReconModalButtonEnabled(true);
                    UIManager.setDownloadButtonEnabled(true);
                    try {
                        const metaResult = await APIService.getSimulationMetadata(
                            AppState.lastSimVersionId,
                            AppState.lastSimJobId,
                        );
                        if (metaResult.success) {
                            UIManager.setLoadedScoringResultMetadata(
                                AppState.lastSimVersionId,
                                AppState.lastSimJobId,
                                metaResult.metadata,
                            );
                        }
                    } catch (metadataError) {
                        console.warn('Failed to load scoring metadata for completed run:', metadataError);
                    }
                    // Update status display on completion
                    UIManager.updateSimStatusDisplay(AppState.lastSimJobId, status.total_events);
                }
                AppState.currentSimJobId = null;
                UIManager.setSimulationState('idle');
                UIManager.appendToSimConsole(`\n--- Simulation ${status.status} ---`);
                if (status.status === 'Completed' && UIManager.getDrawTracksOptions().draw) {
                    // Call the track fetching and drawing function
                    fetchAndDrawTracks(AppState.lastSimVersionId, AppState.lastSimJobId, UIManager.getDrawTracksOptions().range);
                }
            }
        }
    } catch (error) {
        console.error("Polling error:", error);
        clearInterval(AppState.simStatusPoller);
        AppState.simStatusPoller = null;
        UIManager.setSimulationState('idle');
        UIManager.appendToSimConsole(`--- Polling Error: ${error.message} ---`);
    }
}

async function handleStopSimulation() {
    if (!AppState.currentSimJobId) return;

    UIManager.appendToSimConsole("Sending stop request...");
    // We need a new API endpoint for this
    try {
        await APIService.stopSimulation(AppState.currentSimJobId);
        // The poller will eventually report the status as "Error" or "Completed" (Aborted)
    } catch (error) {
        UIManager.showError("Failed to send stop request: " + error.message);
    }
}

/**
 * Orchestrates fetching track data from the backend and telling the scene manager to draw it.
 * @param {string} versionId The ID of the project version for the run.
 * @param {string} jobId The ID of the simulation run.
 * @param {string|number} eventSpec The event(s) to fetch, e.g., 'all' or 0.
 */
async function fetchAndDrawTracks(versionId, jobId, eventSpec) {
    if (!versionId || !jobId) {
        UIManager.showError("Cannot fetch tracks: Missing version or job ID.");
        return;
    }

    UIManager.showLoading("Loading simulation tracks...");
    try {
        // 1. Call the API service to get the raw text data for the tracks
        const trackData = await APIService.getEventTracks(versionId, jobId, eventSpec);

        // 2. Pass the raw text data to the SceneManager to parse and draw
        SceneManager.drawTracks(trackData);

    } catch (error) {
        // The apiService function will throw a detailed error if the fetch fails
        UIManager.showError(`Could not load tracks: ${error.message}`);
    } finally {
        UIManager.hideLoading();
    }
}

function handleOpenSimOptions() {
    UIManager.setSimOptions(
        buildResolvedSimulationOptions(AppState.currentProjectState, AppState.simOptions),
    );
    UIManager.showSimOptionsModal();
}

function handleSaveSimOptions() {
    AppState.simOptions = buildSimulationOptionOverrides(
        AppState.currentProjectState,
        UIManager.getSimOptions(),
    );
    UIManager.hideSimOptionsModal();
    //UIManager.showNotification("Simulation options saved for the next run.");
}

async function handleDrawTracksToggle() {
    const drawOptions = UIManager.getDrawTracksOptions();

    // Always clear existing tracks when this is triggered
    SceneManager.clearTracks();

    if (drawOptions.draw && drawOptions.range.trim() !== '') {
        if (!AppState.lastSimVersionId || !AppState.lastSimJobId) {
            UIManager.showNotification("No completed simulation run available to draw tracks from.");
            return;
        }
        // Fetch and draw the requested range
        await fetchAndDrawTracks(AppState.lastSimVersionId, AppState.lastSimJobId, drawOptions.range);
    }
}

async function handleOpenAnalysisModal() {
    if (!AppState.lastSimVersionId || !AppState.lastSimJobId) {
        UIManager.showError("No completed simulation run found.");
        return;
    }

    UIManager.showAnalysisModal();
}

// This handler is now just for opening the modal
async function handleOpenReconstructionModal() {
    if (!AppState.lastSimVersionId || !AppState.lastSimJobId) {
        UIManager.showError("No completed simulation run found.");
        return;
    }

    UIManager.showLoading("Checking for LORs...");
    try {
        // Call the new API endpoint to check for the LOR file
        const result = await APIService.checkLorFile(AppState.lastSimVersionId, AppState.lastSimJobId);

        // Show the modal regardless of the outcome
        UIManager.showReconstructionModal();

        if (result.success && result.exists) {
            // LORs file was found!
            let details = [];
            if (result.energy_cut > 0) details.push(`E>${result.energy_cut}MeV`);
            if (result.energy_resolution > 0) details.push(`ERes:${result.energy_resolution}`);
            if (result.position_resolution) {
                const pr = result.position_resolution;
                if (pr.x > 0 || pr.y > 0 || pr.z > 0) details.push(`Smear:[${pr.x},${pr.y},${pr.z}]mm`);
            }

            let msg = `Found ${result.num_lors} LORs.`;
            if (details.length > 0) msg += ` (${details.join(', ')})`;

            UIManager.setLorStatus(msg, false);
            UIManager.setReconstructionButtonEnabled(true);
        } else {
            // LORs file was not found
            UIManager.setLorStatus("No LORs processed for this run. Click 'Process LORs' to begin.", false);
            UIManager.setReconstructionButtonEnabled(false);
        }
    } catch (error) {
        // If the API call fails, show an error and open the modal in a disabled state
        UIManager.showReconstructionModal();
        UIManager.setLorStatus(`Error checking for LOR file: ${error.message}`, true);
        UIManager.setReconstructionButtonEnabled(false);
    } finally {
        UIManager.hideLoading();
    }
}

// New handler for the "Process LORs" button
async function handleProcessLors(params) {
    if (!AppState.lastSimVersionId || !AppState.lastSimJobId) {
        UIManager.showError("Cannot process LORs: No simulation context.");
        return;
    }

    // Stop any previous poller
    if (AppState.lorStatusPoller) {
        clearInterval(AppState.lorStatusPoller);
    }

    UIManager.showLoading("Initializing LOR processing...");
    try {
        // This call will now return immediately with a 202 status
        await APIService.processLors(AppState.lastSimVersionId, AppState.lastSimJobId, params);

        // Start polling for progress
        AppState.lorStatusPoller = setInterval(pollLorStatus, 1000); // Poll every second

    } catch (error) {
        UIManager.showError("Failed to start LOR processing: " + error.message);
    } finally {
        UIManager.hideLoading();
    }
}

async function handleGenerateSensitivity(params) {
    if (!AppState.lastSimVersionId || !AppState.lastSimJobId) {
        UIManager.showError("Cannot generate sensitivity: No simulation context.");
        return;
    }

    const fullParams = {
        ...params,
        version_id: AppState.lastSimVersionId,
        job_id: AppState.lastSimJobId
    };

    UIManager.showLoading("Generating Sensitivity Matrix...");
    try {
        const result = await APIService.generateSensitivityMatrix(fullParams);
        if (result.success) {
            UIManager.setSensitivityStatus(true, null, false);
            UIManager.showNotification("Sensitivity Matrix Generated Successfully.");
        }
    } catch (error) {
        UIManager.showError("Failed to generate sensitivity matrix: " + error.message);
        UIManager.setSensitivityStatus(false, null, true);
    } finally {
        UIManager.hideLoading();
    }
}

// The reconstruction handler is now separate
async function handleRunReconstruction(reconParams) {
    if (!AppState.lastSimVersionId || !AppState.lastSimJobId) {
        UIManager.showError("Cannot run reconstruction: No simulation context.");
        return;
    }
    UIManager.showLoading("Running MLEM Reconstruction...");
    try {
        const result = await APIService.runReconstruction(AppState.lastSimVersionId, AppState.lastSimJobId, reconParams);
        AppState.currentReconShape = result.image_shape;

        const axis = document.getElementById('reconAxis').value;
        const voxelSize = reconParams.voxel_size;
        let aspectRatio = 1.0;
        if (axis === 'z') { // Axial slice (X vs Y)
            aspectRatio = (AppState.currentReconShape[0] * voxelSize[0]) / (AppState.currentReconShape[1] * voxelSize[1]);
        } else if (axis === 'y') { // Coronal slice (X vs Z)
            aspectRatio = (AppState.currentReconShape[0] * voxelSize[0]) / (AppState.currentReconShape[2] * voxelSize[2]);
        } else { // Sagittal slice (Y vs Z)
            aspectRatio = (AppState.currentReconShape[1] * voxelSize[1]) / (AppState.currentReconShape[2] * voxelSize[2]);
        }
        UIManager.setReconViewerAspectRatio(aspectRatio);

        const initialAxis = document.getElementById('reconAxis').value;
        UIManager.setupSliceSlider(initialAxis, AppState.currentReconShape);
        UIManager.showNotification(result.message);
    } catch (error) {
        UIManager.showError("Reconstruction failed: " + error.message);
    } finally {
        UIManager.hideLoading();
    }
}

function handleSliceSliderChange(axis, sliceNum) {
    if (!AppState.lastSimVersionId || !AppState.lastSimJobId || !AppState.currentReconShape) return;

    const maxSlice = (axis === 'x') ? AppState.currentReconShape[0] : (axis === 'y') ? AppState.currentReconShape[1] : AppState.currentReconShape[2];
    const imageUrl = APIService.getReconstructionSliceUrl(AppState.lastSimVersionId, AppState.lastSimJobId, axis, sliceNum);
    UIManager.updateReconstructionSlice(imageUrl, sliceNum, maxSlice);
}

function handleSliceAxisChange(newAxis) {
    if (!AppState.currentReconShape) return;
    UIManager.setupSliceSlider(newAxis, AppState.currentReconShape);
}

async function pollLorStatus() {
    if (!AppState.lastSimJobId) {
        clearInterval(AppState.lorStatusPoller);
        AppState.lorStatusPoller = null;
        return;
    }

    try {
        const result = await APIService.getLorStatus(AppState.lastSimJobId);
        if (result.success) {
            const status = result.status;
            if (status.status === "Processing coincidences...") {
                const percent = status.total > 0 ? ((status.progress / status.total) * 100).toFixed(1) : 0;
                UIManager.setLorStatus(`Processing... ${status.progress} / ${status.total} events (${percent}%)`, false);
            } else {
                UIManager.setLorStatus(status.message || status.status, status.status === 'Error');
            }

            if (status.status === 'Completed' || status.status === 'Error') {
                clearInterval(AppState.lorStatusPoller);
                AppState.lorStatusPoller = null;
                if (status.status === 'Completed') {
                    UIManager.setReconstructionButtonEnabled(true);
                }
            }
        }
    } catch (error) {
        console.error("LOR status polling error:", error);
        UIManager.setLorStatus(`Polling failed: ${error.message}`, true);
        clearInterval(AppState.lorStatusPoller);
        AppState.lorStatusPoller = null;
    }
}
/**
 * Fetches and displays the physics analysis for the currently loaded simulation run.
 * @param {number} energyBins 
 * @param {number} spatialBins 
 */
async function handleRefreshAnalysis(energyBins, spatialBins, sensitiveDetector = '') {
    if (!AppState.lastSimJobId || !AppState.lastSimVersionId) {
        UIManager.showError("No simulation run loaded to analyze.");
        return;
    }

    console.log(`Refreshing physics analysis for job ${AppState.lastSimJobId}...`);
    UIManager.setAnalysisStatus("Loading analysis data...");

    try {
        const result = await APIService.fetchSimulationAnalysis(
            AppState.lastSimVersionId,
            AppState.lastSimJobId,
            energyBins,
            spatialBins,
            sensitiveDetector
        );

        if (result.success) {
            UIManager.updateAnalysisCharts(result);
        } else {
            UIManager.showError("Failed to fetch analysis: " + result.error);
            UIManager.setAnalysisStatus("Error loading analysis data.");
        }
    } catch (error) {
        console.error("Analysis refresh failed:", error);
        UIManager.showError("An error occurred during analysis: " + error.message);
        UIManager.setAnalysisStatus("Error loading analysis data.");
    }
}

/**
 * Triggers a download of the raw HDF5 simulation results.
 */
async function handleDownloadSimData() {
    if (!AppState.lastSimJobId || !AppState.lastSimVersionId) {
        UIManager.showError("No simulation run loaded to download.");
        return;
    }

    const versionId = AppState.lastSimVersionId;
    const jobId = AppState.lastSimJobId;
    
    console.log(`Requesting download for run ${jobId}...`);
    
    // Create a temporary link to trigger the browser download
    const url = `/api/simulation/download/${versionId}/${jobId}`;
    try {
        const response = await fetch(url);
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || "Download failed");
        }
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `sim_${jobId.substring(0, 8)}_output.hdf5`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
        UIManager.showError("Download failed: " + error.message);
    }
}
