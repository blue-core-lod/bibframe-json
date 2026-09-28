import { docsLoader } from "@astrojs/starlight/loaders";
import { docsSchema } from "@astrojs/starlight/schema";
import { defineCollection } from "astro:content";

// Astro 5 and later need the collection declared before it will look in
// src/content/docs/ at all. Without this the build succeeds and produces
// nothing but a 404 page, which is a quiet way to fail.
export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
};
