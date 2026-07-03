"""
exporter.py — Export des appels d'offres en Excel ou CSV
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger


class AOExporter:
    """Export des données scrapées vers Excel ou CSV."""

    def __init__(self):
        self.output_dir = Path(os.getenv("OUTPUT_DIR", "data/output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.format = os.getenv("OUTPUT_FORMAT", "excel").lower()

    def _build_filename(self, extension: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return self.output_dir / f"piter_ao_{timestamp}.{extension}"

    def export(self, records: list[dict]) -> Path:
        """
        Exporte la liste d'AO vers le format configuré dans .env.
        Retourne le chemin du fichier créé.
        """
        if not records:
            logger.warning("Aucune donnée à exporter.")
            return None

        df = pd.DataFrame(records)
        df = self._clean_dataframe(df)

        if self.format == "csv":
            return self._to_csv(df)
        else:
            return self._to_excel(df)

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoyage basique avant export."""
        # Supprime les doublons sur le lien
        df = df.drop_duplicates(subset=["lien"], keep="first")

        # Trie par date de publication décroissante
        if "date_publication" in df.columns:
            df = df.sort_values("date_publication", ascending=False, na_position="last")

        df = df.reset_index(drop=True)
        logger.info(f"{len(df)} appels d'offres uniques après déduplication")
        return df

    def _to_excel(self, df: pd.DataFrame) -> Path:
        filepath = self._build_filename("xlsx")

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Appels d'offres")

            # Mise en forme basique
            ws = writer.sheets["Appels d'offres"]
            for col in ws.columns:
                max_len = max(
                    len(str(cell.value or "")) for cell in col
                )
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

        logger.success(f"✅ Export Excel : {filepath}")
        return filepath

    def _to_csv(self, df: pd.DataFrame) -> Path:
        filepath = self._build_filename("csv")
        df.to_csv(filepath, index=False, encoding="utf-8-sig")  # utf-8-sig pour Excel FR
        logger.success(f"✅ Export CSV : {filepath}")
        return filepath
