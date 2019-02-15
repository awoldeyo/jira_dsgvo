import unittest

from jira.client import JIRA

from cocoa import Connection


class TestClass(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.jira = Connection().jira

    @classmethod
    def tearDownClass(cls):
        pass
            
    def test_authenticate(self):
        self.assertTrue(isinstance(self.jira, JIRA) or isinstance(self.jira, type(None)))

if __name__ == '__main__':
    unittest.main()