import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://pysetu.io";
  const routes = [
    { path: "", changeFrequency: "daily" as const, priority: 1.0 },
    { path: "/developer-portal", changeFrequency: "weekly" as const, priority: 0.9 },
    { path: "/whitepaper", changeFrequency: "monthly" as const, priority: 0.9 },
    { path: "/blog", changeFrequency: "daily" as const, priority: 0.8 },
    { path: "/legal/security", changeFrequency: "monthly" as const, priority: 0.6 },
    { path: "/terms", changeFrequency: "monthly" as const, priority: 0.5 },
    { path: "/privacy", changeFrequency: "monthly" as const, priority: 0.5 },
    { path: "/cookies", changeFrequency: "monthly" as const, priority: 0.5 },
    { path: "/login", changeFrequency: "monthly" as const, priority: 0.4 },
  ];

  return routes.map((r) => ({
    url: `${baseUrl}${r.path}`,
    lastModified: new Date(),
    changeFrequency: r.changeFrequency,
    priority: r.priority,
  }));
}
