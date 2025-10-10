"""
Cleanup script to remove duplicate session packs
Keeps only the LATEST pack for each user
"""
from database import SessionLocal
from sqlalchemy import text

def cleanup_duplicate_packs():
    db = SessionLocal()
    
    print("="*80)
    print("CLEANING UP DUPLICATE SESSION PACKS")
    print("="*80)
    
    # Find users with multiple available packs
    result = db.execute(text("""
        SELECT 
            sp.user_id,
            u.email,
            COUNT(*) as pack_count
        FROM session_packs sp
        LEFT JOIN sessions s ON CAST(sp.session_id AS varchar) = CAST(s.session_id AS varchar)
        JOIN users u ON CAST(sp.user_id AS varchar) = CAST(u.id AS varchar)
        WHERE s.session_id IS NULL OR s.status IN ('planned', 'active')
        GROUP BY sp.user_id, u.email
        HAVING COUNT(*) > 1
        ORDER BY pack_count DESC
    """))
    
    users_with_dupes = result.fetchall()
    
    if not users_with_dupes:
        print("\n✅ No duplicate packs found!")
        db.close()
        return
    
    print(f"\nFound {len(users_with_dupes)} user(s) with duplicate packs:\n")
    
    total_deleted = 0
    
    for user in users_with_dupes:
        user_id = str(user[0])
        email = user[1]
        pack_count = user[2]
        
        print(f"\n{email}: {pack_count} packs")
        
        # Get all available packs for this user, ordered by creation date
        packs_result = db.execute(text("""
            SELECT sp.session_id, sp.created_at
            FROM session_packs sp
            LEFT JOIN sessions s ON CAST(sp.session_id AS varchar) = CAST(s.session_id AS varchar)
            WHERE sp.user_id = :user_id
            AND (s.session_id IS NULL OR s.status IN ('planned', 'active'))
            ORDER BY sp.created_at DESC
        """), {"user_id": user_id})
        
        packs = packs_result.fetchall()
        
        if len(packs) > 1:
            # Keep the latest (first in list), delete others
            keep_pack = packs[0]
            delete_packs = packs[1:]
            
            print(f"  Keeping: {str(keep_pack[0])[:16]}... (created {keep_pack[1]})")
            print(f"  Deleting {len(delete_packs)} older pack(s):")
            
            for pack in delete_packs:
                pack_id = str(pack[0])
                
                # Delete pack questions first
                db.execute(text("""
                    DELETE FROM session_pack_questions
                    WHERE session_id = :session_id
                """), {"session_id": pack_id})
                
                # Delete pack
                db.execute(text("""
                    DELETE FROM session_packs
                    WHERE session_id = :session_id
                """), {"session_id": pack_id})
                
                print(f"    ✅ Deleted: {pack_id[:16]}... (created {pack[1]})")
                total_deleted += 1
            
            db.commit()
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: Deleted {total_deleted} duplicate pack(s) from {len(users_with_dupes)} user(s)")
    print(f"{'='*80}")
    
    db.close()

if __name__ == "__main__":
    cleanup_duplicate_packs()
