#!/usr/bin/env python3
"""
Carga completa capa RAW en BigQuery desde GCS:

- raw.Maestro
- raw.Ventas
- raw.Stock

"""

from google.cloud import bigquery, storage
from google.api_core.exceptions import NotFound, Forbidden # type: ignore
from src.config import PROJECT_ID, BUCKET

DATASET = "raw"

client_bq = bigquery.Client(project=PROJECT_ID)
client_gcs = storage.Client(project=PROJECT_ID)


def list_uris(filter_substring: str):
    """Lista todas las URIs de GCS que contienen cierto substring en el path."""
    blobs = client_gcs.list_blobs(BUCKET, prefix="data/")
    uris = [
        f"gs://{BUCKET}/{b.name}"
        for b in blobs
        if filter_substring in b.name
    ]
    if not uris:
        raise SystemExit(f"No se encontraron archivos con patrón: {filter_substring}")
    print(f"\nArchivos para '{filter_substring}':")
    for u in uris:
        print(" -", u)
    return uris


def load_csv_to_bq(table_id: str, uris, write_disposition="WRITE_TRUNCATE"):
    """Carga uno o varios CSV de GCS en una tabla de BigQuery."""
    print(f"\nCargando {len(uris)} archivos en {table_id} ...")

    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=write_disposition,
        field_delimiter=",",
        encoding="UTF-8",
        allow_quoted_newlines=True,
        allow_jagged_rows=True,
    )

    try:
        job = client_bq.load_table_from_uri(uris, table_id, job_config=job_config)
        job.result()
    except NotFound as e:
        raise SystemExit(
            f"❌ NotFound cargando {table_id}. "
            f"Verificá que exista el dataset y el proyecto.\n{e}"
        )
    except Forbidden as e:
        print("❌ Forbidden: BigQuery no puede leer el bucket.")
        print("Revisá IAM del bucket. Ejemplo de fix:")
        print(
            "  gcloud storage buckets add-iam-policy-binding "
            f"gs://{BUCKET} \\"
        )
        print(
            "    --member='serviceAccount:service-[PROJECT_NUMBER]@bigquery-encryption.iam.gserviceaccount.com' \\"
        )
        print("    --role='roles/storage.objectViewer'")
        raise

    tbl = client_bq.get_table(table_id)
    print(f"✅ {tbl.num_rows} filas cargadas en {table_id}")


def ensure_dataset(dataset_id: str):
    """Crea el dataset si no existe."""
    full_id = f"{PROJECT_ID}.{dataset_id}"
    try:
        client_bq.get_dataset(full_id)
        print(f"Dataset {full_id} ya existe.")
    except NotFound:
        print(f"Creando dataset {full_id} ...")
        ds = bigquery.Dataset(full_id)
        ds.location = "US"
        client_bq.create_dataset(ds)
        print(f"✅ Dataset {full_id} creado.")


def main():
    # Asegurar dataset RAW
    ensure_dataset(DATASET)

    # -------- Maestro --------
    maestro_uris = list_uris("/maestro/Maestro_")
    load_csv_to_bq(
        table_id=f"{PROJECT_ID}.{DATASET}.Maestro",
        uris=maestro_uris,
        write_disposition="WRITE_TRUNCATE",
    )

    # -------- Ventas --------
    ventas_uris = list_uris("/ventas/Venta_Clientes_")
    load_csv_to_bq(
        table_id=f"{PROJECT_ID}.{DATASET}.Ventas",
        uris=ventas_uris,
        write_disposition="WRITE_TRUNCATE",
    )

    # -------- Stock --------
    stock_uris = list_uris("/stock/StockPeriodo_")
    load_csv_to_bq(
        table_id=f"{PROJECT_ID}.{DATASET}.Stock",
        uris=stock_uris,
        write_disposition="WRITE_TRUNCATE",
    )

    print("\n✨ Capa RAW cargada correctamente (Maestro, Ventas, Stock).")


if __name__ == "__main__":
    main()