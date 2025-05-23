

[ ] - Add admin role check to /users endpoint.
[ ] - /users get endpoint is simulating returns from local 
[ ] - Admin role check needs to be implemented for user management endpoints
[ ] - User listing endpoint currently uses test data (needs to be connected to actual storage)
[ ] - Email sender configuration needs to be reviewed
[ ] - Authorization checks needed for user operations (admin or self)
[ ] - History of tasks needs to be implemented
[ ] - Redis Keys are stored in a sorted set. Whenever we run keys() it returns the full set. This won't scale. We need to implement a pagination system or limit per user.
[ ] - tests are returned for all users. limit per user.
[ ] - user validation for tests, executions, etc.
[ ] - only draft tests can be changed or deleted. 
[ ] - copy test to draft.
[ ] - security around the test init. Server side, how to ensure the requester is also the owner of the target chatbot, else it's a security exploit (ddos etc). On the browser, handle CORS. Handle logins. 

- add test for "/users/{user_id}"
- add test for "/users/email/{email}"

- fix this error:
    2025-05-23 17:01:47 grc_api-1  | 2025-05-23 07:01:47,334 ERROR [AI_GRC_API error] Error retrieving user 593e1930-14d9-499a-97dd-f924ff9b0fd1: 1 validation error for UserResponse
    2025-05-23 17:01:47 grc_api-1  |   Input should be a valid dictionary or instance of UserResponse [type=model_type, input_value=UserInDB(id=UUID('593e193...et_code_expires_at=None), input_type=UserInDB]
    2025-05-23 17:01:47 grc_api-1  |     For further information visit https://errors.pydantic.dev/2.4/v/model_type
    2025-05-23 17:01:47 grc_api-1  | 2025-05-23 07:01:47,335 ERROR [AI_GRC_API error] rid=9b30f2a3-4272-40dc-a0cd-b98f812f399e error response: {"detail":"Error retrieving user"}