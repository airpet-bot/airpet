import assert from 'node:assert/strict';
import test from 'node:test';

import {
    LEFT_PANEL_DEFAULT_WIDTH,
    clampLeftPanelWidth,
    getLeftPanelWidthBounds,
    normalizeStoredPanelWidth,
} from '../../static/panelLayout.js';


test('left panel width stays within desktop workspace bounds', () => {
    assert.deepEqual(getLeftPanelWidthBounds(1440), {
        min: 260,
        max: 720,
    });
    assert.equal(clampLeftPanelWidth(100, 1440), 260);
    assert.equal(clampLeftPanelWidth(480, 1440), 480);
    assert.equal(clampLeftPanelWidth(900, 1440), 720);
});

test('left panel yields space to the viewer on narrow windows', () => {
    assert.deepEqual(getLeftPanelWidthBounds(600), {
        min: 232,
        max: 232,
    });
    assert.equal(clampLeftPanelWidth(350, 600), 232);
});

test('stored left panel widths fall back safely', () => {
    assert.equal(normalizeStoredPanelWidth('425'), 425);
    assert.equal(normalizeStoredPanelWidth('not-a-width'), LEFT_PANEL_DEFAULT_WIDTH);
    assert.equal(normalizeStoredPanelWidth('-20'), LEFT_PANEL_DEFAULT_WIDTH);
});
