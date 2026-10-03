import artifacts from "../../../artifacts.json";

/**
 * Where the artifacts are published.
 *
 * A link to a schema is written as its full URL rather than as a path,
 * because that URL is the schema's own `$id`: it is the thing a reader needs
 * to copy, and a relative path is not. Read from artifacts.json so the value
 * exists once, and so generate/rebase.py moves it along with every $id.
 */
export const PUBLISHED = artifacts.base;

/** The published URL of an unversioned artifact, e.g. `example/linked.json`. */
export const url = (path: string) => `${PUBLISHED}/${path}`;

/** The artifact version the context and the schemas are published under. */
export const VERSION = artifacts.version;

/**
 * The published URL of a versioned artifact, e.g. `schema/linked.json`.
 *
 * Separate from `url` because only the context and the schemas carry a
 * version: example/ and conformance/ track the current one. Built from
 * artifacts.json so the segment is written down once -- a page that spelled
 * it out itself went on linking to the unversioned path after the version
 * arrived, and every one of those links 404'd.
 */
export const versioned = (path: string) => `${PUBLISHED}/${VERSION}/${path}`;
