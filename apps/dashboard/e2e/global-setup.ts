import * as fs from "fs";
import * as path from "path";

/** Remove the route-inventory shards of previous runs so /system/qa always shows exactly one matrix. */
export default async function globalSetup() {
  const dir = path.join(process.cwd(), "e2e", "results");
  if (!fs.existsSync(dir)) return;
  for (const f of fs.readdirSync(dir)) {
    if (f.startsWith("route-inventory")) fs.unlinkSync(path.join(dir, f));
  }
}
