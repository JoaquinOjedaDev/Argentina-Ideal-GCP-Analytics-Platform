#!/usr/bin/env python3
from google.cloud import bigquery
from src.config import PROJECT_ID

def ensure_dwh_dataset(project_id: str):
    """Crea el dataset dwh si no existe."""
    client = bigquery.Client(project=project_id)
    dataset_id = f"{project_id}.dwh"

    try:
        client.get_dataset(dataset_id)
        print("✅ Dataset 'dwh' ya existe.")
    except Exception:
        dataset = bigquery.Dataset(dataset_id)
        # Ajustá la región si tu proyecto está en otra
        dataset.location = "US"
        client.create_dataset(dataset)
        print("✅ Dataset 'dwh' creado.")


def create_dwh_tables(project_id: str):
    client = bigquery.Client(project=project_id)

    # ---------- DIMENSIONES ORIGINALES ----------

    sql_dim_sucursal = f"""
    CREATE OR REPLACE TABLE `{project_id}.dwh.dim_sucursal` AS
    SELECT DISTINCT
      ROW_NUMBER() OVER (ORDER BY sucursal) AS sucursal_id,
      sucursal,
      provincia,
      ciudad,
      tipo_negocio,
      distribuidor,
      coordenada_latitud,
      coordenada_longitud
    FROM `{project_id}.raw.Maestro`;
    """

    sql_dim_cliente = f"""
    CREATE OR REPLACE TABLE `{project_id}.dwh.dim_cliente` AS
    SELECT DISTINCT
      ROW_NUMBER() OVER (ORDER BY cliente) AS cliente_id,
      cliente,
      nombre_cliente,
      razon_social,
      cuit,
      telefono,
      provincia,
      ciudad,
      dia_visita,
      fecha_alta,
      fecha_baja,
      deuda_vencida,
      distribuidor
    FROM `{project_id}.raw.Maestro`;
    """

    sql_dim_producto = f"""
    CREATE OR REPLACE TABLE `{project_id}.dwh.dim_producto` AS
    SELECT DISTINCT
      producto,
      sku,
      unidad
    FROM `{project_id}.raw.Stock`;
    """

    # ---------- DIMENSIONES EXTRA PARA TUS DMs ----------

    # dim_distribuidor: base para ciudad / provincia / filtros compartidos
    sql_dim_distribuidor = f"""
    CREATE OR REPLACE TABLE `{project_id}.dwh.dim_distribuidor` AS
    SELECT
      distribuidor,
      ANY_VALUE(provincia) AS provincia,
      ANY_VALUE(ciudad)    AS ciudad,
      distribuidor         AS filtro_distribuidor,
      ANY_VALUE(provincia) AS filtro_provincia
    FROM `{project_id}.dwh.dim_sucursal`
    GROUP BY distribuidor;
    """

    # dim_fecha: base para semana y semana_inicio
    sql_dim_fecha = f"""
    CREATE OR REPLACE TABLE `{project_id}.dwh.dim_fecha` AS
    WITH fechas AS (
      SELECT DISTINCT fecha_cierre FROM `{project_id}.raw.Ventas`
      UNION DISTINCT
      SELECT DISTINCT fecha_cierre FROM `{project_id}.raw.Stock`
    )
    SELECT
      fecha_cierre,
      EXTRACT(ISOWEEK FROM fecha_cierre)         AS semana,
      DATE_TRUNC(fecha_cierre, WEEK(MONDAY))     AS semana_inicio
    FROM fechas;
    """

    # ---------- TABLAS DE HECHOS ----------

    sql_fact_ventas = f"""
    CREATE OR REPLACE TABLE `{project_id}.dwh.fact_ventas` AS
    SELECT
      ROW_NUMBER() OVER (ORDER BY v.fecha_cierre, v.cliente, v.sku) AS venta_id,
      s.sucursal_id,
      c.cliente_id,
      v.fecha_cierre,
      p.sku,
      v.condicion_venta,
      v.venta_unidades,
      v.venta_importe,
      c.distribuidor
    FROM `{project_id}.raw.Ventas` v
    LEFT JOIN `{project_id}.dwh.dim_sucursal` s
      ON v.sucursal = s.sucursal
    LEFT JOIN `{project_id}.dwh.dim_cliente` c
      ON v.cliente = c.cliente
    LEFT JOIN `{project_id}.dwh.dim_producto` p
      ON v.sku = p.sku;
    """

    sql_fact_stock = f"""
    CREATE OR REPLACE TABLE `{project_id}.dwh.fact_stock` AS
    SELECT
      suc.sucursal_id,
      s.fecha_cierre,
      s.sku,
      s.stock,
      s.distribuidor
    FROM `{project_id}.raw.Stock` s
    LEFT JOIN `{project_id}.dwh.dim_sucursal` suc
      ON s.sucursal = suc.sucursal;
    """

    queries = [
        ("dwh.dim_sucursal", sql_dim_sucursal),
        ("dwh.dim_cliente", sql_dim_cliente),
        ("dwh.dim_producto", sql_dim_producto),
        ("dwh.dim_distribuidor", sql_dim_distribuidor),
        ("dwh.dim_fecha", sql_dim_fecha),
        ("dwh.fact_ventas", sql_fact_ventas),
        ("dwh.fact_stock", sql_fact_stock),
    ]

    for name, sql in queries:
        print(f"▶ Creando/reemplazando {name} ...")
        job = client.query(sql)
        job.result()
        print(f"✅ {name} OK")


if __name__ == "__main__":
    ensure_dwh_dataset(PROJECT_ID)
    create_dwh_tables(PROJECT_ID)
    print("\n✨ DWH construido correctamente.")