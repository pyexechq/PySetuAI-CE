import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/platform/", "/accept-invite", "/auth/oidc/callback"],
      },
    ],
    sitemap: "https://pysetu.io/sitemap.xml",
  };
}
