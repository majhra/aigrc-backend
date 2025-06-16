

[x] - /users endpoint inclides password and verification code. Redact
[x] - /users get endpoint is simulating returns from local 
[x] - User listing endpoint currently uses test data (needs to be connected to actual storage)
[x] - Add admin role check to /users endpoint.
[x] - Admin role check needs to be implemented for user management endpoints
[ ] - Email sender configuration needs to be reviewed
[ ] - Authorization checks needed for user operations (admin or self)
[ ] - History of tasks needs to be implemented
[ ] - Redis Keys are stored in a sorted set. Whenever we run keys() it returns the full set. This won't scale. We need to implement a pagination system or limit per user.
[ ] - tests are returned for all users. limit per user.
[ ] - user validation for tests, executions, etc.
[ ] - only draft tests can be changed or deleted. 
[ ] - copy test to draft.
[ ] - security around the test init. Server side, how to ensure the requester is also the owner of the target chatbot, else it's a security exploit (ddos etc). On the browser, handle CORS. Handle logins. 
[ ] - Validate user lookup has access to view user details
