import test from 'node:test';
import assert from 'node:assert/strict';

import {
    getNormalizedGpsDirectionVector,
    normalizeGpsAngularType,
    parseGpsDirectionVector,
    isDirectedGpsAngularType,
    isIsotropicGpsAngularType,
} from '../../static/gpsAngularMode.js';

test('normalizeGpsAngularType accepts friendly and Geant4 angular mode names', () => {
    assert.equal(normalizeGpsAngularType('Direction'), 'beam1d');
    assert.equal(normalizeGpsAngularType('beam1d'), 'beam1d');
    assert.equal(normalizeGpsAngularType('directed'), 'beam1d');
    assert.equal(normalizeGpsAngularType('Isotropic'), 'iso');
    assert.equal(normalizeGpsAngularType('iso'), 'iso');
});

test('directed and isotropic helpers remain stable across canonical and alias values', () => {
    assert.equal(isDirectedGpsAngularType('Direction'), true);
    assert.equal(isDirectedGpsAngularType('beam1d'), true);
    assert.equal(isDirectedGpsAngularType('Isotropic'), false);

    assert.equal(isIsotropicGpsAngularType('Isotropic'), true);
    assert.equal(isIsotropicGpsAngularType('iso'), true);
    assert.equal(isIsotropicGpsAngularType('beam1d'), false);
});

test('direction-vector helpers parse triples and normalize them for display', () => {
    assert.deepEqual(parseGpsDirectionVector('0 0 1'), { x: '0', y: '0', z: '1' });
    assert.deepEqual(parseGpsDirectionVector('1, 2, 3'), { x: '1', y: '2', z: '3' });
    assert.deepEqual(getNormalizedGpsDirectionVector('0 0 0'), { x: 0, y: 0, z: 1 });

    const normed = getNormalizedGpsDirectionVector('0 3 4');
    assert.ok(Math.abs(normed.x - 0) < 1e-12);
    assert.ok(Math.abs(normed.y - 0.6) < 1e-12);
    assert.ok(Math.abs(normed.z - 0.8) < 1e-12);
});
