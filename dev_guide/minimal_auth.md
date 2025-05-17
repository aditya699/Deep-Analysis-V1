# ✅ END-TO-END AUTH FLOW (Email + OTP + JWT + Mongo + Frontend)

---

## 👤 1. User lands on your site

Let’s say:
**Aditya** visits **your website** (`deepanalysis.ai`)

He sees a simple login screen:

```
👋 Welcome to Deep Analysis  
📧 Enter your email to begin
```

---

## 📩 2. User enters email: `aditya@example.com`

Frontend sends a request:

```http
POST /auth/request-password
Content-Type: application/json

{
  "email": "aditya@example.com"
}
```

---

## 🔧 3. Backend generates OTP

* Generates: `Ds_73Ufq`
* Stores in MongoDB `otp_codes` collection:

```json
{
  "email": "aditya@example.com",
  "otp": "Ds_73Ufq",
  "expires_at": "2025-05-20T12:00:00Z"
}
```

* Sends email (or logs it for now):

```
💌 Sent login password to aditya@example.com:
Your password: Ds_73Ufq (valid for 72 hours)
```

---

## 🔐 4. User enters password

```
Enter password: Ds_73Ufq
```

Frontend sends:

```http
POST /auth/verify-password
Content-Type: application/json

{
  "email": "aditya@example.com",
  "otp": "Ds_73Ufq"
}
```

---

## ✅ 5. Backend verifies

* Looks up OTP from Mongo
* Checks:

  * Email matches
  * OTP matches
  * Not expired ✅

Now looks up the `users` collection:

```json
{
  "email": "aditya@example.com",
  "name": "Aditya",
  "plan": "free"
}
```

If user exists → generate JWT:

```json
{
  "sub": "aditya@example.com",
  "exp": "2025-05-20T22:00:00Z"
}
```

Returns token:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 🧠 6. Frontend stores the token

In browser:

```js
localStorage.setItem("token", "eyJhbGciOiJIUzI1NiIs...")
```

User is now **authenticated**.

---

## 📄 7. User uploads a CSV file

```http
POST /analyze
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## 🧠 8. Backend decodes the token

```python
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
email = payload["sub"]  # aditya@example.com
```

Looks up in `users`:

```json
{
  "email": "aditya@example.com",
  "plan": "free",
  "files_uploaded": 3
}
```

If all valid → accepts the request and starts analysis.

---

## ✅ Final Result

* User didn't need to sign up
* Password was temporary
* Token is used everywhere
* Identity is **stateless**
* Users stored in DB
* Tasks linked to email

---

## 🔁 Recap of Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API

    User->>Frontend: Enter email
    Frontend->>API: POST /request-password
    API->>Mongo: Save OTP
    API-->>User: Email sent (OTP)

    User->>Frontend: Enters OTP
    Frontend->>API: POST /verify-password
    API->>Mongo: Check OTP + get user
    API-->>Frontend: Return JWT

    Frontend->>API: POST /analyze (with JWT)
    API->>Mongo: Get user from token
    API-->>Frontend: Result / Report link
```

