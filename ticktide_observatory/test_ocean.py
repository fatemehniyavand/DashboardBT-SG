"""Ocean/V1 separation, scenario playback, and template/data isolation."""
import sys
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from ocean_theme import ocean_markup

class OceanEditionTests(unittest.TestCase):
    def test_palette_transforms_template_before_data(self):
        template='<html><head></head><body><div class="logo"><span>∿</span> tick wave</div><p style="color:#60e7c6">Gold = actual selected host</p><script>const D=__DATA__</script></body></html>'
        result=ocean_markup(template)
        self.assertIn('__DATA__',result)
        self.assertIn('Violet = actual selected host',result)
        self.assertIn('data:image/svg+xml;base64,',result)
        self.assertNotIn('#60e7c6',result)

    def test_ocean_entry_run_and_scenarios(self):
        app=AppTest.from_file(str(HERE.parent/'streamlit_app_v2.py'),default_timeout=60).run()
        self.assertEqual([e.message for e in app.exception],[])
        self.assertEqual(app.session_state['_tick_wave_edition'],'ocean')
        for scenario in ['baseline','ingress_only','latency_only','latency_path','capacity_stress','combined']:
            next(r for r in app.radio if r.label=='Placement scenario').set_value(scenario).run()
            next(b for b in app.button if b.key=='run_wall').click().run()
            self.assertEqual([e.message for e in app.exception],[])
            self.assertTrue(app.session_state['wall_started'])
        selected=app.session_state['selected_run_id']
        next(b for b in app.button if b.key=='run_wall').click().run()
        self.assertEqual(app.session_state['selected_run_id'],selected+1)
        classic=AppTest.from_file(str(HERE/'app.py'),default_timeout=60).run()
        self.assertEqual(classic.session_state['_tick_wave_edition'],'classic')
        self.assertEqual([e.message for e in classic.exception],[])

if __name__=='__main__':unittest.main()
