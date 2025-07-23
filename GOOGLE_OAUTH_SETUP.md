# Google OAuth Setup Guide

This guide will help you set up Google OAuth integration for the FastAPI Authentication System.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console
3. The application running locally

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API (if not already enabled)

## Step 2: Configure OAuth Consent Screen

1. In Google Cloud Console, go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type (unless you have a Google Workspace)
3. Fill in the required information:
   - **App name**: Your app name (e.g., "FastAPI Auth System")
   - **User support email**: Your email
   - **Developer contact information**: Your email
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Add test users (your email) if in testing mode
6. Save and continue

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Configure the OAuth client:
   - **Name**: Your app name
   - **Authorized JavaScript origins**:
     - `http://localhost:8000`
     - `http://localhost:3000` (if using frontend)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/auth/google/callback`
5. Click **Create**
6. Copy the **Client ID** and **Client Secret**

## Step 4: Set Environment Variables

Add these environment variables to your system:

```bash
# Google OAuth Configuration
export GOOGLE_CLIENT_ID="your-google-client-id-here"
export GOOGLE_CLIENT_SECRET="your-google-client-secret-here"
export GOOGLE_REDIRECT_URI="http://localhost:8000/auth/google/callback"

# Existing configuration
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=password
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=auth_app
export SECRET_KEY="your-secure-secret-key-here"
```

## Step 5: Run Database Migration

Apply the new migration to add OAuth fields:

```bash
alembic upgrade head
```

## Step 6: Test the Integration

### Method 1: Using the API

1. **Get OAuth URL:**
   ```bash
   curl http://localhost:8000/auth/google
   ```

2. **Redirect to Google:**
   ```bash
   curl -L http://localhost:8000/auth/google/redirect
   ```

3. **Handle callback** (you'll need to implement a frontend or use the browser)

### Method 2: Using a Frontend

Create a simple HTML page to test the OAuth flow:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Google OAuth Test</title>
</head>
<body>
    <h1>Google OAuth Test</h1>
    <button onclick="startGoogleOAuth()">Login with Google</button>
    
    <script>
        function startGoogleOAuth() {
            window.location.href = 'http://localhost:8000/auth/google/redirect';
        }
    </script>
</body>
</html>
```

## API Endpoints

### Google OAuth Endpoints

1. **GET** `/auth/google`
   - Returns the Google OAuth URL
   - Response: `{"oauth_url": "https://accounts.google.com/..."}`

2. **GET** `/auth/google/redirect`
   - Redirects to Google OAuth
   - Redirects to Google's authorization page

3. **POST** `/auth/google/callback`
   - Handles OAuth callback with authorization code
   - Request body: `{"code": "auth_code", "redirect_uri": "callback_url"}`
   - Response: JWT token and user info

4. **GET** `/auth/google/callback`
   - Handles OAuth callback via URL parameters
   - Query parameter: `?code=auth_code`
   - Response: JWT token and user info

## OAuth Flow

1. **User clicks "Login with Google"**
2. **Redirect to Google** (`/auth/google/redirect`)
3. **User authorizes on Google**
4. **Google redirects back** with authorization code
5. **Server exchanges code for token**
6. **Server gets user info from Google**
7. **Server creates/updates user in database**
8. **Server returns JWT token**

## User Management

### OAuth Users vs Email Users

- **Email users**: Have passwords, use `/signup` and `/login`
- **OAuth users**: No passwords, use Google OAuth flow
- **Mixed accounts**: If a user signs up with email and later uses Google OAuth with the same email, the accounts are merged

### User Fields

- `google_id`: Unique Google user ID
- `avatar_url`: Google profile picture URL
- `auth_provider`: "email" or "google"
- `hashed_password`: Null for OAuth users

## Security Considerations

1. **HTTPS in Production**: Always use HTTPS in production
2. **Secure Redirect URIs**: Only allow trusted redirect URIs
3. **Token Storage**: Store tokens securely
4. **User Validation**: Validate Google user info before creating accounts
5. **Rate Limiting**: Implement rate limiting on OAuth endpoints

## Troubleshooting

### Common Issues

1. **"Invalid redirect_uri"**
   - Check that your redirect URI matches exactly in Google Console
   - Ensure no trailing slashes or extra characters

2. **"Invalid client"**
   - Verify your Client ID and Client Secret
   - Check that the OAuth consent screen is configured

3. **"Access denied"**
   - Ensure the user is added to test users (if in testing mode)
   - Check that the required scopes are added

4. **Database errors**
   - Run `alembic upgrade head` to apply migrations
   - Check that all OAuth fields are added to the users table

### Debug Mode

Enable debug logging by setting:

```bash
export LOG_LEVEL=DEBUG
```

## Production Deployment

1. **Update redirect URIs** in Google Console for production domain
2. **Use HTTPS** for all OAuth endpoints
3. **Set secure environment variables**
4. **Implement proper error handling**
5. **Add rate limiting**
6. **Monitor OAuth usage**

## Example Response

Successful OAuth login response:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "full_name": "John Doe",
    "auth_provider": "google",
    "avatar_url": "https://lh3.googleusercontent.com/..."
  }
}
``` 