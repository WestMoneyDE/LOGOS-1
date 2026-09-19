import { Alert, AlertDescription } from "@/components/ui/alert";

export function RecordsOnly({ text }: { text: string }) {
  return <Alert className="max-w-3xl"><AlertDescription>{text}</AlertDescription></Alert>;
}
