// Solo adapta sintaxis habitual de notas. No es un compilador LaTeX completo.
// Codigo, frontmatter y formulas ya delimitadas se conservan.
export function normalizeNote(text: string): string {
  let out = '';
  let i = 0;
  const front = /^---\r?\n[\s\S]*?\r?\n(?:---|\.\.\.)(?:\r?\n|$)/.exec(text);
  if (front) { out = front[0]; i = front[0].length; }
  const closing = (delimiter: string, from: number) => {
    let pos = text.indexOf(delimiter, from);
    while (pos >= 0) {
      let k = pos - 1;
      while (k >= 0 && text[k] === '\\') k--;
      if ((pos - 1 - k) % 2 === 0) return pos;
      pos = text.indexOf(delimiter, pos + delimiter.length);
    }
    return -1;
  };
  while (i < text.length) {
    const rest = text.slice(i);
    if (i === 0 || text[i - 1] === '\n') {
      const fence = /^ {0,3}(`{3,}|~{3,})[^\n]*(?:\n|$)/.exec(rest);
      if (fence) {
        const run = fence[1];
        const tail = rest.slice(fence[0].length);
        const end = new RegExp('^ {0,3}' + run[0] + '{' + run.length + ',}[ \\t]*(?:\\n|$)', 'm').exec(tail);
        const n = end ? fence[0].length + end.index + end[0].length : rest.length;
        out += rest.slice(0, n); i += n; continue;
      }
      if (rest.startsWith('    ') || rest.startsWith('\t')) {
        const end = rest.indexOf('\n');
        const n = end < 0 ? rest.length : end + 1;
        out += rest.slice(0, n); i += n; continue;
      }
    }
    if (text[i] === '`') {
      const run = /^`+/.exec(rest)![0];
      const end = new RegExp('(?<!`)' + run + '(?!`)').exec(rest.slice(run.length));
      if (end) {
        const n = run.length + end.index + end[0].length;
        out += rest.slice(0, n); i += n; continue;
      }
    }
    if (text[i] === '$') {
      const delimiter = rest.startsWith('$$') ? '$$' : '$';
      const j = closing(delimiter, i + delimiter.length);
      if (j >= 0) {
        out += text.slice(i, j + delimiter.length); i = j + delimiter.length; continue;
      }
    }
    if (rest.startsWith('\\(') || rest.startsWith('\\[')) {
      const display = rest.startsWith('\\[');
      const j = closing(display ? '\\]' : '\\)', i + 2);
      if (j >= 0) {
        const body = text.slice(i + 2, j).trim();
        out += display ? '\n\n$$\n' + body + '\n$$\n\n' : '$' + body + '$';
        i = j + 2; continue;
      }
    }
    const env = /^\\begin\{(equation\*?|displaymath|align\*?|gather\*?|multline\*?)\}/.exec(rest);
    if (env) {
      const endMark = '\\end{' + env[1] + '}';
      const j = text.indexOf(endMark, i + env[0].length);
      if (j >= 0) {
        let body = text.slice(i + env[0].length, j).trim();
        const name = env[1].replace(/\*$/, '');
        const inner = ({ align: 'aligned', gather: 'gathered', multline: 'gathered' } as Record<string, string>)[name];
        if (inner) body = '\\begin{' + inner + '}\n' + body + '\n\\end{' + inner + '}';
        out += '\n\n$$\n' + body + '\n$$\n\n';
        i = j + endMark.length; continue;
      }
    }
    const heading = /^\\(section|subsection|subsubsection|paragraph)\*?\s*\{/.exec(rest);
    if (heading) {
      const start = i + heading[0].length;
      let j = start, depth = 1;
      while (j < text.length && depth) {
        if (text[j] === '\\') { j += 2; continue; }
        if (text[j] === '{') depth++;
        if (text[j] === '}') depth--;
        j++;
      }
      if (depth === 0) {
        const level = ({ section: 1, subsection: 2, subsubsection: 3, paragraph: 4 } as Record<string, number>)[heading[1]];
        out = out.replace(/^ {0,3}#{1,6}[ \t]+$/m, '');
        out += '\n\n' + '#'.repeat(level) + ' ' + normalizeNote(text.slice(start, j - 1)).trim().replace(/\n/g, ' ') + '\n\n';
        i = j;
        while (i < text.length && /[ \t]/.test(text[i])) i++;
        continue;
      }
    }
    if (text[i] === '\\' && i + 1 < text.length) {
      out += text.slice(i, i + 2); i += 2; continue;
    }
    out += text[i++];
  }
  return out;
}

// Las imagenes del migrador existente pertenecen a este bucket y proyecto.
// No intentar abrir rutas de Windows desde el navegador ni sitios externos.
export function repositoryImageUrl(src: string | undefined, base: string): string | null {
  if (!src || !/^https:\/\//i.test(src)) return null;
  try {
    const url = new URL(src);
    if (url.origin !== new URL(base).origin || url.username || url.password) return null;
    const prefix = '/storage/v1/object/public/repository-images/';
    return url.pathname.startsWith(prefix) && url.pathname.length > prefix.length ? url.href : null;
  } catch { return null; }
}
