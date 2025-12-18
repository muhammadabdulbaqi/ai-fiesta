# Quick Admin Setup Guide

## Creating Your First Admin User

### Step 1: Run the Migration

Make sure the `admin_users` table exists:

```bash
cd backend
alembic upgrade head
```

### Step 2: Create Admin User

Run the admin creation script:

```bash
cd backend
python create_admin.py
```

Enter:
- **Email**: Your admin email (e.g., `admin@fiesta.com`)
- **Username**: Your admin username (e.g., `admin`)
- **Password**: Your admin password

### Step 3: Login

1. Go to `http://localhost:3000/login`
2. Enter your admin email and password
3. You'll be logged in and see the "Admin Dashboard" link in the sidebar
4. Click it to access the admin panel

## Adding Regular Users

### Option 1: Through Frontend (Recommended)
1. Go to `http://localhost:3000/register`
2. Fill in the registration form
3. User is created automatically

### Option 2: Using Script
```bash
cd backend
python add_user.py
```

## Viewing Database

### Using pgAdmin
1. Download pgAdmin from https://www.pgadmin.org/download/
2. Create new server connection:
   - Host: `localhost`
   - Port: `5433`
   - Database: `fiesta_db`
   - Username: `fiesta_user`
   - Password: `fiesta_pass`
3. Browse tables to view users, conversations, etc.

### Using Command Line
```bash
psql -h localhost -p 5433 -U fiesta_user -d fiesta_db
# Password: fiesta_pass
```

## Important Notes

- **Admin login**: Admins can login through the regular login page (`/login`). The system automatically detects admin credentials.
- **Admin Dashboard**: Only visible in sidebar if you're logged in as admin.
- **Separate tokens**: Admin tokens are stored separately from user tokens, so you can be logged in as both (though not recommended).
- **Password security**: Always use the provided scripts to create users/admins - they properly hash passwords.

For more details, see `DATABASE_MANAGEMENT_GUIDE.md`.

