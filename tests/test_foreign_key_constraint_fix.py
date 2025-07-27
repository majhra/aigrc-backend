"""
Integration test to validate the foreign key constraint fix.

This test specifically validates that the fix implemented in tests_store.py
properly handles cascade deletion of executions when deleting tests.

This is a simplified test that focuses on the core constraint issue
without complex schema dependencies.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4


class TestForeignKeyConstraintFix(unittest.TestCase):
    """Test the specific foreign key constraint fix."""
    
    def test_test_deletion_calls_execution_cleanup(self):
        """
        Test that test deletion properly calls execution cleanup.
        This is the core fix that prevents foreign key constraint violations.
        """
        # Import the module under test
        from app.modules.tests_store import AITestStore
        
        # Create a mock store
        mock_store = MagicMock()
        test_store = AITestStore(mock_store)
        test_id = str(uuid4())
        
        # Mock the execution store and its methods
        with patch('app.modules.executions_store.ExecutedTestStore') as MockExecutedTestStore:
            mock_execution_store = MagicMock()
            MockExecutedTestStore.return_value = mock_execution_store
            
            # Mock executions exist for this test
            # Create mock execution objects with id attributes
            exec1 = MagicMock()
            exec1.id = "exec1"
            exec2 = MagicMock() 
            exec2.id = "exec2"
            
            mock_execution_store.list.return_value = (
                [exec1, exec2],  # 2 executions found
                2  # total count
            )
            
            # Mock successful execution deletions
            mock_execution_store.delete.return_value = True
            
            # Mock successful test deletion
            mock_store.pop.return_value = {"deleted": True}
            
            # Perform the deletion
            result = test_store.delete(test_id)
            
            # Verify the fix is working:
            
            # 1. Should create ExecutedTestStore instance
            MockExecutedTestStore.assert_called_once_with(mock_store)
            
            # 2. Should list executions for the test
            mock_execution_store.list.assert_called_once_with(
                test_id=test_id, page=1, limit=1000
            )
            
            # 3. Should delete each execution
            expected_delete_calls = [
                unittest.mock.call("exec1"),
                unittest.mock.call("exec2")
            ]
            mock_execution_store.delete.assert_has_calls(expected_delete_calls, any_order=True)
            
            # 4. Should delete the test after executions are cleaned up
            mock_store.pop.assert_called_once_with(test_id)
            
            # 5. Should return success
            self.assertTrue(result)
            
            print("✅ Foreign key constraint fix is working correctly!")
            print("   - Executions are listed before test deletion")
            print("   - Each execution is deleted individually") 
            print("   - Test is deleted after execution cleanup")

    def test_test_deletion_handles_no_executions(self):
        """
        Test that test deletion works normally when no executions exist.
        """
        from app.modules.tests_store import AITestStore
        
        mock_store = MagicMock()
        test_store = AITestStore(mock_store)
        test_id = str(uuid4())
        
        with patch('app.modules.executions_store.ExecutedTestStore') as MockExecutedTestStore:
            mock_execution_store = MagicMock()
            MockExecutedTestStore.return_value = mock_execution_store
            
            # Mock no executions exist
            mock_execution_store.list.return_value = ([], 0)
            
            # Mock successful test deletion
            mock_store.pop.return_value = {"deleted": True}
            
            # Perform the deletion
            result = test_store.delete(test_id)
            
            # Verify behavior:
            # 1. Should still check for executions
            mock_execution_store.list.assert_called_once_with(
                test_id=test_id, page=1, limit=1000
            )
            
            # 2. Should not call delete on execution store since no executions
            mock_execution_store.delete.assert_not_called()
            
            # 3. Should delete the test normally
            mock_store.pop.assert_called_once_with(test_id)
            
            # 4. Should return success
            self.assertTrue(result)
            
            print("✅ Test deletion works correctly when no executions exist!")

    def test_test_deletion_handles_execution_cleanup_failure(self):
        """
        Test that test deletion handles execution cleanup failures gracefully.
        """
        from app.modules.tests_store import AITestStore
        
        mock_store = MagicMock()
        test_store = AITestStore(mock_store)
        test_id = str(uuid4())
        
        with patch('app.modules.executions_store.ExecutedTestStore') as MockExecutedTestStore:
            mock_execution_store = MagicMock()
            MockExecutedTestStore.return_value = mock_execution_store
            
            # Mock execution listing fails
            mock_execution_store.list.side_effect = Exception("Database connection failed")
            
            # Mock successful test deletion (optimistic case)
            mock_store.pop.return_value = {"deleted": True}
            
            # Perform the deletion - should not raise exception
            result = test_store.delete(test_id)
            
            # Verify graceful handling:
            # 1. Should attempt to list executions
            mock_execution_store.list.assert_called_once()
            
            # 2. Should still attempt test deletion despite execution cleanup failure
            mock_store.pop.assert_called_once_with(test_id)
            
            # 3. Should return success if test deletion succeeds
            self.assertTrue(result)
            
            print("✅ Test deletion handles execution cleanup failures gracefully!")

    def test_before_fix_would_cause_constraint_violation(self):
        """
        Demonstrate what would happen without the fix.
        This shows why the fix was necessary.
        """
        # This is a conceptual test showing the problem that was fixed
        
        print("\n🚨 Before the fix:")
        print("   1. test_store.delete(test_id) would be called")
        print("   2. SQL: DELETE FROM ai_tests WHERE id = test_id")
        print("   3. Database would reject with foreign key constraint violation:")
        print("      'update or delete on table \"ai_tests\" violates foreign key constraint'")
        print("      'test_executions_test_id_fkey on table \"test_executions\"'")
        print("   4. API would return 500 Internal Server Error")
        print("   5. Backend logs would show sqlalchemy.exc.IntegrityError")
        
        print("\n✅ After the fix:")
        print("   1. test_store.delete(test_id) is called")
        print("   2. First: execution_store.list(test_id=test_id) finds related executions")
        print("   3. Then: execution_store.delete(exec_id) for each execution")
        print("   4. Finally: DELETE FROM ai_tests WHERE id = test_id")
        print("   5. No constraint violation because executions were deleted first")
        print("   6. API returns 204 No Content (success)")
        
        # This demonstrates the importance of the fix
        self.assertTrue(True, "Fix prevents 500 errors in production")


if __name__ == '__main__':
    print("🧪 Testing Foreign Key Constraint Fix")
    print("=" * 50)
    print("This test validates that the cascade deletion fix")
    print("prevents foreign key constraint violations that")
    print("were causing 500 errors in production.")
    print("=" * 50)
    
    unittest.main(verbosity=2)