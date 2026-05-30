import test from 'node:test';
import assert from 'node:assert/strict';

import {
    VISUAL_SELF_CRITIQUE_DEFAULT_CAPTURE_OPTIONS,
    VISUAL_SELF_CRITIQUE_SOURCE_LABEL,
    buildAutomaticVisualSelfCritiqueDisplayMessage,
    buildAutomaticVisualSelfCritiqueGoal,
    buildVisualSelfCritiqueDisplayMessage,
    buildVisualSelfCritiqueMetadata,
    buildVisualSelfCritiquePrompt,
} from '../../static/visualSelfCritique.js';

test('visual self-critique metadata strips image data while preserving view attachments', () => {
    const packet = {
        kind: 'airpet.visual_verification_packet',
        schema_version: 1,
        scene_summary: { component_count: 2 },
        views: [
            {
                name: 'front',
                label: 'Front view',
                description: 'front',
                image: {
                    mime_type: 'image/png',
                    width: 320,
                    height: 240,
                    data_url: 'data:image/png;base64,abc123',
                },
                camera: { fov_deg: 50 },
            },
        ],
    };
    const metadata = buildVisualSelfCritiqueMetadata(packet, [
        {
            artifact_id: 'artifact-front',
            original_filename: 'airpet_visual_verification_front.png',
            mime_type: 'image/png',
            visual_verification_view: 'front',
        },
    ]);

    assert.equal(metadata.kind, 'airpet.visual_verification_packet');
    assert.equal(metadata.views.length, 1);
    assert.equal(metadata.views[0].attached_artifact_id, 'artifact-front');
    assert.equal(metadata.views[0].attached_filename, 'airpet_visual_verification_front.png');
    assert.equal(metadata.views[0].image.width, 320);
    assert.equal(metadata.views[0].image.data_url, undefined);
});

test('visual self-critique prompt asks for critique, metadata evidence, and tool repairs', () => {
    const prompt = buildVisualSelfCritiquePrompt({
        userGoal: 'Check whether the silicon tiles are aligned.',
        packetMetadata: {
            scene_summary: { component_count: 12 },
            views: [{ name: 'top', attached_artifact_id: 'artifact-top' }],
        },
    });

    assert.match(prompt, /VISUAL SELF-CRITIQUE AND REPAIR REQUEST/);
    assert.match(prompt, /silicon tiles are aligned/);
    assert.match(prompt, /use the available AIRPET tools/i);
    assert.match(prompt, /Do not run a Geant4 simulation/i);
    assert.match(prompt, /"component_count": 12/);
});

test('manual visual self-critique prompt can run as critique-only without tools', () => {
    const prompt = buildVisualSelfCritiquePrompt({
        userGoal: 'Look for visible detector alignment problems.',
        allowRepairs: false,
        packetMetadata: {
            scene_summary: { component_count: 4 },
            views: [{ name: 'front', attached_artifact_id: 'artifact-front' }],
        },
    });

    assert.match(prompt, /critique-only visual check/i);
    assert.match(prompt, /do not call AIRPET tools/i);
    assert.match(prompt, /recommended repair steps/i);
});

test('visual self-critique defaults capture four canonical views', () => {
    assert.deepEqual(
        [...VISUAL_SELF_CRITIQUE_DEFAULT_CAPTURE_OPTIONS.views],
        ['front', 'side', 'top', 'isometric'],
    );
    assert.equal(VISUAL_SELF_CRITIQUE_SOURCE_LABEL, 'visual-verification-self-critique');
    assert.equal(
        buildVisualSelfCritiqueDisplayMessage('  Please check the beam line.  '),
        'Visual self-critique request:\n\nPlease check the beam line.',
    );
});

test('automatic visual self-critique goal preserves user intent and unique tool names', () => {
    const goal = buildAutomaticVisualSelfCritiqueGoal({
        originalUserMessage: 'Build a four-panel silicon telescope.',
        toolsUsed: ['batch_geometry_update', 'batch_geometry_update', 'configure_incident_beam'],
    });

    assert.match(goal, /automatic visual verification checkpoint/i);
    assert.match(goal, /Build a four-panel silicon telescope/);
    assert.match(goal, /batch_geometry_update, configure_incident_beam/);
    assert.match(goal, /do not make unnecessary edits/i);
    assert.equal(
        buildAutomaticVisualSelfCritiqueDisplayMessage('Build a four-panel silicon telescope.'),
        'Automatic visual check after AI edits:\n\nBuild a four-panel silicon telescope.',
    );
});
