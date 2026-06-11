import assert from 'node:assert/strict';
import test from 'node:test';

import { halfLengthFromGdmlFullLength } from '../../static/primitiveDimensions.js';

test('GDML full lengths convert to renderer half lengths exactly once', () => {
    assert.equal(halfLengthFromGdmlFullLength(100), 50);
    assert.equal(halfLengthFromGdmlFullLength(7.5), 3.75);
});
