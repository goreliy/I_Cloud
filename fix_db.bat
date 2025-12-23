@echo off
echo Fixing database...
del thingspeak.db
python init_db.py
alembic stamp head
echo Database fixed! Run: python run.py



















