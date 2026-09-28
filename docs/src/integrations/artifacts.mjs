import { cp, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import config from "../../../artifacts.json" with { type: "json" };

/**
 * Publish the schemas, the context and the conformance corpus.
 *
 * These are the product; the pages are how you find out about them. Each tree
 * lands at the path its own `$id`s name, which is what makes those `$id`s
 * resolvable and `{"$ref": "Ref.json"}` work over the network. The mapping
 * lives in artifacts.json so that tests/test_artifacts.py can check it rather
 * than restate it.
 *
 * Copied into `public/` at the start of a build rather than written to the
 * output directory at the end, so `astro dev` serves them too and the site
 * behaves the same either way.
 */
export function artifacts() {
  return {
    name: "bibframe-json:artifacts",
    hooks: {
      "astro:config:setup": async ({ config: astro, logger }) => {
        // The trees live in the repository, above the site. Resolved against
        // this file rather than against astro.root, which is docs/.
        const root = fileURLToPath(new URL("../../../", import.meta.url));
        const publicDir = fileURLToPath(astro.publicDir);
        for (const [from, to] of Object.entries(config.publish)) {
          await mkdir(`${publicDir}/${to}`, { recursive: true });
          await cp(`${root}/${from}`, `${publicDir}/${to}`, {
            recursive: true,
            // README.md next to a schema is for someone reading the
            // repository, not something to serve.
            filter: (path) =>
              !path.endsWith(".md") && !path.includes("__pycache__"),
          });
          logger.info(`published ${from} at /${to}`);
        }
      },
    },
  };
}
