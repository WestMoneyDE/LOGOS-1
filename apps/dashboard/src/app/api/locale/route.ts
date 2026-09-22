import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const { locale } = await req.json();
  const l = locale === "en" ? "en" : "de";
  const res = NextResponse.json({ locale: l });
  res.cookies.set("logos_locale", l, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
  return res;
}
