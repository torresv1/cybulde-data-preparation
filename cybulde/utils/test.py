import pandas as pd

dev_df = pd.read_parquet("data/processed/dev.parquet")

print(dev_df.shape)
print(dev_df.head())