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

/** The published URL of an artifact, e.g. `schema/linked.json`. */
export const url = (path: string) => `${PUBLISHED}/${path}`;
