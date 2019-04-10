import unittest

from upload_issues import UploadIssues, get_issues
from cocoa import Connection

@unittest.skip("Skipping TestClass_1")
class TestClass_1(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        testfile = '/Users/lilitkhurshudyan/Documents/12_Projects/VW/JIRA/__uploads__/test_upload/DAML_only_missing_test.xlsm'
        cls.up = UploadIssues(filename=testfile)
        cls.up.createUploadDictDAML()
        cls.up.postDAML()
        cls.up.addCommentDAML() 
        cls.up.changeStatusDAML()

    @classmethod
    def tearDownClass(cls):
        jira = Connection(True).jira
        my_issues = 'creator = currentUser() AND created >= -5m ORDER BY updated DESC'
        issues = jira.search_issues(my_issues)
        _ = [i.delete() for i in issues]
    
    def test_uploadsuccess(self):
        self.assertEqual(self.up.df.shape, (4,39))
        
    def test_uploadincorrect(self):
        self.assertEqual(self.up.incorrect_df.shape, (0, 33))
    
    def test_uploadincomplete(self):
        self.assertEqual(self.up.incomplete_df.shape, (13, 36))
        
class TestClass_2(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        testfile = '/Users/lilitkhurshudyan/Documents/12_Projects/VW/JIRA/__uploads__/test_upload/DAML_DC_all_complete.xlsm'
        cls.up = UploadIssues(filename=testfile)
        cls.up.createUploadDictDAML()
        cls.up.postDAML()
        cls.up.addCommentDAML() 
        cls.up.changeStatusDAML()
        cls.up.createUploadDictDC() 
        cls.up.postDC()
        cls.up.addCommentDC()
        cls.up.changeStatusDC()
        cls.up.linkDAML_DC()

    @classmethod
    def tearDownClass(cls):
        jira = Connection(True).jira
        my_issues = 'creator = currentUser() AND created >= -5m ORDER BY updated DESC'
        issues = jira.search_issues(my_issues)
        _ = [i.delete() for i in issues]
    
    def test_uploadsuccess(self):
        self.assertEqual(self.up.df.shape, (18,39))
        
    def test_uploadincorrect(self):
        self.assertEqual(self.up.incorrect_df.shape, (0, 33))
    
    def test_uploadincomplete(self):
        self.assertEqual(self.up.incomplete_df.shape, (0, 36))

    
if __name__ == '__main__':
    unittest.main()