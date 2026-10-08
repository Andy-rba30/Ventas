export function cn(...clases: (string | false | null | undefined)[]): string {
  return clases.filter(Boolean).join(" ");
}
