"""
Supabase Connection Tester
Tests various connection string formats and provides detailed diagnostics
"""

import psycopg2
import sys
from urllib.parse import urlparse

def test_connection_string(connection_string):
    """Test a PostgreSQL connection string with detailed diagnostics"""
    print(f"🔍 Testing connection string...")
    print(f"Connection string: {connection_string}")
    
    # Parse the URL
    try:
        parsed = urlparse(connection_string)
        print(f"\n📋 Parsed connection details:")
        print(f"   Host: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Database: {parsed.path[1:] if parsed.path else 'Not specified'}")
        print(f"   Username: {parsed.username}")
        print(f"   Password: {'***' if parsed.password else 'Not provided'}")
        
    except Exception as e:
        print(f"❌ Failed to parse connection string: {e}")
        return False
    
    # Test basic connectivity
    print(f"\n🌐 Testing network connectivity...")
    import socket
    try:
        socket.gethostbyname(parsed.hostname)
        print(f"✅ Hostname resolves to IP address")
    except socket.gaierror as e:
        print(f"❌ Hostname resolution failed: {e}")
        print(f"💡 This suggests the hostname might be incorrect")
        return False
    
    # Test database connection
    print(f"\n🔌 Testing database connection...")
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful!")
        print(f"   PostgreSQL version: {version[:60]}...")
        
        # Test database info
        cursor.execute("SELECT current_database(), current_user")
        db_info = cursor.fetchone()
        print(f"   Current database: {db_info[0]}")
        print(f"   Current user: {db_info[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        
        # Provide specific guidance based on error
        error_str = str(e)
        if "authentication failed" in error_str:
            print(f"💡 Authentication issue - check username/password")
        elif "does not exist" in error_str:
            print(f"💡 Database or user doesn't exist")
        elif "timeout" in error_str:
            print(f"💡 Connection timeout - check network/firewall")
        elif "refused" in error_str:
            print(f"💡 Connection refused - check host/port")
        
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def suggest_fixes():
    """Provide common Supabase connection string fixes"""
    print(f"\n🛠️ Common Supabase Connection Issues & Fixes:")
    print(f"\n1. **Connection String Format**:")
    print(f"   Correct: postgresql://postgres:password@db.xxx.supabase.co:5432/postgres")
    print(f"   Wrong:   postgresql://postgres:@password@db.xxx.supabase.co:5432/postgres")
    
    print(f"\n2. **How to get correct connection string from Supabase:**")
    print(f"   - Go to your Supabase project dashboard")
    print(f"   - Click 'Settings' → 'Database'")
    print(f"   - Look for 'Connection string' section")
    print(f"   - Select 'URI' format")
    print(f"   - Copy the string (it will have [YOUR-PASSWORD] placeholder)")
    print(f"   - Replace [YOUR-PASSWORD] with your actual password")
    
    print(f"\n3. **Special Characters in Password:**")
    print(f"   - If password has @, #, %, etc., it needs URL encoding")
    print(f"   - @ becomes %40")
    print(f"   - # becomes %23")
    print(f"   - % becomes %25")
    
    print(f"\n4. **Supabase-specific Notes:**:")
    print(f"   - Default username is 'postgres'")
    print(f"   - Default database is 'postgres'")
    print(f"   - Port is always 5432")
    print(f"   - SSL is automatically enabled")

def main():
    """Main testing function"""
    print("🔧 Supabase PostgreSQL Connection Tester")
    print("=" * 50)
    
    # Test the provided connection string
    connection_string = "postgresql://postgres:Sumedh_123@db.itgusggwslnsbgonyicv.supabase.co:5432/postgres"
    
    success = test_connection_string(connection_string)
    
    if not success:
        suggest_fixes()
        
        print(f"\n📝 Next Steps:")
        print(f"1. Verify your Supabase connection string from the dashboard")
        print(f"2. Check if your password needs URL encoding")
        print(f"3. Ensure your Supabase project is active")
        print(f"4. Try connecting with a PostgreSQL client first")
    else:
        print(f"\n🎉 Connection successful! Ready to run migration.")

if __name__ == "__main__":
    main()