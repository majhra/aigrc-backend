import sys
sys.path.insert(0, '/workspace')

# Test the AITestSchema validation directly
test_data = {
    'id': '299a92b5-7ba7-442a-95ce-2846143277c4', 
    'name': 'test1', 
    'description': 'Test1', 
    'prompt_template': 'This is the testiest test prompt you could ever test', 
    'interface_type': 'DIRECT_LLM', 
    'connection_config': {
        'endpoint': 'http://backend-grc_api-1:80/api/v1.0/simulation/v1/chat/completions', 
        'auth_type': 'API_KEY', 
        'auth_string': 'Bearer 12345', 
        'timeout': 30
    }, 
    'validation_config': {
        'validator_type': 'HUMAN', 
        'validation_criteria': []
    }, 
    'tags': [], 
    'risk_level': 'LOW', 
    'status': 'ACTIVE', 
    'created_by': '4bcf6001-e0c3-42c2-b673-76af4193d962', 
    'group_id': '29f46b82-293d-4074-bc99-2e6d1e8acbcc', 
    'created_at': '2025-07-26T08:52:54.441506+00:00', 
    'updated_at': '2025-07-26T08:52:54.441506+00:00', 
    'latest_execution_id': ''
}

try:
    from app.schemas.tests import AITestSchema
    
    print("Testing AITestSchema validation...")
    test_schema = AITestSchema(**test_data)
    print("✅ Schema validation successful!")
    print(f"Test name: {test_schema.name}")
    print(f"Test group_id: {test_schema.group_id}")
    
except Exception as e:
    print(f"❌ Schema validation failed: {e}")
    print(f"Error type: {type(e)}")
    
    # Try to identify which field is causing the issue
    import traceback
    traceback.print_exc()