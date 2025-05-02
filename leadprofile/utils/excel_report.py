# excel_report.py
"""
Gera a planilha Auditoria_da_busca_<nome>_<telefone>.xlsx                      ✓
"""
import pandas as pd                                        # pandas ExcelWriter :contentReference[oaicite:7]{index=7}
from io import BytesIO


def build_audit_excel(name, phone, ddd, data) -> BytesIO:
    df = pd.DataFrame([{
        "nome": name,
        "telefone": phone,
        "link_claro_ddd": data["url"],
        "ddd": ddd,
        "cidades": ", ".join(data["cities"]),
        "estado": data["state"]
    }])
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="auditoria")
    buffer.seek(0)
    return buffer
