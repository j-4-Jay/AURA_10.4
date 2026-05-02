import os
import glob
import time
import polars as pl

# [AURA-STRICT-PROTOCOL] Enforcing rigid directory structures
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_LANDING = os.path.join(BASE_DIR, "csv_landing")
PARQUET_CAPSULES = os.path.join(BASE_DIR, "parquet_capsules")

os.makedirs(PARQUET_CAPSULES, exist_ok=True)

def convert_csv_to_parquet():
    print("[AURA] Engaging Phase 1: High-Speed Data Conversion Module (TSV Enabled)")
    
    csv_files = glob.glob(os.path.join(CSV_LANDING, "*.csv"))
    
    if not csv_files:
        print("[!] No CSV files found in 'csv_landing'. Aborting.")
        return

    print(f"[*] Detected {len(csv_files)} files. Commencing conversion...\n")
    
    total_start_time = time.time()
    
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(PARQUET_CAPSULES, f"{base_name}.parquet")
        
        print(f"-> Processing: {filename}")
        start_time = time.time()
        
        try:
            # 1. Read file using TAB separator. MT5 uses \t despite the .csv extension.
            df = pl.read_csv(
                file_path, 
                has_header=True,
                separator='\t', 
                infer_schema_length=0 
            )
            
            # Clean up MT5 header brackets
            df.columns = [col.replace('<', '').replace('>', '').strip().upper() for col in df.columns]
            
            # 2. Date/Time handling. Daily files often omit TIME.
            if "TIME" in df.columns:
                df = df.with_columns(
                    pl.concat_str([pl.col("DATE"), pl.col("TIME")], separator=" ").alias("DATETIME")
                )
                # MT5 Timeframes smaller than Daily
                datetime_col = pl.col("DATETIME").str.strptime(pl.Datetime, format="%Y.%m.%d %H:%M:%S", strict=False).forward_fill()
            else:
                # Daily Timeframe (No TIME column)
                datetime_col = pl.col("DATE").str.strptime(pl.Datetime, format="%Y.%m.%d", strict=False).forward_fill().alias("DATETIME")

            # 3. Cast core financial columns
            df = df.select([
                datetime_col,
                pl.col("OPEN").cast(pl.Float32, strict=False).forward_fill(),
                pl.col("HIGH").cast(pl.Float32, strict=False).forward_fill(),
                pl.col("LOW").cast(pl.Float32, strict=False).forward_fill(),
                pl.col("CLOSE").cast(pl.Float32, strict=False).forward_fill(),
                pl.col("TICKVOL").cast(pl.UInt32, strict=False).fill_null(0) if "TICKVOL" in df.columns else pl.lit(0).alias("TICKVOL"),
                pl.col("VOL").cast(pl.UInt32, strict=False).fill_null(0) if "VOL" in df.columns else pl.lit(0).alias("VOL"),
                pl.col("SPREAD").cast(pl.UInt16, strict=False).fill_null(0) if "SPREAD" in df.columns else pl.lit(0).alias("SPREAD")
            ])
            
            # Drop empty rows where casting failed completely
            df = df.drop_nulls()
            
            # 4. Write Parquet
            df.write_parquet(output_path, compression="snappy")
            
            elapsed = time.time() - start_time
            orig_size = os.path.getsize(file_path) / (1024 * 1024)
            new_size = os.path.getsize(output_path) / (1024 * 1024)
            compression_ratio = ((orig_size - new_size) / orig_size) * 100 if orig_size > 0 else 0
            
            print(f"   [+] Success: {elapsed:.2f}s | {orig_size:.2f}MB -> {new_size:.2f}MB ({compression_ratio:.1f}% reduced)")
            
        except Exception as e:
            print(f"   [!] Failed to process {filename}: {str(e)}")

    total_elapsed = time.time() - total_start_time
    print(f"\n[AURA] Data Pipeline Conversion Complete in {total_elapsed:.2f}s.")
    print("[AURA-STRICT-PROTOCOL] Phase 1 Module 1 VERIFIED AND LOCKED.")

if __name__ == "__main__":
    convert_csv_to_parquet()