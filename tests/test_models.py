"""What the models do for a reader.

Whether they agree with the schema is asserted in test_conformance.py, against
the corpus, so that the question is put to any implementation rather than only
to this one.
"""

import json

import jsonschema
import pytest

from bibframe_json import EDTF, Item, Ref, Text, Work, schema, validate

DIALECT = schema("dialect")


@pytest.fixture(scope="module")
def dialect():
    return jsonschema.Draft202012Validator(DIALECT)


# --- what the models are for -------------------------------------------------


def test_a_literal_keeps_its_language():
    """The romanised and vernacular forms of one title stay distinguishable.

    `bluecore_api` currently joins them with a comma, so a record with both
    renders as though it had two different titles.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "title": [
                {"@type": ["Title"], "mainTitle": ["Trudy Instituta"]},
                {
                    "@type": ["Title"],
                    "mainTitle": [{"@value": "Труды", "@language": "ru-cyrl"}],
                },
            ],
        }
    )
    assert [str(t) for t in work.titles_in(None)] == ["Trudy Instituta"]
    assert [str(t) for t in work.titles_in("ru-cyrl")] == ["Труды"]


def test_a_literal_keeps_its_datatype():
    """EDTF encodes uncertainty, so reading it as a date would be wrong."""
    approximate = Text.model_validate({"@value": "199X", "@type": EDTF})
    exact = Text.model_validate("1994-03-01")
    assert approximate.approximate and not exact.approximate
    assert str(approximate) == "199X", "and still behaves as its text"


def test_the_models_parse_rather_than_judge():
    """A record breaking the shape rules still loads, deliberately.

    Required by JSON-LD and never seen in the data -- 703 value objects with a
    datatype, 68 with a language, none with both -- but the rule lives in
    schema/dialect.json rather than here. Enforcing a few rules in the models
    and the rest in the schema would make load() unpredictable, and would put
    each rule in two places since a validator never reaches
    model_json_schema().

    validate() is what reports it, and test_validate.py asserts that it does.
    """
    both = {"@value": "x", "@type": "xsd:string", "@language": "en"}
    text = Text.model_validate(both)
    assert text.datatype and text.language, "parsed, not judged"

    blank = Work.model_validate(
        {"@id": "https://x/1", "@type": ["Work"], "subject": [{"@id": "_:b0"}]}
    )
    assert blank.subject[0].uri == "_:b0", "likewise"


def test_main_title_prefers_a_title_over_a_variant():
    """What a template would otherwise write as work.title[0].main[0], with a
    check at every step, and every consumer would write again."""
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "title": [
                {"@type": ["VariantTitle"], "mainTitle": ["Proceedings"]},
                {"@type": ["Title"], "mainTitle": ["Trudy Instituta"]},
            ],
        }
    )
    assert str(work.main_title) == "Trudy Instituta"


def test_unmodelled_properties_survive():
    """BIBFRAME has 226 properties and the data uses 136; modelling a dozen and
    rejecting the rest would make these useless for anything else."""
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "tableOfContents": ["Chapter one -- Chapter two"],
        }
    )
    assert [str(v) for v in work.get("tableOfContents")] == [
        "Chapter one -- Chapter two"
    ]
    assert work.get("neverSeen") == []


def test_an_unmodelled_property_reads_like_a_modelled_one():
    """get() parses, so a consumer need not know which half a property is in.

    Returning raw JSON meant a template printing an unmodelled value got
    `{'@value': 'Труды', '@language': 'ru-cyrl'}` where a modelled one gave the
    text, and a bare URI had no `.uri` to link to.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "summary": [{"@value": "Труды", "@language": "ru-cyrl"}],
            "originPlace": [{"@id": "https://x/p"}],
        }
    )
    summary = work.get("summary")[0]
    assert (str(summary), summary.language) == ("Труды", "ru-cyrl")
    assert work.get("originPlace")[0].uri == "https://x/p"


