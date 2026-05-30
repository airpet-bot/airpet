// static/visualSelfCritique.js

export const VISUAL_SELF_CRITIQUE_SOURCE_LABEL = 'visual-verification-self-critique';

export const VISUAL_SELF_CRITIQUE_DEFAULT_CAPTURE_OPTIONS = Object.freeze({
    views: Object.freeze(['front', 'side', 'top', 'isometric']),
    image_width: 768,
    image_height: 576,
    include_grid: true,
    include_axes: true,
});

const AUTO_VISUAL_SELF_CRITIQUE_GOAL = `This is an automatic visual verification checkpoint after AIRPET AI modified the detector.

Compare the current screenshots and metadata against the user's latest construction intent. Repair only high-confidence issues that are visible or clearly contradicted by metadata. If the current detector already looks consistent, say so and do not make unnecessary edits.`;

function cloneJson(value) {
    return JSON.parse(JSON.stringify(value ?? null));
}

function asArray(value) {
    return Array.isArray(value) ? value : [];
}

export function buildVisualSelfCritiqueDisplayMessage(userGoal = '') {
    const goal = String(userGoal || '').trim();
    return goal
        ? `Visual self-critique request:\n\n${goal}`
        : 'Visual self-critique request for the current AIRPET detector.';
}

export function buildAutomaticVisualSelfCritiqueGoal({
    originalUserMessage = '',
    toolsUsed = [],
} = {}) {
    const userMessage = String(originalUserMessage || '').trim();
    const uniqueTools = [...new Set(asArray(toolsUsed).map((tool) => String(tool || '').trim()).filter(Boolean))];
    const lines = [AUTO_VISUAL_SELF_CRITIQUE_GOAL];

    if (userMessage) {
        lines.push('', 'Original user construction request:', userMessage);
    }

    if (uniqueTools.length > 0) {
        lines.push('', `AIRPET tools used before this checkpoint: ${uniqueTools.join(', ')}`);
    }

    return lines.join('\n');
}

export function buildAutomaticVisualSelfCritiqueDisplayMessage(originalUserMessage = '') {
    const userMessage = String(originalUserMessage || '').trim();
    return userMessage
        ? `Automatic visual check after AI edits:\n\n${userMessage}`
        : 'Automatic visual check after AI edits.';
}

export function buildVisualSelfCritiqueMetadata(packet, uploadedArtifacts = []) {
    const metadata = cloneJson(packet) || {};
    const artifactsByView = new Map();

    asArray(uploadedArtifacts).forEach((artifact) => {
        const viewName = artifact?.visual_verification_view || artifact?.view_name;
        if (viewName) artifactsByView.set(viewName, artifact);
    });

    metadata.views = asArray(metadata.views).map((view) => {
        const artifact = artifactsByView.get(view?.name) || {};
        const image = view?.image || {};
        return {
            name: view?.name || null,
            label: view?.label || null,
            description: view?.description || null,
            attached_artifact_id: artifact.artifact_id || null,
            attached_filename: artifact.original_filename || artifact.filename || null,
            image: {
                mime_type: image.mime_type || artifact.mime_type || 'image/png',
                width: image.width || null,
                height: image.height || null,
            },
            camera: view?.camera || null,
            scene_bounds_mm: view?.scene_bounds_mm || null,
        };
    });

    return metadata;
}

export function buildVisualSelfCritiquePrompt({
    packetMetadata,
    userGoal = '',
    allowRepairs = true,
} = {}) {
    const displayGoal = String(userGoal || '').trim() || 'No extra user goal was provided; inspect the current detector state.';
    const metadataJson = JSON.stringify(packetMetadata || {}, null, 2);
    const repairInstruction = allowRepairs
        ? 'If you find high-confidence issues that can be repaired in AIRPET, use the available AIRPET tools to inspect and then repair them. Do not hand-wave with pseudo-code.'
        : 'This is a critique-only visual check: do not call AIRPET tools or modify the detector. If you find high-confidence issues, describe the exact object IDs, evidence, and recommended repair steps so the user can choose whether to apply them.';
    const requestTitle = allowRepairs
        ? 'VISUAL SELF-CRITIQUE AND REPAIR REQUEST'
        : 'VISUAL SELF-CRITIQUE REQUEST';

    return `${requestTitle}

You have been given AIRPET visual verification screenshots as image attachments plus structured geometry/simulation metadata below.

User goal or concern:
${displayGoal}

Instructions:
1. Compare all attached views together with the structured metadata. Do not rely on a single screenshot.
2. Check geometry alignment, missing or duplicated parts, scale, rotations, overlaps that are visually apparent, material assignments, sensitive detector flags, sources, scoring, fields, and CAD/procedural-generator annotations.
3. ${repairInstruction}
4. Do not run a Geant4 simulation unless the user explicitly asked for a simulation run.
5. If the screenshots are ambiguous, say exactly what is ambiguous and avoid destructive edits.
6. In your final response, summarize: visual evidence, metadata evidence, repairs performed, and remaining uncertainty.

Structured visual verification metadata JSON:
\`\`\`json
${metadataJson}
\`\`\``;
}
