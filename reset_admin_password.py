#!/usr/bin/env python3
"""
Reset admin password script
"""
import asyncio
import sys
import os
sys.path.append('/app/backend')

from database import get_async_compatible_db, User
from sqlalchemy import select, update
from auth_service import AuthService

async def reset_admin_password():
    """Reset admin password to 'admin2025'"""
    try:
        # Create auth service
        auth_service = AuthService()
        
        # Get database session
        from database import SessionLocal, AsyncSession
        sync_db = SessionLocal()
        db = AsyncSession(sync_db)
        
        try:
            # Find admin user
            result = await db.execute(select(User).where(User.email == 'sumedhprabhu18@gmail.com'))
            admin_user = result.scalar_one_or_none()
            
            if admin_user:
                print(f"Found admin user: {admin_user.email}")
                print(f"Current is_admin status: {admin_user.is_admin}")
                
                # Hash new password
                new_password_hash = auth_service.hash_password('admin2025')
                
                # Update password and ensure is_admin is True
                await db.execute(
                    update(User)
                    .where(User.email == 'sumedhprabhu18@gmail.com')
                    .values(password_hash=new_password_hash, is_admin=True)
                )
                await db.commit()
                
                print("✅ Admin password reset to 'admin2025'")
                print("✅ Admin flag set to True")
                
                # Verify the change
                result = await db.execute(select(User).where(User.email == 'sumedhprabhu18@gmail.com'))
                updated_user = result.scalar_one_or_none()
                
                if updated_user:
                    password_correct = auth_service.verify_password('admin2025', updated_user.password_hash)
                    print(f"✅ Password verification: {password_correct}")
                    print(f"✅ Is admin: {updated_user.is_admin}")
                
            else:
                print("❌ Admin user not found. Creating new admin user...")
                
                # Create new admin user
                new_admin = User(
                    email='sumedhprabhu18@gmail.com',
                    full_name='Admin User',
                    password_hash=auth_service.hash_password('admin2025'),
                    is_admin=True
                )
                
                db.add(new_admin)
                await db.commit()
                await db.refresh(new_admin)
                
                print(f"✅ Created new admin user: {new_admin.email}")
                print(f"✅ Admin ID: {new_admin.id}")
                print(f"✅ Is admin: {new_admin.is_admin}")
                
        finally:
            await db.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reset_admin_password())