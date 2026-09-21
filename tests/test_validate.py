"""load() parses, validate() judges, and the schemas ship with the package."""

import pytest
from pydantic import ValidationError

from bibframe_json import (
    DIALECT,
    ONTOLOGY,
    Hub,
    Instance,
    Item,
    Work,
    context,
    load,
    schema,
    validate,
)

CLEAN = {
    "@id": "https://bcld.info/works/1",
    "@type": ["Work"],
    "title": [{"@type": ["Title"], "mainTitle": ["A title"]}],
}


# --- the artifacts are reachable from an install -----------------------------


@pytest.mark.parametrize("name", [DIALECT, ONTOLOGY])
def test_schemas_load_through_the_package(name):
    """Read through importlib.resources, not a relative path.

    The schemas used to sit at the top level of the repo, where `packages`
    excluded them from the wheel: an installed copy had neither schema nor
    context, and the only way to validate was from a checkout with the right
    working directory.
    """
    assert schema(name)["$schema"].startswith("https://json-schema.org/")


def test_context_loads_through_the_package():
    assert context()["@context"]["@vocab"].startswith("http://id.loc.gov/")


def test_an_unknown_schema_is_an_error_rather_than_a_path():
    with pytest.raises(ValueError, match="no such schema"):
        schema("nonesuch")


# --- load(): parsing ---------------------------------------------------------


@pytest.mark.parametrize(
    ("types", "expected"),
    [
        (["Work"], Work),
        (["Instance"], Instance),
        (["Hub"], Hub),
        (["Item"], Item),
        (["Monograph", "Text", "Work"], Work),
        ("Instance", Instance),
        # A real Hub is typed both, in either order: marc2bibframe2 writes
        # bf:Work alongside bf:Hub and framing keeps both. The specific type has
        # to win, or every Hub loads as a Work and expression_of is unreachable.
        (["Work", "Hub"], Hub),
        (["Hub", "Work"], Hub),
    ],
)
def test_load_dispatches_on_type(types, expected):
    """Including a scalar @type, which a node with one type still carries."""
    assert isinstance(load({"@id": "https://x/1", "@type": types}), expected)


def test_a_hub_typed_as_a_work_still_reads_as_a_hub():
    """The field that was unreachable, on the record shape that hid it.

    Worth asserting beyond the dispatch table above, because the cost of the old
    ordering was not a wrong class name -- it was that Hub.expression_of, the
    Hub-Work link, silently read as empty on every Hub in the corpus.
    """
    hub = load(
        {
            "@id": "https://x/hubs/1",
            "@type": ["Work", "Hub"],
            "expressionOf": [{"@id": "https://x/works/1"}],
        }
    )
    assert isinstance(hub, Hub)
    assert [ref.uri for ref in hub.expression_of] == ["https://x/works/1"]


def test_load_says_so_when_it_cannot_tell_what_a_record_is():
    with pytest.raises(ValueError, match="no model for"):
        load({"@id": "https://x/1", "@type": ["Topic"]})


def test_parsing_is_not_validating():
    """The point of having two functions.

    This record parses happily and breaks two rules: a blank node keeping its
    @id, and mainTitle on a Work rather than on a Title. Parsing checks field
    types and accepts the rest, since of 136 properties in real records only
    about a dozen have fields.
    """
    record = {
        "@id": "https://x/1",
        "@type": ["Work"],
        "subject": [{"@id": "_:b0"}],
        "mainTitle": ["on a Work, which breaks its domain"],
    }
    assert isinstance(load(record), Work), "parses"
    assert validate(record), "and does not conform"


def test_something_unparseable_raises():
    with pytest.raises(ValidationError):
        load({"@id": "https://x/1", "@type": ["Work"], "title": [[1, 2]]})


# --- validate(): judging -----------------------------------------------------


def test_a_clean_record_has_no_findings():
    assert validate(CLEAN) == []


def test_layers_can_be_asked_for_separately():
    record = {**CLEAN, "subject": [{"@id": "_:b0"}], "mainTitle": ["x"]}
    assert {f.layer for f in validate(record)} == {DIALECT, ONTOLOGY}
    assert {f.layer for f in validate(record, ontology=False)} == {DIALECT}
    assert {f.layer for f in validate(record, dialect=False)} == {ONTOLOGY}
    assert validate(record, dialect=False, ontology=False) == []


def test_dialect_findings_are_errors_and_ontology_findings_are_not():
    """When the data and the ontology disagree the ontology is often the one
    that is behind, so its findings are warnings."""
    record = {**CLEAN, "subject": [{"@id": "_:b0"}], "mainTitle": ["x"]}
    by_layer = {f.layer: f for f in validate(record)}
    assert by_layer[DIALECT].is_error
    assert not by_layer[ONTOLOGY].is_error


