# Admin Management Guide

## Overview
The Kite Order Scheduler now includes a multi-admin authentication system. Only authenticated admins can access the dashboard and logs.

## Admin Management

### Creating an Admin

Use the CLI tool to create new admin users:

```bash
python manage_admins.py create-admin
```

This will prompt you to enter:
- **Username**: Unique admin username
- **Password**: Admin password (will prompt for confirmation)
- **Email**: Optional email address

**Example:**
```bash
python manage_admins.py create-admin --username john --password secret123 --email john@example.com
```

### Listing All Admins

To view all admin users in the system:

```bash
python manage_admins.py list-admins
```

### Changing Admin Password

To change an admin's password:

```bash
python manage_admins.py change-password
```

This will prompt you for:
- **Username**: The admin username
- **Password**: New password (will prompt for confirmation)

**Example:**
```bash
python manage_admins.py change-password --username admin
```

### Deleting an Admin

To remove an admin user:

```bash
python manage_admins.py delete-admin --username john
```

This will ask for confirmation before deletion.

## Admin Login Flow

### 1. **Initial Access**
- Navigate to the app home or `/admin/login`
- If not authenticated, you will be redirected to the login page

### 2. **Login**
- Enter your **username** and **password**
- Click "Login"

### 3. **Dashboard Access**
- Upon successful login, you'll be redirected to the dashboard
- Your username appears in the top-right corner navbar
- You can now:
  - View Kite users
  - Create new users
  - Schedule orders
  - View logs

### 4. **Logout**
- Click the "Logout" button in the navbar (top-right corner)
- Session is cleared and you'll be redirected to login page

## Protected Routes

The following routes require admin authentication:
- `/dashboard` - Main dashboard
- `/logs` - Logs and audit page
- `/dashboard/orders/create` - Schedule orders (POST)
- `/dashboard/users/create` - Create Kite users (POST)

## Session Management

- Admin sessions are stored in Flask's secure session cookies
- Session data includes:
  - `admin_id`: Admin user ID
  - `admin_username`: Admin username (displayed in navbar)
- Sessions persist across page refreshes
- Logging out clears all session data

## Security Notes

- Passwords are hashed using werkzeug's `generate_password_hash` (PBKDF2 by default)
- Never commit plaintext passwords to version control
- Use strong passwords for admin accounts
- Regularly review admin access logs
- Delete unused admin accounts promptly

## Default Admin

An initial admin account is created during setup:
- **Username**: `admin`
- **Password**: `admin123` (change this immediately in production!)

Create additional admin accounts for each team member who needs access.

## Troubleshooting

### "Invalid username or password"
- Verify spelling of username
- Ensure caps lock is not on
- Check that account exists: `python manage_admins.py list-admins`

### "Please login as admin first"
- Your session may have expired
- Try logging in again at `/admin/login`

### Locked out of all accounts
- You can create a new admin via CLI:
  ```bash
  python manage_admins.py create-admin --username newadmin
  ```
- Or reset the database and reinitialize
