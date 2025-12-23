"""Create sample data for testing"""
import random
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import User, Channel, Feed, ApiKey
from app.services.auth_service import get_password_hash
from app.services.channel_service import generate_api_key
from app.config import settings


def create_sample_data():
    """Create sample channels and data"""
    db = SessionLocal()
    
    try:
        print("Creating sample data...")
        
        # Create a test user if auth is enabled
        user_id = None
        if settings.AUTH_ENABLED:
            test_user = db.query(User).filter(User.email == "test@example.com").first()
            if not test_user:
                test_user = User(
                    email="test@example.com",
                    hashed_password=get_password_hash("test123"),
                    is_active=True,
                    is_admin=False
                )
                db.add(test_user)
                db.commit()
                db.refresh(test_user)
                print(f"✓ Created test user: test@example.com / test123")
            user_id = test_user.id
        
        # Create sample channels
        channels_data = [
            {
                "name": "Температурный датчик",
                "description": "Мониторинг температуры и влажности в помещении",
                "public": True
            },
            {
                "name": "Датчик качества воздуха",
                "description": "Измерение CO2, PM2.5 и PM10",
                "public": True
            },
            {
                "name": "Метеостанция",
                "description": "Погодные данные: температура, давление, влажность",
                "public": True
            }
        ]
        
        for ch_data in channels_data:
            # Check if channel already exists
            existing = db.query(Channel).filter(Channel.name == ch_data["name"]).first()
            if existing:
                print(f"  Channel '{ch_data['name']}' already exists, skipping...")
                continue
            
            # Create channel
            channel = Channel(
                user_id=user_id,
                name=ch_data["name"],
                description=ch_data["description"],
                public=ch_data["public"],
                timezone="UTC",
                last_entry_id=0
            )
            db.add(channel)
            db.commit()
            db.refresh(channel)
            
            # Create API keys
            write_key = ApiKey(
                channel_id=channel.id,
                key=generate_api_key(),
                type="write",
                is_active=True
            )
            read_key = ApiKey(
                channel_id=channel.id,
                key=generate_api_key(),
                type="read",
                is_active=True
            )
            db.add(write_key)
            db.add(read_key)
            db.commit()
            
            print(f"✓ Created channel: {channel.name}")
            print(f"  Write key: {write_key.key}")
            print(f"  Read key: {read_key.key}")
            
            # Generate sample data for the last 7 days
            print(f"  Generating sample data...")
            now = datetime.utcnow()
            
            for i in range(168):  # 168 hours = 7 days
                timestamp = now - timedelta(hours=168-i)
                
                channel.last_entry_id += 1
                
                # Generate realistic random data based on channel type
                if "Температур" in channel.name:
                    field1 = 20 + random.uniform(-5, 10) + 5 * random.sin(i / 12)  # Temperature
                    field2 = 50 + random.uniform(-10, 10)  # Humidity
                    feed = Feed(
                        channel_id=channel.id,
                        entry_id=channel.last_entry_id,
                        created_at=timestamp,
                        field1=round(field1, 2),
                        field2=round(field2, 2)
                    )
                elif "воздуха" in channel.name:
                    field1 = 400 + random.uniform(-100, 200)  # CO2
                    field2 = 10 + random.uniform(-5, 15)  # PM2.5
                    field3 = 20 + random.uniform(-10, 30)  # PM10
                    feed = Feed(
                        channel_id=channel.id,
                        entry_id=channel.last_entry_id,
                        created_at=timestamp,
                        field1=round(field1, 2),
                        field2=round(field2, 2),
                        field3=round(field3, 2)
                    )
                else:  # Weather station
                    field1 = 15 + random.uniform(-10, 15) + 8 * random.sin(i / 24)  # Temperature
                    field2 = 1013 + random.uniform(-20, 20)  # Pressure
                    field3 = 60 + random.uniform(-20, 20)  # Humidity
                    feed = Feed(
                        channel_id=channel.id,
                        entry_id=channel.last_entry_id,
                        created_at=timestamp,
                        field1=round(field1, 2),
                        field2=round(field2, 2),
                        field3=round(field3, 2)
                    )
                
                db.add(feed)
            
            db.commit()
            print(f"  ✓ Generated {channel.last_entry_id} data points\n")
        
        print("✓ Sample data creation complete!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_data()

