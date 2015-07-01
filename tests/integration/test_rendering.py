from tests.integration.base_test import BaseIntegrationTest


class TestRendering(BaseIntegrationTest):
    def test_example1(self):
        self.load_scenario("example_1.xml", load_immediately=True)

        import time
        time.sleep(10)
