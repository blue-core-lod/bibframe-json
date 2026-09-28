/**
 * Where LC's BIBFRAME primer explains each definition.
 *
 * Hand-curated editorial data: eleven of the fifteen definitions have a
 * counterpart there. Ref, Text, Resource and main are artefacts of this shape
 * rather than parts of the model, and Classification has no section of its
 * own. Moved here from generate/site.py, unchanged.
 *
 * We say how to write a description down. The primer says what to describe.
 */
const BASE = "https://bibframe.org/docs/view/documentation-bf-primer/";
const CLASSES = "data-model-resource-description-classes/";
const COMMON = "data-model-common-properties-and-classes/";

export const PRIMER: Record<string, string> = {
  "Work.json": BASE + CLASSES + "works.md",
  "Instance.json": BASE + CLASSES + "instances.md",
  "Item.json": BASE + CLASSES + "items.md",
  "Hub.json": BASE + CLASSES + "hubs.md",
  "AdminMetadata.json": BASE + COMMON + "administrative-metadata.md",
  "Contribution.json": BASE + COMMON + "contributions-and-contributors.md",
  "Identifier.json": BASE + COMMON + "identifiers.md",
  "Note.json": BASE + COMMON + "notes.md",
  "ProvisionActivity.json": BASE + COMMON + "provision-activity.md",
  "Relation.json": BASE + COMMON + "relationships.md",
  "Title.json": BASE + COMMON + "titles.md",
};
