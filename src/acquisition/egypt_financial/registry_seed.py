import os
import uuid
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.acquisition.egypt_financial.models import Base, InstitutionRegistry, DiscoveryStatus

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to local SQLite if no Supabase Postgres URL is provided
    DATABASE_URL = "sqlite:///l6_evidence.db"

EXCEL_PATH = ".planning/sharia-compliance-chatbot/docs/Egypt_Financial_Institutions_COMPLETE.xlsx"

SECTOR_MAP = {
    '01_CBE_Banks': ('Banking', 'CBE'),
    '02_Capital_Market': ('Capital Market', 'FRA'),
    '03_Insurance': ('Insurance', 'FRA'),
    '04_NonBank_Financial': ('Non-Bank Financial', 'FRA')
}

def seed_registry():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        xls = pd.ExcelFile(EXCEL_PATH)
        for sheet_name, (sector, regulator) in SECTOR_MAP.items():
            df = pd.read_excel(xls, sheet_name)
            
            # Clean dataframe
            df = df.dropna(subset=['Name', 'Name (English)', 'Name (Arabic)'], how='all')
            
            for _, row in df.iterrows():
                name_val = str(row.get('Name', '')).strip()
                name_en = str(row.get('Name (English)', '')).strip()
                name_ar = str(row.get('Name (Arabic)', '')).strip()
                
                if name_en == 'nan' or not name_en: name_en = name_val if name_val != 'nan' else ''
                if name_ar == 'nan': name_ar = ''
                
                if not name_en and not name_ar:
                    continue
                
                # Check if it already exists
                existing = None
                if name_en:
                    existing = session.query(InstitutionRegistry).filter(InstitutionRegistry.name_en == name_en).first()
                if not existing and name_ar:
                    existing = session.query(InstitutionRegistry).filter(InstitutionRegistry.name_ar == name_ar).first()
                
                if not existing:
                    inst = InstitutionRegistry(
                        institution_id=str(uuid.uuid4()),
                        name_en=name_en,
                        name_ar=name_ar,
                        sector=sector,
                        regulator=regulator,
                        registry_source_url="Egypt_Financial_Institutions_COMPLETE.xlsx",
                        registry_source_date=datetime.utcnow()
                    )
                    session.add(inst)
        
        session.commit()
        print("Database seeded successfully with institution registry.")
    except Exception as e:
        session.rollback()
        print(f"Error seeding database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_registry()