def test_properties_covers_both_halves_of_an_open_model():
    """What a template iterates, and why model_extra alone will not do.

    model_extra holds only the unmodelled half, so a loop over it skips title
    and contribution entirely -- the bug waiting for anything that renders a
    record property by property.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "@context": {"@vocab": "http://x/"},
            "title": [{"@type": ["Title"], "mainTitle": ["A title"]}],
            "tableOfContents": ["Chapter one"],
        }
    )
    held = work.properties()
    assert "title" in held, "a modelled property"
    assert "tableOfContents" in held, "an unmodelled one"
    # keywords are not properties, and an empty property is omitted so a caller
    # can loop without checking
    assert "@context" not in held
    assert "@id" not in held and "@type" not in held
    assert "subject" not in held


def test_primary_contribution_is_found_by_its_extra_type():
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "contribution": [
                {"@type": ["Contribution"], "agent": ["https://x/a"]},
                {
                    "@type": ["Contribution", "PrimaryContribution"],
                    "agent": ["https://x/b"],
                },
            ],
        }
    )
    assert len(work.primary_contributions) == 1
    assert work.primary_contributions[0].agent[0].uri == "https://x/b"


def test_a_reference_renders_as_its_label_when_it_has_one():
    assert str(Ref.model_validate("https://x/1")) == "https://x/1"
    assert (
        str(Ref.model_validate({"@id": "https://x/1", "rdfs:label": ["Prokhorov"]}))
        == "Prokhorov"
    )


# --- the schema the models produce -------------------------------------------


def test_the_generated_schema_has_no_oneOf():
    """The payoff of pinning cardinality in the context first.

    With every property a list, the models are list[X] rather than
    X | list[X] | None, so there are no unions for the schema to spell out. The
    IIIF v3 schema has 38 oneOf and ships a 414-line error processor whose only
    job is working out which branch an error came from.
    """
    text = json.dumps(DIALECT)
    assert '"oneOf"' not in text
    assert '"allOf"' not in text


def test_the_hand_written_rules_are_present():
    """Guard against a regeneration quietly dropping them.

    These two cannot come from the models: a Pydantic validator never appears in
    model_json_schema(), so they are written in JSON Schema in generate/dialect.py
    and merged. If someone regenerates without that step the schema still looks
    fine and silently stops checking.
    """
    text = json.dumps(DIALECT)
    assert '"not"' in text, "the exclusions survived generation"
    assert "^_:" in text, "the blank node rule survived"
    assert DIALECT["$defs"]["Text"]["anyOf"][0]["type"] == [
        "string",
        "number",
        "boolean",
    ], "a literal may be a bare scalar"


# --- the shape that predates the context -------------------------------------

LEGACY = {
    "@id": "https://x/1",
    "@type": "Work",
    "title": {"@type": "Title", "mainTitle": "Trudy Instituta"},
    "subject": {"@id": "https://x/s"},
    "identifiedBy": {"@type": "Isbn", "rdf:value": "9781234"},
}


def test_the_models_accept_the_shape_that_predates_the_context():
    """The module docstring promises this, and only Text, Ref and @type kept it.

    Every declared list field raised on a single bare value, so a record written
    before the context parsed for its unmodelled properties -- Node.get has
    always tolerated a scalar -- and refused for its modelled ones, which is the
    opposite of useful. bluecore_api's view tests feed exactly this shape, and
    its views/nodes.py records that un-reframed rows outlive any backfill.
    """
    work = Work.model_validate(LEGACY)
    assert str(work.main_title) == "Trudy Instituta"
    assert work.types == ["Work"]
    assert work.subject[0].uri == "https://x/s"
    assert work.identified_by[0].kind == "Isbn"


def test_a_value_object_is_not_a_list_of_one():
    """Text must not inherit the coercion, and this is why it is not a Shape.

    A value object's @value is a scalar by definition, and its extra keys are
    keywords rather than properties -- the same line the dialect generator draws
    when it applies the array rule to nodes and not to Text.
    """
    text = Text.model_validate({"@value": "x", "@language": "ru"})
    assert (text.value, text.language) == ("x", "ru")
    assert Text.model_validate("plain").value == "plain"


def test_the_coercion_leaves_a_context_alone():
    """@context is a vocabulary, not a property, so it is not wrapped.

    Only declared list fields are, which also means an unmodelled property is
    stored exactly as the record wrote it and model_dump still round-trips it.
    """
    work = Work.model_validate({**LEGACY, "@context": {"@vocab": "http://y/"}})
    assert (work.model_extra or {})["@context"] == {"@vocab": "http://y/"}


def test_the_dialect_still_demands_the_array():
    """The asymmetry is deliberate, and it is the opposite of wrap_ref's.

    A bare literal and a bare URI are what the current context produces, so the
    schema was widened to accept them. A bare property is only ever a record
    written before the context: the models read it so a page still renders, and
    the schema refuses it so an ingest gate still catches it. Widening the
    schema here would make "every property is an array" hold for the dozen
    modelled properties and not for the other hundred and twenty.
    """
    assert validate(LEGACY, ontology=False) != []


@pytest.mark.parametrize(
    "value",
    [
        ["https://x/2"],
        [{"@id": "https://x/2"}],
        "https://x/2",
    ],
    ids=["bare uri", "wrapper", "scalar"],
)
def test_a_reference_reads_whichever_context_framed_it(value):
    """itemOf is a bare URI under this library's context and a wrapper under
    bluecore-models', which coerces a different three properties.

    Typed list[str] these raised on the wrapper, which is the shape production
    actually stores. Ref reads all three and str(ref) is the URI either way, so
    the narrower type refused half the corpus to say nothing extra.
    """
    item = Item.model_validate(
        {"@id": "https://x/1", "@type": ["Item"], "itemOf": value}
    )
    assert item.item_of[0].uri == "https://x/2"
    assert str(item.item_of[0]) == "https://x/2"


def test_a_term_carries_the_authority_it_came_from():
    """bf:source is what tells two identically spelled headings apart.

    Reachable before this only as ref.model_extra["source"], because Ref had no
    get() of its own -- and subject, genreForm, language, note and extent are
    all Refs, so the escape hatch was missing on exactly the values a consumer
    most needs to reach into.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "subject": [
                {
                    "@id": "http://id.loc.gov/authorities/subjects/sh1",
                    "source": [{"@id": "http://id.loc.gov/authorities/subjects"}],
                }
            ],
        }
    )
    assert work.subject[0].source[0].uri == "http://id.loc.gov/authorities/subjects"


