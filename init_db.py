"""Database initialization script"""
import sys
from app.database import engine, Base, SessionLocal
from app.models import User, UserProfile, Channel, Feed, ApiKey, RequestLog, CustomWidget, AutomationRule  # Import models before creating tables
from app.services.auth_service import get_or_create_admin
from app.config import settings

def init_database():
    """Initialize database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    
    if settings.AUTH_ENABLED:
        print("\nCreating admin user...")
        db = SessionLocal()
        try:
            admin = get_or_create_admin(db)
            print(f"✓ Admin user created: {admin.email}")
            print(f"  Password: {settings.ADMIN_PASSWORD}")
            
            # Create admin profile
            from app.models.user_profile import UserProfile
            admin_profile = db.query(UserProfile).filter(UserProfile.user_id == admin.id).first()
            if not admin_profile:
                admin_profile = UserProfile(
                    user_id=admin.id,
                    display_name="Administrator"
                )
                db.add(admin_profile)
                db.commit()
                print(f"✓ Admin profile created")
        finally:
            db.close()
    
    print("\n✓ Database initialization complete!")
    print(f"\nConfiguration:")
    print(f"  - Auth enabled: {settings.AUTH_ENABLED}")
    print(f"  - Database: {settings.DATABASE_TYPE}")
    print(f"  - Database URL: {settings.DATABASE_URL}")
    
    if settings.AUTH_ENABLED:
        print(f"\nAdmin credentials:")
        print(f"  - Email: {settings.ADMIN_EMAIL}")
        print(f"  - Password: {settings.ADMIN_PASSWORD}")
        print(f"\n⚠️  Change admin password after first login!")


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        sys.exit(1)

