import pandas as pd
import json
import os

def excel_to_json(xlsx_path, json_path):
    try:
        df = pd.read_excel(xlsx_path)
        # Ensure HSN_CD is treated as string and padded if necessary
        df['HSN_CD'] = df['HSN_CD'].astype(str).str.strip()
        
        # Create a dictionary of code -> description
        hsn_master = {}
        for _, row in df.iterrows():
            code = row['HSN_CD']
            desc = row['HSN_Description']
            hsn_master[code] = desc
            
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(hsn_master, f, indent=2)
        print(f"Successfully converted {len(hsn_master)} codes to {json_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    xlsx = r'c:\Users\ALIENWARE\Projects\helpU\bookkeeper\docs\HSN_SAC.xlsx'
    output = r'c:\Users\ALIENWARE\Projects\helpU\bookkeeper\docs\hsn_master.json'
    excel_to_json(xlsx, output)
