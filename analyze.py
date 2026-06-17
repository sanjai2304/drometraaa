import pandas as pd
import numpy as np
import os

filepath = r"d:\croud project\dataset\Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
df = pd.read_csv(filepath)

summary_path = r"d:\croud project\dataset_summary.txt"
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("=== DATASET SHAPE ===\n")
    f.write(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}\n\n")
    
    f.write("=== COLUMN INFO ===\n")
    missing = df.isnull().sum()
    duplicates = df.duplicated().sum()
    f.write(f"Duplicate rows: {duplicates}\n\n")
    
    info_df = pd.DataFrame({
        'Data Type': df.dtypes.astype(str),
        'Missing Values': missing,
        'Missing %': (missing / len(df)) * 100
    })
    f.write(info_df.to_string())
    f.write("\n\n")
    
    f.write("=== SAMPLE DATA ===\n")
    cols_to_show = ['id', 'event_type', 'latitude', 'longitude', 'event_cause', 'priority', 'status', 'start_datetime', 'corridor', 'police_station']
    cols_to_show = [c for c in cols_to_show if c in df.columns]
    f.write(df[cols_to_show].head(5).to_string())
    f.write("\n\n")
    
    f.write("=== VALUE COUNTS FOR ALL CATEGORICALS ===\n")
    for col in df.select_dtypes(include=['object', 'bool']).columns:
        unique_cnt = df[col].nunique()
        f.write(f"\nValue counts for {col} (Unique values: {unique_cnt}):\n")
        f.write(df[col].value_counts().head(20).to_string())
        f.write("\n")
        
    f.write("\n=== NUMERICAL DESCRIBE ===\n")
    f.write(df.describe().to_string())
    f.write("\n")

print("Analysis written to dataset_summary.txt successfully!")