def test_any_node_can_state_its_label_not_only_a_reference():
    """rdfs:label is on the base, because it is not a reference's private business.

    It is where a note writes its text, an extent writes its text and an
    organization writes its name.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "note": [{"@type": ["Note"], "rdfs:label": ["Chiefly in Korean"]}],
        }
    )
    assert str(work.note[0]) == "Chiefly in Korean"
    assert work.label == []


# --- the nodes a consumer loops over -----------------------------------------


def test_a_call_number_reaches_its_assigner():
    """The link a consumer loses today when the property holds a list.

    bluecore_api reads a classification's assigner with an isinstance(dict)
    check, so under the framed all-lists shape the href is None and the link
    silently disappears while the text still renders. A typed list makes that
    shape the only one there is.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "classification": [
                {
                    "@type": ["ClassificationLcc"],
                    "classificationPortion": ["TJ807.9.K6"],
                    "itemPortion": ["Y864 2023"],
                    "assigner": [
                        {"@id": "http://id.loc.gov/vocabulary/organizations/dlc"}
                    ],
                    "status": [{"@id": "http://id.loc.gov/vocabulary/mstatus/uba"}],
                }
            ],
        }
    )
    call_number = work.classification[0]
    assert call_number.kind == "ClassificationLcc"
    assert str(call_number.portion[0]) == "TJ807.9.K6"
    assert call_number.assigner[0].uri == (
        "http://id.loc.gov/vocabulary/organizations/dlc"
    )
    assert call_number.status[0].uri == "http://id.loc.gov/vocabulary/mstatus/uba"


