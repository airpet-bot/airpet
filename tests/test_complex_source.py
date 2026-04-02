import unittest
import os
import sys
import json
import tempfile
from io import BytesIO

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock src.step_parser to avoid OCC dependency
from unittest.mock import MagicMock
sys.modules['src.step_parser'] = MagicMock()

from src.project_manager import ProjectManager, GeometryState, ParticleSource

class TestComplexSource(unittest.TestCase):
    def setUp(self):
        mock_evaluator = MagicMock()
        self.pm = ProjectManager(mock_evaluator)
        self.pm.create_empty_project()
        
    def test_multiple_sources_macro(self):
        # Create two sources
        source1 = ParticleSource("Source1", gps_commands={"particle": "gamma", "energy": "511 keV"}, intensity=1.0)
        source2 = ParticleSource("Source2", gps_commands={"particle": "e+", "energy": "1 MeV"}, intensity=0.5)
        
        self.pm.current_geometry_state.add_source(source1)
        self.pm.current_geometry_state.add_source(source2)
        
        # Activate both
        self.pm.set_active_source(source1.id)
        self.pm.set_active_source(source2.id)
        
        # Generate macro
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dummy version.json
            with open(os.path.join(tmpdir, 'version.json'), 'w') as f:
                json.dump({"version": "1.0"}, f)

            macro_path = self.pm.generate_macro_file("test_job", {}, tmpdir, tmpdir, tmpdir)
            
            with open(macro_path, 'r') as f:
                content = f.read()
                
            print(content)
            
            # Verify content
            self.assertIn("/gps/source/intensity 1.0", content)
            self.assertIn("/gps/source/add 0.5", content)
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
                self.assertEqual(s.intensity, 2.0)
                # The source should be activated
                self.assertIn(s.id, state.active_source_ids)
                break
        self.assertTrue(source_found)

if __name__ == '__main__':
    unittest.main()
