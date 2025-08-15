# 🚀 Quick Supabase Setup for Twelvr

## Issue: Current Project Not Responding
Your current Supabase project hostname `db.itgusggwslnsbgonyicv.supabase.co` is not resolving, which suggests:
- Project may be paused/inactive
- Project still being provisioned  
- Network configuration issue

## ⚡ Quick Fix: Create New Project (2 minutes)

### Step 1: Create New Supabase Project
1. Go to [https://supabase.com/dashboard/projects](https://supabase.com/dashboard/projects)
2. Click **"New Project"**
3. Fill in details:
   - **Name**: `twelvr-prod`
   - **Database Password**: Use a simple password like `Twelvr2025!` (no special symbols)
   - **Region**: Choose closest to your users
4. Click **"Create new project"**
5. Wait 30-60 seconds for provisioning

### Step 2: Get Connection String  
1. Once project is ready, go to **Settings → Database**
2. Look for **"Connection string"** section
3. Click **"URI"** tab
4. Copy the connection string
5. Replace `[YOUR-PASSWORD]` with your password

### Step 3: Verify Format
Your new connection string should look like:
```
postgresql://postgres:password@db.[NEW-REF].supabase.co:5432/postgres
```

## 🔧 Alternative: Fix Current Project

### Check Current Project Status:
1. Go to your current project dashboard
2. Look for status indicators:
   - **Green "Active"** = Good
   - **Orange "Paused"** = Need to unpause
   - **Red "Issue"** = Need to fix

### If Project is Paused:
1. Click **"Resume project"** or **"Unpause"**
2. Wait for it to become active
3. Try connection string again

## 🎯 Recommended Password Formats

**Avoid these characters in passwords:**
- `@` `$` `#` `%` `&` (need URL encoding)

**Use these instead:**
- `Twelvr2025!`
- `SecurePass123`
- `MyApp2025_Safe`

## ✅ Testing New Connection

Once you have a new connection string, I'll test it and run the migration immediately!