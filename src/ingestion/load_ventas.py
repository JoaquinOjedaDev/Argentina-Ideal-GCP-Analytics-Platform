from google.cloud import bigquery
from src.config import PROJECT_ID, BUCKET

DATASET = "raw"

# Tabla correcta: raw.Ventas
TABLE_ID = f"{PROJECT_ID}.{DATASET}.Ventas"

# Paths correctos: carpeta ventas y patrón Venta_Clientes_*.csv
URIS = [
    f"gs://{BUCKET}/data/distribuidor_1/ventas/Venta_Clientes_*.csv",
    f"gs://{BUCKET}/data/distribuidor_2/ventas/Venta_Clientes_*.csv",
    f"gs://{BUCKET}/data/distribuidor_3/ventas/Venta_Clientes_*.csv",
    f"gs://{BUCKET}/data/distribuidor_4/ventas/Venta_Clientes_*.csv",
    f"gs://{BUCKET}/data/distribuidor_5/ventas/Venta_Clientes_*.csv",
]


def main():
    client = bigquery.Client(project=PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition="WRITE_TRUNCATE",  # full reload
        field_delimiter=",",
        encoding="UTF-8",
        allow_quoted_newlines=True,
    )

    load_job = client.load_table_from_uri(URIS, TABLE_ID, job_config=job_config)
    print(f"Starting load job {load_job.job_id} for Ventas...")
    load_job.result()

    table = client.get_table(TABLE_ID)
    print(f"✅ Loaded {table.num_rows} rows into {TABLE_ID}")


if __name__ == "__main__":
    main()