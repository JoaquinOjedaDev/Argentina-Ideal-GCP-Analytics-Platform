#!/usr/bin/env python3
"""
Pipeline end-to-end Argentina Ideal (Cloud Shell)

(Carga de Datos a GCP)

Orden de ejecución:
  1) load_raw_all.py    -> carga capa RAW (Maestro, Ventas, Stock) en BigQuery
  2) build_dwh.py       -> construye dimensiones y hechos en dwh
  3) build_dm.py        -> construye data marts en dm
"""

import subprocess
import sys

def run_step(name: str, module: str):
    print(f"\n▶ {name}")
    subprocess.run([sys.executable, "-m", module], check=True)

def main():
    run_step("1) Cargar RAW", "src.ingestion.load_raw_all")
    run_step("2) Construir DWH", "src.modeling.build_dwh")
    run_step("3) Construir DM", "src.modeling.build_dm")
    print("\n✅ Pipeline ejecutado correctamente.\n")

if __name__ == "__main__":
    main()
