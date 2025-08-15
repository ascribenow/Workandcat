# 🐘 PostgreSQL Migration Guide for Twelvr CAT Preparation Platform

## 🎯 Overview
This guide walks you through migrating from SQLite to production-ready managed PostgreSQL.

## 🥇 Recommended: Neon (Serverless PostgreSQL)

### Why Neon?
- ✅ **Serverless**: Auto-scales, pay-per-use
- ✅ **Free Tier**: 512MB storage, perfect for getting started
- ✅ **Production Ready**: Automatic backups, monitoring, branching
- ✅ **Developer Friendly**: 2-minute setup, great dashboard

### Step 1: Create Neon Account
1. Go to [https://neon.tech](https://neon.tech)
2. Sign up with GitHub/Google (recommended)
3. Create a new project
4. Choose a project name: "twelvr-cat-prep"
5. Select region closest to your users

### Step 2: Get Connection String
1. In Neon dashboard, go to your project
2. Click "Connection Details"
3. Copy the connection string (starts with `postgresql://`)
4. It will look like: `postgresql://username:password@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require`

### Step 3: Update Environment Variables
Add to your `.env` file:
```bash
# PostgreSQL Configuration (Production)
DATABASE_URL=postgresql://your-connection-string-here
```

### Step 4: Run Migration
```bash
cd /app/scripts
python migrate_to_postgresql.py
```

## 🥈 Alternative: Supabase PostgreSQL

### Why Supabase?
- ✅ **Full Stack**: Database + Auth + Real-time + Storage
- ✅ **Free Tier**: 500MB database, 2 projects
- ✅ **Great Dashboard**: Easy database management

### Setup Steps:
1. Go to [https://supabase.com](https://supabase.com)
2. Create account and new project
3. Go to Settings → Database
4. Copy the connection string
5. Update DATABASE_URL in .env
6. Run migration script

## 🏗️ Production Environment Variables

### Required .env Updates:
```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:5432/database?sslmode=require

# Optional: Database Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
```

## 🚀 Migration Process

### What the Migration Does:
1. ✅ **Schema Creation**: Creates all tables in PostgreSQL
2. ✅ **Data Migration**: Copies all data from SQLite
3. ✅ **Verification**: Ensures data integrity
4. ✅ **Performance**: Optimizes for production workload

### Tables Migrated:
- Users (admin/student accounts)
- Topics (CAT taxonomy)
- Questions (practice questions)
- Sessions (study sessions)
- Attempts (question attempts)
- PYQ data (previous year questions)
- Mastery tracking
- Progress analytics

## 🧪 Testing After Migration

### 1. Basic Functionality:
```bash
# Test database connection
python -c "from database import engine; print('✅ Database connected!')"

# Test admin login
# Access your app and login with admin credentials

# Test student session
# Start a practice session as student
```

### 2. Performance Verification:
- Test multiple concurrent users
- Verify session creation speed
- Check progress analytics loading

## 🔒 Security Best Practices

### Database Security:
- ✅ **SSL Required**: All connections encrypted
- ✅ **Connection Pooling**: Prevents connection exhaustion
- ✅ **Managed Service**: Automatic security updates
- ✅ **Backups**: Automatic daily backups

### Environment Security:
- Never commit DATABASE_URL to git
- Use different databases for dev/staging/production
- Monitor database access logs

## 📊 Performance Benefits

### PostgreSQL vs SQLite:
| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Concurrent Users | Limited | Unlimited |
| Data Size | 281TB max | Unlimited |
| ACID Compliance | Yes | Yes |
| Full-text Search | Basic | Advanced |
| Backups | Manual | Automatic |
| Scaling | Vertical only | Horizontal |
| Production Ready | No | Yes |

## 🆘 Troubleshooting

### Common Issues:

#### "connection refused"
- Check DATABASE_URL format
- Verify database is running
- Check firewall/network settings

#### "relation does not exist"
- Run migration script again
- Verify schema creation completed

#### "authentication failed"
- Check username/password in connection string
- Verify database user has proper permissions

#### Migration fails with data issues
- Check SQLite data integrity first
- Look for special characters in data
- Verify all required columns exist

### Getting Help:
1. Check migration script output
2. Verify connection string format
3. Test with simple PostgreSQL client
4. Contact Neon/Supabase support if needed

## 🎉 After Migration

### What You Get:
- ✅ **Production Ready**: Handles multiple concurrent users
- ✅ **Scalable**: Grows with your user base  
- ✅ **Reliable**: Automatic backups and monitoring
- ✅ **Fast**: Optimized for web applications
- ✅ **Secure**: SSL encryption and managed security

### Next Steps:
1. Monitor database performance
2. Set up monitoring alerts
3. Configure automatic backups
4. Plan for scaling as user base grows

---

**Need help?** The migration script provides detailed output to help troubleshoot any issues!