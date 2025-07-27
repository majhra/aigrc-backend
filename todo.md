

[x] - /users endpoint inclides password and verification code. Redact
[x] - /users get endpoint is simulating returns from local 
[x] - User listing endpoint currently uses test data (needs to be connected to actual storage)
[x] - Add admin role check to /users endpoint.
[x] - Admin role check needs to be implemented for user management endpoints
[x] - Authorization checks needed for user operations (admin or self)
[x] - Validate user lookup has access to view user details
[x] - tests are returned for all users. limit per user.
[ ] - Email sender configuration needs to be reviewed
[ ] - History of tasks needs to be implemented
[ ] - Redis Keys are stored in a sorted set. Whenever we run keys() it returns the full set. This won't scale. We need to implement a pagination system or limit per user.
[ ] - user validation for tests, executions, etc.
[ ] - only draft tests can be changed or deleted. 
[ ] - copy test to draft.
[ ] - security around the test init. Server side, how to ensure the requester is also the owner of the target chatbot, else it's a security exploit (ddos etc). On the browser, handle CORS. Handle logins. 
[ ] - Add updated test sets from NIST AI Risk Management Framework, OECD AI Principles, GDPR, CCPA/CPRA , NYDFS Cybersecurity Regulation , OCC/FDIC/FFIEC Guidelines , SOX & COSO Frameworks, NIST SP 800-53 / SP 800-161, other standard tests?
[ ] - Password reset return malformed data 400 on password resets on invalid email. 
[ ] - user group CRUD.
[ ] - admin group membership

[ ] - add user id to all backend logs to track who does what. 
[x] - GET /api/v1.0/prompts/?page=1&limit=50&status=ACTIVE&search=tes doesn't seem to respond with valid data. is it because we're searching name rather than uuid? 
[ ] - Select Prompt from Library 'GET /api/v1.0/prompts/?page=1&limit=100&category_type=SAFETY&status=ACTIVE' fails for categoty_type
[ ] - The tests themselves have limited connection stored compared with the AI emdpoint config. Update!

[ ] - investigate handling other things than llm results - marketing images, emails etc etc
[ ] - change system to handle async database queries to better handle load
[ ] - database config and password needs to be in .env. 
[ ] - if not group_filter: group_filter = "default" # might filter out all groups for admin. we want admin to see all groups so leave it as None or blank.
