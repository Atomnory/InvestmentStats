import os
import datetime
from django.test import TestCase
from config.settings import MEDIA_ROOT
from .graph import GraphPath
from .utils import get_today


class GraphPathTests(TestCase):
    def test_default_work(self):
        pk = 1
        graph_type = 'security'
        gp = GraphPath(pk, graph_type)
        self.assertEqual(gp.graph_path, os.path.join('portfolio_graph', str(pk), f'{graph_type}_pie.png'))
        self.assertEqual(gp.graph_full_root, os.path.join(MEDIA_ROOT, 'portfolio_graph', str(pk)))
        self.assertEqual(gp.graph_full_path, os.path.join(MEDIA_ROOT, 'portfolio_graph', str(pk), f'{graph_type}_pie.png'))

    def test_mixed_arguments(self):
        pk = 'country'
        graph_type = 2
        gp = GraphPath(pk, graph_type)
        self.assertEqual(gp.graph_path, os.path.join('portfolio_graph', pk, f'{str(graph_type)}_pie.png'))
        self.assertEqual(gp.graph_full_root, os.path.join(MEDIA_ROOT, 'portfolio_graph', pk))
        self.assertEqual(gp.graph_full_path, os.path.join(MEDIA_ROOT, 'portfolio_graph', pk, f'{str(graph_type)}_pie.png'))


class UtilsGetTodayTests(TestCase):
    def test_equal_utc_time(self):
        t = get_today()
        self.assertIsInstance(t, datetime.date)
        self.assertEqual(t, datetime.datetime.utcnow().date())
