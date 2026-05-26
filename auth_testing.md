# Auth-Gated App Testing Playbook

## Step 1: Create Test User & Session via mongosh
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
"

## Step 2: Test Backend API
curl -X GET "$URL/api/auth/me" -H "Authorization: Bearer YOUR_SESSION_TOKEN"

## Checklist
- User has custom user_id (UUID), NOT MongoDB's _id
- Session user_id matches user's user_id exactly
- All queries use {"_id": 0} projection
- /api/auth/me returns user data (not 401/404)
- Operator allowlist via OPERATOR_EMAIL env enforced
