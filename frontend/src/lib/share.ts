/** Texto para WhatsApp: título en negrita (formato de WhatsApp: *negrita*) y bloques
 *  separados por una línea en blanco, para que llegue legible sin editarlo a mano.
 *  Los bloques vacíos se omiten. Sin emojis (astral/4 bytes): wa.me los corrompe. */
export const bold = (text: string) => `*${text}*`;

export function shareText(title: string, ...blocks: string[][]): string {
  return [[bold(title)], ...blocks]
    .filter((block) => block.length > 0)
    .map((block) => block.join("\n"))
    .join("\n\n");
}

/** Lista con viñeta y detalle indentado debajo: "• Partido" / "    quiénes". */
export const bulletWithDetail = (label: string, detail: string) => `• ${label}\n    ${detail}`;