def test_a_relation_names_its_kind_and_its_target():
    """A series relation describes its target in place rather than pointing at it.

    So associated_resource is a Resource and not a Ref: it carries a bf:Title of
    its own and no URI anywhere, which is why str() has to reach the nested
    title rather than the label keys the node itself holds.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "relation": [
                {
                    "@type": ["Relation"],
                    "relationship": [{"@id": "https://x/rel/hasSeries"}],
                    "seriesEnumeration": ["2023-04"],
                    "associatedResource": [
                        {
                            "@type": ["Series"],
                            "title": [{"@type": ["Title"], "mainTitle": ["A series"]}],
                        }
                    ],
                }
            ],
        }
    )
    relation = work.relation[0]
    assert relation.relationship[0].uri == "https://x/rel/hasSeries"
    assert str(relation.series_enumeration[0]) == "2023-04"
    assert str(relation.associated_resource[0]) == "A series"


def test_a_title_is_told_from_its_variants_by_its_type():
    """LC prints the two under separate headings, so joining them is wrong.

    An untyped node counts as the proper title: a record saying only "this is a
    title" means the title.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "title": [
                {"@type": ["Title"], "mainTitle": ["The proper one"]},
                {"@type": ["VariantTitle"], "mainTitle": ["A variant"]},
                {"@type": ["ParallelTitle"], "mainTitle": ["In translation"]},
                {"mainTitle": ["Untyped, so proper"]},
            ],
        }
    )
    assert [str(t) for t in work.title_proper] == [
        "The proper one",
        "Untyped, so proper",
    ]
    assert [str(t) for t in work.variant_titles] == ["A variant", "In translation"]
    assert str(work.main_title) == "The proper one"


def test_a_record_with_no_title_is_still_named():
    """An authority or an agent carries no title at all, only a label.

    So "what is this called" cannot rely on main_title, and every consumer would
    otherwise write this fallback chain itself.
    """
    filed_under = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "bflc:aap": ["King, Stephen, 1947-. Dark tower"],
            "title": [{"@type": ["Title"], "mainTitle": ["Dark tower"]}],
        }
    )
    assert str(filed_under.access_point) == "King, Stephen, 1947-. Dark tower"

    labelled = Work.model_validate(
        {"@id": "https://x/1", "@type": ["Work"], "rdfs:label": ["Only a label"]}
    )
    assert str(labelled.access_point) == "Only a label"

    titled = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "title": [{"@type": ["Title"], "mainTitle": ["Only a title"]}],
        }
    )
    assert str(titled.access_point) == "Only a title"

    assert Work.model_validate({"@type": ["Work"]}).access_point is None


def test_every_uri_a_record_cites_is_collected():
    """A consumer looks each one up to turn a code into a name.

    Blank node labels are left out: they address nothing outside the record.
    """
    work = Work.model_validate(
        {
            "@id": "https://x/1",
            "@type": ["Work"],
            "subject": [
                {"@id": "https://x/s", "source": [{"@id": "https://x/scheme"}]}
            ],
            "contribution": [{"@type": ["Contribution"], "agent": [{"@id": "_:b0"}]}],
            "originPlace": [{"@id": "https://x/p"}],
        }
    )
    assert work.uris() == {
        "https://x/1",
        "https://x/s",
        "https://x/scheme",
        "https://x/p",
    }


def test_a_label_keeps_its_language():
    """stated_label returns a Text, not a str, so the tag survives.

    Many records hold a romanised and a vernacular form of one value, and the
    tag is the only thing telling them apart.
    """
    ref = Ref.model_validate(
        {
            "@id": "https://x/s",
            "mads:authoritativeLabel": [{"@value": "Труды", "@language": "ru-cyrl"}],
        }
    )
    label = ref.stated_label
    assert label is not None
    assert label.language == "ru-cyrl"
    assert str(ref) == "Труды"
