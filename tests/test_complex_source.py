import unittest
import os
import sys
import tempfile

import pytest

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ProjectManager imports src.step_parser at module import time.
pytest.importorskip("OCC.Core.STEPControl")

from src.project_manager import ProjectManager, GeometryState, ParticleSource
from src.expression_evaluator import ExpressionEvaluator

class TestComplexSource(unittest.TestCase):
    def setUp(self):
        self.pm = ProjectManager(ExpressionEvaluator())
        self.pm.create_empty_project()
        
    def test_multiple_sources_macro(self):
        # Create two sources
        source1 = ParticleSource("Source1", gps_commands={"particle": "gamma", "energy": "511 keV"}, activity=1.0)
        source2 = ParticleSource("Source2", gps_commands={"particle": "e+", "energy": "1 MeV"}, activity=0.5)
        
        self.pm.current_geometry_state.add_source(source1)
        self.pm.current_geometry_state.add_source(source2)
        
        # Activate both
        self.pm.set_active_source(source1.id)
        self.pm.set_active_source(source2.id)
        
        # Generate macro
        with tempfile.TemporaryDirectory() as tmpdir:
            # generate_macro_file reads the saved project snapshot from version.json.
            with open(os.path.join(tmpdir, 'version.json'), 'w') as f:
                f.write(self.pm.save_project_to_json_string())

            macro_path = self.pm.generate_macro_file("test_job", {}, tmpdir, tmpdir, tmpdir)
            
            with open(macro_path, 'r') as f:
                content = f.read()
                
            print(content)
            
            # Verify content
            self.assertIn("/gps/source/intensity 0.6666666666666666", content)
            self.assertIn("/gps/source/add 0.3333333333333333", content)
            self.assertIn("# Source: Source1", content)
            self.assertIn("# Source: Source2", content)
            self.assertIn("/gps/particle gamma", content)
            self.assertIn("/gps/particle e+", content)

    def test_import_phantom(self):
        # Create a dummy phantom JSON with geometry and sources
        phantom_data = {
            "solids": {
                "phantom_box": {
                    "name": "phantom_box",
                    "type": "Box",
                    "params": {"x": 100, "y": 100, "z": 100}
                }
            },
            "sources": {
                "PhantomSource1": {
                    "id": "test-source-id",
                    "name": "PhantomSource1",
                    "gps_commands": {"particle": "gamma"},
                    "intensity": 2.0
                }
            },
            "active_source_ids": ["test-source-id"]
        }
        
        # Create GeometryState from the data and merge it
        phantom_state = GeometryState.from_dict(phantom_data)
        success, msg = self.pm.merge_from_state(phantom_state)
        self.assertTrue(success, msg)
        
        # Verify geometry was merged
        state = self.pm.current_geometry_state
        self.assertIn("phantom_box", state.solids)
        
        # Check source was merged
        source_found = False
        for s in state.sources.values():
            if s.name.startswith("PhantomSource1"):
                source_found = True
                self.assertEqual(s.activity, 2.0)
                # The source should be activated
                self.assertIn(s.id, state.active_source_ids)
                break
        self.assertTrue(source_found)

if __name__ == '__main__':
    unittest.main()
