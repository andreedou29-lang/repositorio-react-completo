import base64
import os
from pathlib import Path
import tempfile
import unittest

import pikepdf

from sincronizar_biblioteca import (
    MAX_FILE_SIZE,
    identificar_libros_obsoletos,
    partes_pdf_vigentes,
    preparar_pdf_para_subida,
)


class BookPdfPreparationTests(unittest.TestCase):
    def test_old_folder_book_is_removed_only_after_a_valid_current_path_exists(self):
        old = {
            "id": "old-id",
            "source_sha256": "same-content",
            "storage_path": "Analisis 1 y 2/book.pdf",
        }
        current = {
            "id": "current-id",
            "source_sha256": "same-content",
            "storage_path": "Analisis/Analisis 1/book.pdf",
            "title": "book",
            "size_bytes": 100,
        }
        rows = {
            "Analisis 1 y 2\\book.pdf": old,
            "Analisis\\Analisis 1\\book.pdf": current,
        }
        sources = {
            "Analisis\\Analisis 1\\book.pdf": ("same-content", 100),
        }

        self.assertEqual(
            identificar_libros_obsoletos(rows, sources),
            [("Analisis 1 y 2\\book.pdf", old)],
        )
        self.assertEqual(
            identificar_libros_obsoletos(
                {"Analisis 1 y 2\\book.pdf": old}, sources
            ),
            [],
        )
        self.assertEqual(
            identificar_libros_obsoletos(
                {"Otra carpeta\\book.pdf": old, **rows}, sources
            ),
            [("Analisis 1 y 2\\book.pdf", old)],
        )

    def test_large_legacy_parts_are_removed_only_when_current_parts_are_complete(self):
        current_path = "Algebra Lineal\\Algebra Lineal 1\\book.pdf"
        rows = {
            "Algebra Lineal 1 y 2\\book.pdf::sync-part-0001": {
                "id": "old-part-1",
                "source_sha256": "large-content",
                "storage_path": "old.part-1.pdf",
            },
            "Algebra Lineal 1 y 2\\book.pdf::sync-part-0002": {
                "id": "old-part-2",
                "source_sha256": "large-content",
                "storage_path": "old.part-2.pdf",
            },
            f"{current_path}::sync-part-0001": {
                "source_sha256": "large-content",
                "title": "book (Parte 1 de 2)",
                "size_bytes": 100,
            },
            f"{current_path}::sync-part-0002": {
                "source_sha256": "large-content",
                "title": "book (Parte 2 de 2)",
                "size_bytes": 200,
            },
        }

        obsolete = identificar_libros_obsoletos(
            rows, {current_path: ("large-content", MAX_FILE_SIZE + 1)}
        )
        self.assertEqual(
            [key for key, _ in obsolete],
            [
                "Algebra Lineal 1 y 2\\book.pdf::sync-part-0001",
                "Algebra Lineal 1 y 2\\book.pdf::sync-part-0002",
            ],
        )
        incomplete_rows = dict(rows)
        incomplete_rows.pop(f"{current_path}::sync-part-0002")
        self.assertEqual(
            identificar_libros_obsoletos(
                incomplete_rows, {current_path: ("large-content", MAX_FILE_SIZE + 1)}
            ),
            [],
        )

    def test_uploaded_parts_are_skipped_only_when_the_whole_sequence_matches(self):
        rows = {
            "book.pdf::sync-part-0001": {
                "source_sha256": "source",
                "title": "book (Parte 1 de 2)",
                "size_bytes": 100,
            },
            "book.pdf::sync-part-0002": {
                "source_sha256": "source",
                "title": "book (Parte 2 de 2)",
                "size_bytes": 200,
            },
        }
        self.assertTrue(partes_pdf_vigentes("book.pdf", "source", rows))
        self.assertFalse(
            partes_pdf_vigentes("book.pdf", "changed", rows)
        )
        first_key, first_row = next(iter(rows.items()))
        self.assertFalse(
            partes_pdf_vigentes(
                "book.pdf", "source", {first_key: first_row}
            )
        )

    def test_large_pdf_is_split_into_valid_ordered_parts_under_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "large.pdf"
            pdf = pikepdf.Pdf.new()
            for _ in range(3):
                page = pdf.add_blank_page(page_size=(200, 200))
                comments = [
                    b"%" + base64.b64encode(os.urandom(256)) + b"\n"
                    for _ in range(100)
                ]
                page.obj["/Contents"] = pdf.make_stream(b"".join(comments))
            pdf.save(source)

            limit = 70 * 1024
            parts = preparar_pdf_para_subida(source, root, max_bytes=limit)

            self.assertGreater(len(parts), 1)
            self.assertEqual(
                [(start, end) for _, start, end in parts],
                sorted((start, end) for _, start, end in parts),
            )
            pages = 0
            for path, start, end in parts:
                self.assertLessEqual(path.stat().st_size, limit)
                with pikepdf.open(path) as part:
                    self.assertEqual(len(part.pages), end - start + 1)
                    pages += len(part.pages)
            self.assertEqual(pages, 3)

    def test_single_page_larger_than_limit_fails_with_clear_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "single-page.pdf"
            pdf = pikepdf.Pdf.new()
            page = pdf.add_blank_page(page_size=(200, 200))
            page.obj["/Contents"] = pdf.make_stream(
                b"%" + base64.b64encode(os.urandom(8192)) + b"\n"
            )
            pdf.save(source)

            with self.assertRaisesRegex(RuntimeError, "pagina 1 ocupa mas del limite"):
                preparar_pdf_para_subida(source, root, max_bytes=1024)


if __name__ == "__main__":
    unittest.main()