@pytest.mark.parametrize(
    ("record", "path", "says"),
    [
        (
            {**CLEAN, "subject": [{"@id": "_:b0"}]},
            "subject/0",
            "blank node",
        ),
        (
            {
                **CLEAN,
                "title": [
                    {
                        "@type": ["Title"],
                        "mainTitle": [
                            {"@value": "x", "@type": "xsd:string", "@language": "en"}
                        ],
                    }
                ],
            },
            "title/0/mainTitle/0",
            "at most one of @type or @language",
        ),
        ({**CLEAN, "mainTitle": ["x"]}, "", "rdfs:domain"),
    ],
)
def test_findings_say_what_is_wrong_and_where(record, path, says):
    """Not which keyword noticed.

    Both schemas use anyOf, and jsonschema reports the anyOf itself -- whose
    message is the whole record printed back with "is not valid under any of the
    given schemas". The reason is buried in error.context, so it is dug out.
    """
    matching = [f for f in validate(record) if says in f.message]
    assert matching, [str(f) for f in validate(record)]
    assert matching[0].path == path


def test_the_type_noise_from_a_failing_anyof_is_dropped():
    """A node rejected for carrying an @id also fails the branch that wanted a
    bare URI string, which reports "is not of type string". Where a path has a
    real explanation that complaint is noise, and one fault should read as one
    finding."""
    findings = validate({**CLEAN, "subject": [{"@id": "_:b0"}]}, ontology=False)
    assert len(findings) == 1, [str(f) for f in findings]


def test_validate_reports_what_the_models_let_through():
    """The other half of test_the_models_parse_rather_than_judge.

    Those two rules are enforced in exactly one place each, and this is it. If
    the models ever start rejecting them, the pair of tests will disagree and
    say so.
    """
    record = {
        **CLEAN,
        "subject": [{"@id": "_:b0"}],
        "title": [
            {
                "@type": ["Title"],
                "mainTitle": [
                    {"@value": "x", "@type": "xsd:string", "@language": "en"}
                ],
            }
        ],
    }
    load(record)  # parses
    messages = [f.message for f in validate(record, ontology=False)]
    assert any("blank node" in m for m in messages), messages
    assert any("at most one of @type or @language" in m for m in messages), messages


def test_unmodelled_properties_must_still_be_arrays():
    """The guarantee the whole shape rests on, for the properties that have no
    field: about 120 of the 136 in real records.

    pydantic emits additionalProperties: true for extra="allow", so before this
    was constrained only the dozen modelled properties were checked.
    """
    findings = validate({**CLEAN, "bflc:aap": "not a list"}, ontology=False)
    assert [f.path for f in findings] == ["bflc:aap"]
    assert validate({**CLEAN, "bflc:aap": ["a list"]}, ontology=False) == []


@pytest.mark.parametrize(
    "value",
    [
        "https://bibframe-json.org/context/bibframe.jsonld",
        {"@vocab": "http://id.loc.gov/ontologies/bibframe/"},
        ["https://x/ctx.jsonld", {"@vocab": "http://x/"}],
    ],
)
def test_a_context_is_not_a_property(value):
    """A record may carry the context that produced its shape.

    require_arrays has to exempt JSON-LD keywords, or validate() refuses the
    very document the README recommends it as a gate for. @context is a
    vocabulary rather than data and takes all three of these forms, none of
    which is an array of values.

    The stored Blue Core shape carries no context -- the ORM event pops it after
    framing -- which is why this never reached the rendering path and went
    unnoticed.
    """
    assert validate({**CLEAN, "@context": value}, ontology=False) == []


def test_a_keyword_is_exempt_but_a_property_is_not():
    """The exemption is for keywords only, and it is narrow on purpose.

    @index is a keyword and passes; bflc:aap is a property and must still be an
    array. Pinning both together is what stops the exemption being widened into
    the array guarantee itself.
    """
    assert validate({**CLEAN, "@index": "vol. 2"}, ontology=False) == []
    assert validate({**CLEAN, "bflc:aap": "not a list"}, ontology=False) != []


@pytest.mark.parametrize(
    "field",
    ["subject", "title", "contribution", "identifiedBy", "adminMetadata"],
)
def test_no_node_keeps_a_blank_node_id(field):
    """README offers this as a guarantee of the shape, so it has to hold everywhere.

    The rule lived inside wrap_ref, which reaches Ref-typed fields and no
    others -- so subject and note were checked while title, contribution,
    identifiedBy, provisionActivity, classification and adminMetadata were not.
    The only test for it went through subject, which is why it looked covered.
    """
    findings = validate(
        {**CLEAN, field: [{"@id": "_:b0", "@type": ["Thing"]}]}, ontology=False
    )
    assert "a blank node must not carry an @id" in [f.message for f in findings]


def test_the_blank_node_rule_does_not_reject_every_node():
    """The `required` beside the `properties` is what makes this pass.

    Without it the `not` is vacuously true for an object carrying no @id, and
    the rule rejects every node rather than the blank ones.
    """
    assert (
        validate({**CLEAN, "subject": [{"@id": "https://x/s"}]}, ontology=False) == []
    )
    assert (
        validate(
            {**CLEAN, "title": [{"@type": ["Title"], "mainTitle": ["T"]}]},
            ontology=False,
        )
        == []
    )
