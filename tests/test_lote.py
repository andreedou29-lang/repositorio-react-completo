"""Pruebas sin conexion de red: py -3 -m unittest discover -s tests -p test_lote.py"""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from migrar_obsidian import Config, Migrador
from convertir_nota import ejecutar, ruta_pdf
from lote_obsidian import bloqueo, ejecutar_lote
import lote_obsidian
from normalizar_latex import normalizar_latex
from fake_supabase import Client


class LoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = self.root / 'vault'; self.vault.mkdir()
        self.output = self.root / 'pdfs'; self.output.mkdir()
        self.config = Config('https://example.invalid', 'SECRET_TEST', self.vault, self.output, 'fake')
        self.client = Client()
        self.calls = []
        self.failure = None
        self.migrador = Migrador(self.client, self.config, self.convert)

    def note(self, name, content='Contenido $x=1$.'):
        p = self.vault / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return p

    def convert(self, **args):
        note = args['nota']; self.calls.append(note.name)
        self.assertTrue((args['boveda_preparada'] / note.relative_to(self.vault)).exists())
        if self.failure: self.failure(note)
        pdf = ruta_pdf(self.vault, note, self.output)
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(b'%PDF-simulado\n' + note.read_bytes())
        return pdf

    def run_batch(self, files=None, force=False):
        with redirect_stdout(io.StringIO()):
            return ejecutar_lote(self.migrador, files or list(self.migrador.archivos()), force, {'test': '1'})

    def report(self):
        return json.loads((self.output/'informe_migracion.json').read_text())

    def test_continua_error_y_reanuda_una_copia_por_lote(self):
        files = [self.note(x) for x in ['A.md','B.md','C.md']]
        def fail(p):
            if p.name=='B.md': raise RuntimeError('Fallo simulado SECRET_TEST')
        self.failure = fail
        with patch.object(lote_obsidian, 'preparar_boveda', wraps=lote_obsidian.preparar_boveda) as prepare:
            self.assertEqual(self.run_batch(files),1)
            self.assertEqual(prepare.call_count,1)
        report = self.report()
        self.assertEqual(report['resumen'],{'sincronizado':2,'error':1})
        self.assertNotIn('SECRET_TEST',json.dumps(report))
        before = len(self.client.events); self.calls.clear(); self.failure = None
        self.assertEqual(self.run_batch(files),0)
        self.assertEqual(self.calls,['B.md'])
        self.assertEqual(self.report()['resumen'],{'sin_cambios':2,'sincronizado':1})
        self.assertGreater(len(self.client.events),before)
        self.assertEqual(len(self.client.rows['documents']),3)

    def test_interrupcion_y_reanudacion(self):
        files=[self.note(x) for x in ['A.md','B.md','C.md']]
        def fail(p):
            if p.name=='B.md': raise KeyboardInterrupt()
        self.failure=fail
        self.assertEqual(self.run_batch(files),130)
        self.assertEqual(self.report()['pendientes'],2)
        self.failure=None; self.calls.clear()
        self.assertEqual(self.run_batch(files),0)
        self.assertEqual(self.calls,['B.md','C.md'])

    def test_informe_incluye_causa_del_exportador_sin_credenciales(self):
        files=[self.note('A.md'),self.note('B.md')]
        def fail(p):
            if p.name == 'A.md':
                ejecutar([sys.executable, '-c',
                          "print('Failed to decode YAML frontmatter SECRET_TEST'); raise SystemExit(1)"],
                         self.root, self.output/'A.conversion.log')
        self.failure=fail
        self.assertEqual(self.run_batch(files),1)
        report=self.report()
        self.assertEqual(report['archivos'][0]['categoria'],'metadatos')
        self.assertIn('Failed to decode YAML frontmatter',report['archivos'][0]['detalle'])
        self.assertNotIn('SECRET_TEST',json.dumps(report))
        self.assertEqual(report['archivos'][1]['estado'],'sincronizado')

    def test_pdf_original_jerarquia_y_colision_de_nombres(self):
        self.note('A/Clase.md'); self.note('B/Clase.md')
        original=self.vault/'A/Clase.pdf';original.write_bytes(b'%PDF-original')
        self.assertEqual(self.run_batch(),0)
        self.assertEqual((self.output/'A/Clase.pdf').read_bytes(),original.read_bytes())
        self.assertTrue((self.output/'A/Clase.md.pdf').exists())
        self.assertTrue((self.output/'B/Clase.pdf').exists())
        docs=self.client.rows['documents']
        self.assertEqual(len(docs),3)
        self.assertEqual(len({d['folder_id'] for d in docs if d['extension']=='md'}),2)
        for d in docs:
            self.assertEqual(d['storage_path'],f"documents/{d['id']}.{d['extension']}")
        self.calls.clear()
        self.assertEqual(self.run_batch(),0)
        self.assertEqual(self.calls,[])

    def test_cambio_de_adjunto_invalida_cache(self):
        self.note('A.md')
        image=self.vault/'imagen.png';image.write_bytes(b'version1')
        self.assertEqual(self.run_batch(),0)
        self.calls.clear();image.write_bytes(b'version2')
        self.assertEqual(self.run_batch(),0)
        self.assertEqual(self.calls,['A.md'])

    def test_cambio_durante_conversion_no_publica(self):
        files=[self.note('A.md'),self.note('B.md')]
        self.failure=lambda _: files[0].write_text('Modificado durante compilacion')
        self.assertEqual(self.run_batch(files),1)
        self.assertEqual(self.client.events,[])
        self.assertFalse(self.report()['terminado'])
        self.assertIn('cambio',self.report()['error_general'])

    def test_fallo_subida_no_se_guarda_como_exito(self):
        files=[self.note('A.md')]
        self.client.fail='repository-pdfs'
        self.assertEqual(self.run_batch(files),1)
        self.assertFalse((self.output/'.estado_migracion.json').exists())
        self.assertEqual(self.client.rows['documents'],[])
        self.client.fail=None
        self.assertEqual(self.run_batch(files),0)

    def test_pdf_local_alterado_fuerza_reconversion(self):
        self.note('A.md');self.run_batch();self.calls.clear()
        (self.output/'A.pdf').write_bytes(b'alterado')
        self.assertEqual(self.run_batch(),0)
        self.assertEqual(self.calls,['A.md'])

    def test_registro_remoto_ausente_fuerza_reconversion(self):
        self.note('A.md');self.run_batch();self.calls.clear()
        self.client.rows['documents'].clear()
        self.assertEqual(self.run_batch(),0)
        self.assertEqual(self.calls,['A.md'])

    def test_bloqueo_y_liberacion(self):
        with bloqueo(self.output):
            with self.assertRaises(RuntimeError):
                with bloqueo(self.output): pass
        with bloqueo(self.output): pass

    def test_yamlfalso_sin_tocar_metadatos_codigo_ni_setext(self):
        raw='Texto\n\n---\n## Titulo\n\n>[!note] Texto\n\n---\n'
        fixed=normalizar_latex(raw)
        self.assertIn('---\n\n## Titulo',fixed)
        self.assertEqual(normalizar_latex(fixed),fixed)
        for text in ['---\ntitle: Clase\n---\nTexto\n', 'Titulo\n---\n\nTexto',
                     '```md\n---\n## literal\n```', '$$\n---\n## literal\n$$']:
            self.assertEqual(normalizar_latex(text),text)


if __name__=='__main__': unittest.main()
