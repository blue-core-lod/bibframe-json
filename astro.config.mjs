import { readdirSync } from "node:fs";

import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import starlightLinksValidator from "starlight-links-validator";

import { artifacts } from "./src/integrations/artifacts.mjs";

const RESOURCES = ["Work", "Instance", "Hub", "Item"];

/** One sidebar entry per definition, resource types first. */
function definitions() {
  const names = readdirSync("./bibframe_json/schema/dialect")
    .filter((file) => file.endsWith(".json"))
    .map((file) => file.replace(".json", ""))
    // main.json is the dispatch between the four resource types rather than a
    // definition of its own.
    .filter((name) => name !== "main");
  const rest = names.filter((name) => !RESOURCES.includes(name)).sort();
  return [...RESOURCES, ...rest].map((name) => ({
    label: name,
    link: `/shape/${name}/`,
  }));
}

// A project page, so the site lives under a path. `base` is what puts
// public/schema/dialect.json at /bibframe-json/schema/dialect.json, which is
// the URL every $id in the repository claims.
export default defineConfig({
  site: "https://blue-core-lod.github.io",
  base: "/bibframe-json",
  trailingSlash: "always",
  integrations: [
    artifacts(),
    starlight({
      title: "bibframe-json",
      description:
        "One JSON shape for BIBFRAME: parse it without an RDF library.",
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/blue-core-lod/bibframe-json",
        },
      ],
      customCss: [
        "@fontsource/literata/latin-400.css",
        "@fontsource/literata/latin-400-italic.css",
        "@fontsource/literata/latin-600.css",
        // The shape page shows one title in two scripts inside a code block,
        // so Cyrillic is content here rather than a nicety.
        "@fontsource/literata/cyrillic-400.css",
        "@fontsource/ibm-plex-mono/latin-400.css",
        "@fontsource/ibm-plex-mono/latin-600.css",
        "@fontsource/ibm-plex-mono/cyrillic-400.css",
        "./src/styles/bibframe.css",
      ],
      sidebar: [
        { label: "Overview", link: "/" },
        { label: "The shape", link: "/shape/" },
        { label: "A CBD", link: "/cbd/" },
        { label: "Producing it", link: "/producing/" },
        { label: "Validating", link: "/validating/" },
        { label: "Checking an implementation", link: "/conformance/" },
        {
          // Built from the schema directory rather than listed, so a new
          // definition appears here without anyone remembering to add it.
          // The four resource types first, since those are the documents you
          // actually hold; the rest are what they nest.
          label: "Definitions",
          items: definitions(),
        },
      ],
      expressiveCode: {
        // Wrap rather than scroll. The long lines here are record values and
        // context URLs, data that cannot be shortened without falsifying it,
        // and a clipped @id reads as broken rather than scrollable.
        defaultProps: { wrap: true },
      },
      plugins: [
        starlightLinksValidator({
          // The artifact links point into public/, which the validator cannot
          // see because those are files rather than pages. It refuses
          // relative links outright, so they are exempted here and checked
          // instead by tests/test_artifacts.py against the built output.
          errorOnRelativeLinks: false,
        }),
      ],
    }),
  ],
});
