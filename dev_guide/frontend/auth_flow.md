# 1.Your app uses a passwordless email-based authentication system with JWT tokens

# 2.Step 1: Request Login

Endpoint: POST /request-login
Payload: { "email": "user@example.com" }
Response: { "message": "Login instructions are being sent to your email", "success": true, "email": "user@example.com" }
UI Flow: Show a form for email input → Show "Check your email" message

# 3.Step 2: Password Verification

Endpoint: POST /verify-password
Payload: { "email": "user@example.com", "password": "ABC123" }
Response: { "message": "Password verified successfully", "success": true, "email": "user@example.com", "access_token": "jwt_token_here" }
UI Flow: Show password input form → Store access token → Redirect to authenticated area

# 4. Key Frontend Requirements

Cookie Handling:

Ensure your HTTP client (axios/fetch) is configured to send cookies automatically
For axios: withCredentials: true
For fetch: credentials: 'include'

# 5. Refresh Token Implementation (The Complex Part)

Key Point: Refresh Tokens are Automatic via Cookies

The refresh token is stored in an HttpOnly cookie by your backend
Frontend cannot access it directly (that's the security feature)
Browser automatically sends it when calling /refresh-token

# 6. Simple Refresh Token Implementation

Use Axios Interceptor - Set Once, Works Everywhere:

javascript
// Setup once in your app
const api = axios.create({
  withCredentials: true  // MUST have this for cookies
});

// Add interceptor to handle 401 errors automatically
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        // Try refresh
        const refreshResponse = await axios.post('/refresh-token', {}, {
          withCredentials: true
        });
        
        // Save new token
        localStorage.setItem('access_token', refreshResponse.data.access_token);
        
        // Retry original request
        error.config.headers.Authorization = `Bearer ${refreshResponse.data.access_token}`;
        return api.request(error.config);
        
      } catch (refreshError) {
        // Redirect to login
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Use api for all requests
api.get('/protected-route'); // Token refresh happens automatically if needed

# 7. Summary

## Final Implementation Points for Frontend Developer

### 1. **Two Login Screens**
- **Screen 1:** Email input → POST `/request-login`
- **Screen 2:** 6-digit password input → POST `/verify-password`

### 2. **Token Storage**
- **Access Token:** Store manually from `/verify-password` response
- **Refresh Token:** Browser handles automatically via HttpOnly cookie

### 3. **API Configuration**
```javascript
const api = axios.create({
  withCredentials: true  // MANDATORY for cookies
});
```

### 4. **Add Access Token to All Requests**
```javascript
headers: {
  'Authorization': `Bearer ${access_token}`
}
```

### 5. **Auto Refresh on 401 (One-time Setup)**
```javascript
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Call /refresh-token → get new access_token → retry request
    }
  }
);
```

### 6. **Error Handling**
- **401:** Trigger token refresh
- **Refresh fails:** Redirect to login

**That's it!** Set up once, works everywhere. The backend handles all the security complexity with cookies automatically.
