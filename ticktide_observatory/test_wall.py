"""Regression checks for advancing runs and scenario-specific wall preparation."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).with_name('app.py')

class WallNavigationTests(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_file(str(APP),default_timeout=60).run()
        self.assert_clean()

    def assert_clean(self):
        self.assertEqual([e.message for e in self.at.exception],[])

    def run_wall(self):
        next(b for b in self.at.button if b.key=='run_wall').click().run()
        self.assert_clean()

    def select(self,label,value):
        widgets=self.at.radio if label=='Placement scenario' else self.at.selectbox
        next(s for s in widgets if s.label==label).set_value(value).run()
        self.assert_clean()

    def test_repeated_run_advances(self):
        self.run_wall()
        self.assertEqual(self.at.session_state['selected_run_id'],1)
        self.run_wall()
        self.assertEqual(self.at.session_state['selected_run_id'],2)
        self.assertTrue(self.at.session_state['wall_started'])
        self.run_wall()
        self.assertEqual(self.at.session_state['selected_run_id'],3)

    def test_filtered_path_wraps(self):
        self.select('Recorded strategy path','Recovery')
        selector=next(s for s in self.at.selectbox if s.label=='Execution / Run ID')
        first,last=selector.value,int(selector.options[-1])
        self.select('Execution / Run ID',last)
        self.run_wall()
        self.assertEqual(self.at.session_state['selected_run_id'],last)
        self.run_wall()
        self.assertEqual(self.at.session_state['selected_run_id'],first)

    def test_scenarios_reset_then_launch(self):
        for scenario in ['baseline','ingress_only','latency_only','latency_path','capacity_stress','combined']:
            self.select('Placement scenario',scenario)
            self.run_wall()
            self.assertTrue(self.at.session_state['wall_started'])

    def test_effective_capacity_and_hosting_evidence(self):
        import json
        from wall import prepare_wall
        root=APP.parents[1]
        with (root/'TickTide/outputs/n1000_seed42/execution_service_graphs.jsonl').open() as f:
            graph=json.loads(next(f))
        for scenario in ['baseline','combined']:
            path=next((root/'results_multiseed/seed_42'/scenario).glob('group_001*/placement_result.json'))
            result=json.loads(path.read_text())
            data=prepare_wall(str(root),graph,result,scenario)
            sites={site['id']:site for site in data['site_evidence']}
            self.assertTrue(data['audit']['pass'])
            self.assertIn('bandwidth',data)
            self.assertNotIn('comparison',data)
            if scenario=='combined':
                self.assertEqual(sites['core']['block_limit'],600)
                self.assertIn('F1',sites['edge1']['services'])
                self.assertGreater(len(sites['core']['services']),0)
                self.assertLessEqual(sites['core']['ram_used'],sites['core']['ram_limit'])
            else:
                self.assertEqual(set(sites['core']['services']),set(graph['service_nodes']))

if __name__=='__main__':
    unittest.main()
