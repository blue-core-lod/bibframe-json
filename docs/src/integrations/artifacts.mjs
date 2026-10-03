import { cp, mkdir, rm } from "node:fs/promises";
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
 *
 * Each target is emptied first. `public/` is not cleaned between builds, so
 * without that a tree that moves -- schema/ becoming v0/schema/ -- leaves its
 * old copy behind and the site goes on serving artifacts at a path nothing
 * claims any more. The stale copy is the dangerous kind of wrong: it is a
 * real schema, served at a URL its own $id denies.
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
          // The first segment, so moving schema/ to v0/schema/ clears the old
          // schema/ as well as the new target.
          const top = to.split("/")[0];
          await rm(`${publicDir}/${top}`, { recursive: true, force: true });
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
