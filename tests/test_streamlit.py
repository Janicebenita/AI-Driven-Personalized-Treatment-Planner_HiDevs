import importlib.util
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec('streamlit'), 'Install Streamlit to run UI checks.')
class StreamlitFlowTests(unittest.TestCase):
    def test_initial_render_and_urgent_gate_then_profile_invalidation(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'streamlit_app.py')).run(timeout=45)
        self.assertEqual(len(app.exception), 0)
        app.checkbox(key='renal:acute').set_value(True).run()
        app.button[0].click().run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state['report']['status'], 'withheld')
        self.assertEqual(app.session_state['report']['options'], [])
        app.checkbox(key='renal:acute').set_value(False).run()
        self.assertEqual(len(app.exception), 0)
        with self.assertRaises(KeyError):
            app.session_state['report']


if __name__ == '__main__':
    unittest.main()
