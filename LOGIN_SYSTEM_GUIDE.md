# 🔐 Simplified Login & User Management System

## Overview

The CRM now uses a **simple username/password authentication** system where:
- ✅ Login with **email** OR **full name** as username
- ✅ **Admins** and **Managers** can create user accounts
- ✅ No complex registration process
- ✅ Secure JWT token authentication

---

## 🚀 Quick Start

### 1. Initial Admin Setup (First Time Only)

When deploying to production, create the first admin user:

**Option A: Via API (Recommended)**

```bash
curl -X POST "https://your-backend.onrender.com/api/auth/bootstrap-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Admin User",
    "email": "admin@dmhca.in",
    "password": "SecurePassword123!",
    "phone": "+919876543210",
    "hospital_id": null
  }'
```

**Option B: Via API Docs**

1. Open: `https://your-backend.onrender.com/docs`
2. Find: `POST /api/auth/bootstrap-admin`
3. Click "Try it out"
4. Fill in the admin details
5. Execute

---

### 2. Login

Users can login with:
- **Email**: `admin@dmhca.in`
- **OR Full Name**: `Admin User`
- **Password**: (the one you set)

**Login Page**: `https://your-frontend.vercel.app/login`

---

## 👥 User Management

### Who Can Create Users?

- ✅ **Super Admin** - Can create anyone
- ✅ **Hospital Admin** - Can create users in their hospital
- ✅ **Manager** - Can create team members
- ❌ **Team Leader** - Cannot create users
- ❌ **Counselor** - Cannot create users

### Creating New Users

#### Via Frontend (Easiest)

1. Login as Admin or Manager
2. Go to **Users** page (`/users`)
3. Click **"Add User"** button
4. Fill in the form:
   - Full Name: `John Doe`
   - Email: `john@example.com` (used for login)
   - Phone: `+91 9876543210` (optional)
   - Password: `SecurePassword123`
   - Role: Select from dropdown
   - Hospital ID: (optional, leave empty for Super Admin)
5. Click **"Create User"**

#### Via API

```bash
curl -X POST "https://your-backend.onrender.com/api/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+91 9876543210",
    "password": "SecurePassword123",
    "role": "Counselor",
    "hospital_id": null,
    "reports_to": null,
    "is_active": true
  }'
```

---

## 🔒 Authentication Flow

### 1. User Login Process

```
User enters username/email + password
         ↓
Backend authenticates credentials
         ↓
Returns JWT access token (valid 7 days)
         ↓
Frontend stores token in localStorage
         ↓
Token sent with every API request
```

### 2. Token Usage

Every API request includes:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token contains:
- User email
- User role
- Hospital ID
- Expiration time

---

## 📋 User Roles & Permissions

| Role | Can Create Users | Can View All Leads | Can Modify Settings |
|------|------------------|-------------------|-------------------|
| **Super Admin** | ✅ All roles | ✅ Global | ✅ All |
| **Hospital Admin** | ✅ Below Super Admin | ✅ Hospital only | ✅ Hospital only |
| **Manager** | ✅ Below Manager | ✅ Team only | ⚠️ Limited |
| **Team Leader** | ❌ | ✅ Team only | ❌ |
| **Counselor** | ❌ | ⚠️ Assigned only | ❌ |

---

## 🛠️ Configuration

### Backend Environment Variables

```bash
# JWT Secret (IMPORTANT: Change in production!)
JWT_SECRET_KEY=mJWIVC+ikuaGqlHd4cJxCr+YpN8DjLX+PlQQHUWqcnp4WnF//y2TT6FKfvdnaXnNQ+Y3No3VgVI7HajHhsABoQ==

# Token expiration (minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days
```

### Frontend Configuration

Add to `.env`:
```bash
REACT_APP_API_URL=https://your-backend.onrender.com
```

---

## 🔐 Security Features

1. **Password Hashing**: All passwords encrypted with bcrypt
2. **JWT Tokens**: Secure token-based authentication
3. **Role-Based Access**: Different permissions per role
4. **Auto-Hash Legacy Passwords**: Old plaintext passwords auto-converted on login
5. **Inactive Account Protection**: Disabled users cannot login

---

## 📝 Example User Accounts

For testing, you can create these sample users:

```json
{
  "full_name": "Super Admin",
  "email": "admin@dmhca.in",
  "password": "Admin@123",
  "role": "Super Admin"
}
```

```json
{
  "full_name": "Manager User",
  "email": "manager@dmhca.in", 
  "password": "Manager@123",
  "role": "Manager"
}
```

```json
{
  "full_name": "Counselor User",
  "email": "counselor@dmhca.in",
  "password": "Counselor@123",
  "role": "Counselor"
}
```

---

## 🚨 Troubleshooting

### "Invalid username/email or password"
- Check credentials are correct
- Try using email instead of full name (or vice versa)
- Ensure password is correct (case-sensitive)

### "User account is inactive"
- Contact administrator to activate account
- Admin can update `is_active=true` in Users page

### "You do not have permission to create users"
- Only Admin and Manager roles can create users
- Check your role in Users page

### "Email already registered"
- Email must be unique
- Use a different email address
- Or update the existing user

---

## 🎯 Best Practices

1. **Strong Passwords**: Minimum 8 characters, mix of letters, numbers, symbols
2. **Unique Emails**: One email per user
3. **Regular Updates**: Change passwords periodically
4. **Role Assignment**: Give minimum required permissions
5. **Deactivate, Don't Delete**: Mark users as inactive instead of deleting

---

## 📚 API Endpoints

### Authentication
- `POST /api/auth/login` - Login with username/email + password
- `POST /api/auth/bootstrap-admin` - Create first admin (one-time)
- `GET /api/auth/me` - Get current user profile

### User Management
- `GET /api/users` - List all users (Admin only)
- `POST /api/users` - Create new user (Admin/Manager only)
- `PUT /api/users/{user_id}` - Update user (Admin only)
- `DELETE /api/users/{user_id}` - Delete user (Admin only)

---

## ✅ Summary

**Login is now simple:**
1. Enter email OR name
2. Enter password
3. Click login
4. Start using CRM!

**Creating users is easy:**
1. Login as Admin/Manager
2. Go to Users page
3. Click "Add User"
4. Fill form and create!

**No complex registration needed!** 🎉
