import pandas as pd
try:
    df = pd.read_excel(r'c:\Users\ALIENWARE\Projects\helpU\bookkeeper\docs\HSN_SAC.xlsx')
    print("Columns:", df.columns.tolist())
    print("\nFirst 5 rows:")
    print(df.head())
except Exception as e:
    print(f"Error: {e}")
