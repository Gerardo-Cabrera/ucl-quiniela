// Detecta claves DUPLICADAS en los JSON de i18n. JSON.parse (y el import de Vite) se
// quedan con la última en silencio, así que un bloque repetido o una traducción pisada
// pasan sin error hasta que alguien lo nota en pantalla. Ocurrió al resolver a mano un
// conflicto de merge en es.json (bloque "backfill" dos veces). Corre en `npm run lint`,
// por lo tanto también en la CI. Sin dependencias: un recorrido mínimo del texto que
// solo distingue strings, ':' y llaves.
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const LOCALES_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "i18n", "locales");

/** Rutas (a.b.c) de las claves repetidas dentro del mismo objeto. */
function duplicateKeys(text) {
  const dups = [];
  const stack = [];      // por objeto abierto: Set de claves vistas
  const path = [];       // nombre bajo el que se abrió cada objeto (para el mensaje)
  let lastKey = null;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      let j = i + 1, s = "";
      while (text[j] !== '"') { s += text[j] === "\\" ? text[++j] : text[j]; j++; }
      let k = j + 1;
      while (/\s/.test(text[k])) k++;
      if (text[k] === ":" && stack.length) {           // es una clave, no un valor
        const keys = stack[stack.length - 1];
        if (keys.has(s)) dups.push([...path.slice(1), s].join("."));
        keys.add(s);
        lastKey = s;
      }
      i = j;
    } else if (ch === "{") {
      stack.push(new Set());
      path.push(lastKey ?? "");
      lastKey = null;
    } else if (ch === "}") {
      stack.pop();
      path.pop();
    }
  }
  return dups;
}

let failed = false;
for (const file of readdirSync(LOCALES_DIR).filter((f) => f.endsWith(".json"))) {
  const text = readFileSync(join(LOCALES_DIR, file), "utf8");
  JSON.parse(text);                                   // sintaxis: falla con el error de Node
  const dups = duplicateKeys(text);
  if (dups.length) {
    failed = true;
    console.error(`i18n: claves duplicadas en ${file}: ${dups.join(", ")}`);
  }
}
if (failed) process.exit(1);
console.log("i18n: sin claves duplicadas");
