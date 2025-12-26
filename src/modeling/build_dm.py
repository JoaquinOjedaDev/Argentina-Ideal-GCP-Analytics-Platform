#!/usr/bin/env python3
from google.cloud import bigquery
from src.config import PROJECT_ID

def ensure_dm_dataset(project_id: str):
    """Crea el dataset dm si no existe."""
    client = bigquery.Client(project=project_id)
    dataset_id = f"{project_id}.dm"

    try:
        client.get_dataset(dataset_id)
        print("✅ Dataset 'dm' ya existe.")
    except Exception:
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"  # ajustá si usaste otra región
        client.create_dataset(dataset)
        print("✅ Dataset 'dm' creado.")


def create_dm_tables(project_id: str):
    client = bigquery.Client(project=project_id)

    # ---------- DM FINANZAS (1 fila por cliente) ----------
    # Campos:
    # ciudad, cliente_id, cuit, deuda_vencida, distribuidor,
    # filtro_distribuidor, filtro_provincia, nombre_cliente,
    # provincia, telefono
    sql_finanzas = f"""
    CREATE OR REPLACE TABLE `{project_id}.dm.finanzas` AS
    SELECT DISTINCT
      c.ciudad                                   AS ciudad,          -- cliente
      c.cliente_id                               AS cliente_id,
      c.cuit                                     AS cuit,
      c.deuda_vencida                            AS deuda_vencida,
      c.distribuidor                             AS distribuidor,
      d.filtro_distribuidor                      AS filtro_distribuidor,
      c.provincia                                AS filtro_provincia, -- provincia del cliente
      c.nombre_cliente                           AS nombre_cliente,
      c.provincia                                AS provincia,       -- cliente
      c.telefono                                 AS telefono
    FROM `{project_id}.dwh.dim_cliente` c
    JOIN `{project_id}.dwh.dim_distribuidor` d
      ON c.distribuidor = d.distribuidor
    ;
    """

    # ---------- DM LOGÍSTICA (stock por fecha / distribuidor / producto) ----------
    # Campos:
    # ciudad, distribuidor, fecha_cierre, filtro_distribuidor,
    # filtro_provincia, producto, provincia, sku, stock, unidad
    sql_logistica = f"""
    CREATE OR REPLACE TABLE `{project_id}.dm.logistica` AS
    SELECT
      s.ciudad                                   AS ciudad,          -- sucursal
      fs.distribuidor                            AS distribuidor,
      fs.fecha_cierre                            AS fecha_cierre,
      d.filtro_distribuidor                      AS filtro_distribuidor,
      d.filtro_provincia                         AS filtro_provincia,
      p.producto                                 AS producto,
      s.provincia                                AS provincia,       -- sucursal
      fs.sku                                     AS sku,
      fs.stock                                   AS stock,
      p.unidad                                   AS unidad
    FROM `{project_id}.dwh.fact_stock` fs
    JOIN `{project_id}.dwh.dim_sucursal` s
      ON fs.sucursal_id = s.sucursal_id
    JOIN `{project_id}.dwh.dim_distribuidor` d
      ON fs.distribuidor = d.distribuidor
    JOIN `{project_id}.dwh.dim_producto` p
      ON fs.sku = p.sku
    WHERE fs.fecha_cierre BETWEEN DATE '2025-08-24' AND DATE '2025-11-17'
    ORDER BY
      fs.fecha_cierre,
      fs.distribuidor,
      p.producto
    ;
    """

    # ---------- DM MARKETING (ventas semanales por distribuidor / producto / provincia) ----------
    # Campos:
    # ciudad, distribuidor, filtro_distribuidor, filtro_provincia,
    # monto_total, producto, provincia, semana, semana_inicio,
    # venta_unidades_total
    sql_marketing = f"""
    CREATE OR REPLACE TABLE `{project_id}.dm.marketing` AS
    SELECT
      c.ciudad                                   AS ciudad,
      v.distribuidor                             AS distribuidor,
      d.filtro_distribuidor                      AS filtro_distribuidor,
      d.filtro_provincia                         AS filtro_provincia,
      SUM(v.venta_importe)                       AS monto_total,
      p.producto                                 AS producto,
      c.provincia                                AS provincia,
      f.semana                                   AS semana,
      f.semana_inicio                            AS semana_inicio,
      SUM(v.venta_unidades)                      AS venta_unidades_total
    FROM `{project_id}.dwh.fact_ventas` v
    JOIN `{project_id}.dwh.dim_cliente` c
      ON v.cliente_id = c.cliente_id
    JOIN `{project_id}.dwh.dim_distribuidor` d
      ON v.distribuidor = d.distribuidor
    JOIN `{project_id}.dwh.dim_producto` p
      ON v.sku = p.sku
    JOIN `{project_id}.dwh.dim_fecha` f
      ON v.fecha_cierre = f.fecha_cierre
    WHERE v.fecha_cierre BETWEEN DATE '2025-08-24' AND DATE '2025-11-17'
      AND f.semana BETWEEN 35 AND 46
    GROUP BY
      c.ciudad,
      v.distribuidor,
      d.filtro_distribuidor,
      d.filtro_provincia,
      p.producto,
      c.provincia,
      f.semana,
      f.semana_inicio
    ORDER BY
      f.semana_inicio,
      v.distribuidor,
      p.producto
    ;
    """

    queries = [
        ("dm.finanzas", sql_finanzas),
        ("dm.logistica", sql_logistica),
        ("dm.marketing", sql_marketing),
    ]

    for name, sql in queries:
        print(f"▶ Creando/reemplazando {name} ...")
        job = client.query(sql)
        job.result()
        print(f"✅ {name} OK")


if __name__ == "__main__":
    ensure_dm_dataset(PROJECT_ID)
    create_dm_tables(PROJECT_ID)
    print("\n✨ Data Marts construidos correctamente.")