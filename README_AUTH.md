# Descope Authentication Integration

This application now includes Descope authentication for secure user management and passwordless authentication.

## Setup Instructions

### 1. Get Descope Project ID

1. Visit [Descope Console](https://app.descope.com)
2. Create a new project or use an existing one
3. Copy your Project ID from the project settings

### 2. Environment Configuration

Add your Descope Project ID to your `.env` file:

```env
DESCOPE_PROJECT_ID=P2xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Authentication Methods

The integration supports two authentication methods:

#### Magic Link Authentication
- Users enter their email
- Receive a secure magic link via email
- Click the link to authenticate automatically

#### OTP Authentication
- Users enter their email
- Receive a 6-digit OTP code via email
- Enter the code to authenticate

## API Endpoints

### Authentication Endpoints

- `POST /auth/magic-link/send` - Send magic link
- `POST /auth/magic-link/verify` - Verify magic link token
- `POST /auth/otp/send` - Send OTP code
- `POST /auth/otp/verify` - Verify OTP code
- `POST /auth/refresh` - Refresh session token
- `POST /auth/logout` - Logout user
- `GET /auth/validate` - Validate session token

### Frontend Pages

- `/auth` - Authentication page with Magic Link and OTP options
- `/` - Main booking page with auth integration

## Frontend Integration

The premium booking template now includes:

- Authentication status checking
- Login/logout functionality
- Session token management
- Automatic token refresh
- Protected API calls with authorization headers

## Security Features

- JWT-based sessions
- Secure token validation
- Refresh token mechanism
- Automatic session expiration
- CORS protection
- Input validation and sanitization

## Usage Examples

### JavaScript Frontend

```javascript
// Check authentication status
const sessionToken = localStorage.getItem('session_token');
const isAuthenticated = !!sessionToken;

// Make authenticated API calls
const headers = {
    'Authorization': `Bearer ${sessionToken}`,
    'Content-Type': 'application/json'
};

// Logout
localStorage.removeItem('session_token');
localStorage.removeItem('refresh_token');
localStorage.removeItem('user');
```

### Python Backend

```python
from app.api.auth import get_current_user
from fastapi import Depends

@router.get("/protected-endpoint")
async def protected_route(current_user = Depends(get_current_user)):
    # This route requires authentication
    return {"user": current_user}
```

## Middleware Configuration

To protect specific routes, you can use the auth middleware:

```python
from app.middleware.auth import AuthMiddleware

# Protect specific paths
app.add_middleware(
    AuthMiddleware,
    protected_paths=["/api/bookings", "/api/user"]
)
```

## Error Handling

The system handles various authentication scenarios:

- Invalid tokens (401 Unauthorized)
- Expired sessions (401 Unauthorized)
- Network errors (500 Internal Server Error)
- Invalid OTP codes (400 Bad Request)
- Rate limiting (429 Too Many Requests)

## Development Notes

- Session tokens are stored in localStorage
- Tokens are automatically included in API requests
- The auth service handles token refresh automatically
- All authentication errors are logged for debugging

## Next Steps

1. Configure your Descope project settings
2. Set up email templates in Descope dashboard
3. Configure authentication methods (Magic Link, OTP, Social, etc.)
4. Test the authentication flow
5. Deploy with proper environment variables