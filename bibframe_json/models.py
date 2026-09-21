"""Pydantic models for the shape context/bibframe.jsonld guarantees.

Hand-written, unlike the context and the ontology schema. The division is
deliberate: enumerating 249 `@container: @set` declarations is mechanical and
belongs in a generator, while deciding which properties a template needs and
what to call the helper that finds a display title is editorial. `iiif-prezi3`
is hand-written for the same reason.

These assume the context is adopted. Every property is a list, references are
URI strings, `@type` is a list. Where a record predates that, the validators
below still accept the older shape -- a record restored from a backup will carry
it long after any backfill.

Three things to know before reading further.

**These parse; they do not judge.** No rule about the shape is enforced here --
not the blank node rule, not the one about value objects carrying a single tag.
A record that breaks either still loads. Those rules live in
schema/dialect.json, and `validate()` reports them. Enforcing a few of them here
too would make load() unpredictable and put each rule in two places.

**Models are open, not closed.** `extra="allow"` throughout. BIBFRAME has 226
properties and the data uses 136; modelling the dozen that templates care about
and rejecting the rest would make these useless for anything else. An unmodelled
property is reachable through `model_extra`.

**A plain `@property` is invisible to `model_json_schema()`.** So display helpers
are plain properties and stay out of the published schema, while anything meant
to appear in API output would need `@computed_field`. That distinction is what
lets one set of models serve templates and the schema without display logic
leaking into the contract.
"""

from functools import cache
from typing import Annotated, Any, ClassVar, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

# Datatypes worth naming, since asking "is this date exact?" is the common case.
XSD_DATE = "http://www.w3.org/2001/XMLSchema#date"
XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"
EDTF = "http://id.loc.gov/datatypes/edtf"


def _collect_uris(value: Any, found: set[str]) -> None:
    """Walks anything and collects the URIs it names.

    Has to handle three shapes because a record holds all three: a parsed node,
    a raw dict for a value `get()` could not read, and lists of either.
    """
    if isinstance(value, Shape):
        if value.uri and not value.uri.startswith("_:"):
            found.add(value.uri)
        for held in value.properties().values():
            _collect_uris(held, found)
    elif isinstance(value, dict):
        for key, held in value.items():
            if key == "@id":
                if isinstance(held, str) and not held.startswith("_:"):
                    found.add(held)
            else:
                _collect_uris(held, found)
    elif isinstance(value, list):
        for item in value:
            _collect_uris(item, found)


@cache
def _values() -> TypeAdapter:
    """Reads a raw property value as literals and references.

    Built on first use rather than at import, because `Value` names `Text` and
    `Ref`, which are defined after the base that needs it.
    """
    return TypeAdapter(list[Value])


# Which of a model's fields are lists, by field name and by alias. Computed once
# per class: the coercion below runs for every node of every record read.
_LIST_FIELDS: dict[type, frozenset[str]] = {}


def _list_fields(model: type[BaseModel]) -> frozenset[str]:
    if model not in _LIST_FIELDS:
        names: set[str] = set()
        for name, field in model.model_fields.items():
            if get_origin(field.annotation) is list:
                names.add(name)
                if field.alias:
                    names.add(field.alias)
        _LIST_FIELDS[model] = frozenset(names)
    return _LIST_FIELDS[model]


class Shape(BaseModel):
    """One JSON-LD object, read openly and tolerantly.

    What `Ref` and `Node` share, and the one place the older shape is absorbed.
    Both had the same config, the same two keyword fields and the same
    hand-written `@type` coercion; this is that duplication resolved into the
    base they already implied.

    The context makes every property a list. A record written before it -- or
    restored from a backup taken before it -- holds a single value bare, and
    `models.py` promised those still load while only `Text`, `Ref` and `@type`
    delivered it. Wrapping here rather than in each field is what keeps the
    fields plain `list[X]`, which is what keeps the generated schema free of
    unions.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    uri: str | None = Field(default=None, alias="@id")
    types: list[str] = Field(default_factory=list, alias="@type")
    # On the base rather than on Ref alone, because it is where a note writes
    # its text, an extent writes its text and an organization writes its name --
    # not only where a reference happens to carry a label.
    label: list["Text"] = Field(default_factory=list, alias="rdfs:label")

    @model_validator(mode="before")
    @classmethod
    def a_single_value_is_still_a_list(cls, data: Any) -> Any:
        """Wrap a bare value in the list its field declares.

        Covers `@type` as a case of the general rule rather than as its own
        validator: `@type` is a keyword, so no `@container` can pin it, and a
        node with one type carries a string even under the current context.

        Only declared list fields are wrapped. An unmodelled property is left
        exactly as the record wrote it, so `model_dump()` still round-trips what
        was stored; `get()` normalises those on the way out instead.
        """
        if not isinstance(data, dict):
            return data
        wrapped = {
            key: [value]
            for key, value in data.items()
            if key in _list_fields(cls) and not isinstance(value, list)
        }
        return {**data, **wrapped} if wrapped else data

    def get(self, name: str) -> list[Any]:
        """An unmodelled property, as a list of parsed values.

        The escape hatch for the 120-odd properties with no field here. The
        context guarantees a list; this tolerates a scalar for records written
        before it, and reads each value as a literal or a reference so an
        unmodelled property behaves exactly like a modelled one -- `str(value)`
        for the text, `value.uri` for the link. Returning raw JSON instead meant
        a template printing an unmodelled value got `{'@value': 'x'}`.

        Parsed on the way out rather than at validation, so what was stored
        stays stored and `model_dump()` still round-trips the record untouched.
        A value that is neither a literal nor a reference -- a nested rdf:List,
        say -- comes back as it was rather than raising: these parse, they do
        not judge.
        """
        value = (self.model_extra or {}).get(name)
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        try:
            return _values().validate_python(values)
        except ValidationError:
            return values

    def properties(self) -> dict[str, list[Any]]:
        """Every property this node carries, modelled or not, keyed as the record
        spells it.

        What makes an open model usable from a template. A consumer renders any
        property it does not explicitly withhold, so it iterates a node rather
        than asking for fields by name -- and the modelled and unmodelled halves
        have to look alike when it does. `model_dump()` would hand back Python
        field names and plain dicts; `model_extra` holds only the unmodelled
        half, so a loop over it silently skips `title` and `contribution`.

        @id and @type are left out: they are keywords rather than properties,
        and a caller that wants them has `uri` and `types`.

        Modelled properties come first, in declaration order, then the rest in
        the order the record wrote them. Empty ones are omitted, so a caller can
        loop without checking.
        """
        found: dict[str, list[Any]] = {}
        for name, field in type(self).model_fields.items():
            if name in ("uri", "types"):
                continue
            values = getattr(self, name)
            if values:
                found[field.alias or name] = values
        for name in self.model_extra or {}:
            if name.startswith("@"):
                continue
            values = self.get(name)
            if values:
                found[name] = values
        return found

    # The places this shape writes a human label, in the order they win. A Title
    # writes one in mainTitle, an authority in mads:authoritativeLabel, an
    # identifier in rdf:value -- so which one is present is what decides.
    LABELLED_BY: ClassVar[tuple[str, ...]] = (
        "mainTitle",
        "rdfs:label",
        "mads:authoritativeLabel",
        "bflc:authoritativeLabel",
        "label",
        "rdf:value",
    )

    @property
    def stated_label(self) -> "Text | None":
        """The label this node states, or None when it states none.

        A Text rather than a str, so a language tag survives: many records hold
        a romanised and a vernacular form of one value, and flattening here
        would lose the only thing telling them apart.

        Stops at what the record says. Naming a node that names itself nowhere --
        printing the tail of its URI, or the code it happens to carry -- is a
        decision about what to show a reader, and it belongs to the consumer,
        along with looking a URI up in a database to find a label.
        """
        held = self.properties()
        for name in self.LABELLED_BY:
            for value in held.get(name, []):
                text = str(value).strip()
                if text:
                    return value if isinstance(value, Text) else Text(value=text)
        return None

    def uris(self) -> set[str]:
        """Every URI this record mentions, however deeply nested.

        A consumer collects these to look each one up for a label, since records
        cite a term by URI and drop the label. Blank node labels are left out:
        they address nothing outside the record they came from.
        """
        found: set[str] = set()
        _collect_uris(self, found)
        return found

    def __str__(self) -> str:
        """The label, else the URI, else nothing.

        So a template can print any value of any property without knowing
        whether it is described in place or only pointed at.
        """
        return str(self.stated_label or self.uri or "")


class Text(BaseModel):
    """A literal that still knows its language and datatype.

    Flattening a literal to a bare string loses meaning here, not just metadata,
    which is why this is a model rather than a `str` field:

    - `date` carries three datatypes in real records -- xsd:dateTime, xsd:date
      and EDTF. EDTF encodes uncertainty (`199X`, `1970?`, intervals), so
      reading it as an xsd:date is wrong.
    - a language tag is often the only thing telling parallel scripts apart. 101
      properties hold both a romanised and a vernacular form of one value, and
      `bluecore_api` currently renders them comma-joined as though they were two
      different titles.

    `__str__` returns the value, so a template writing `{{ title }}` gets the
    text and needs to know none of this.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    value: str = Field(alias="@value")
    language: str | None = Field(default=None, alias="@language")
    datatype: str | None = Field(default=None, alias="@type")

    @model_validator(mode="before")
    @classmethod
    def accept_a_bare_string(cls, data: Any) -> Any:
        """A plain string is a literal with no language and no datatype.

        Most literals in the data are plain strings -- 14,021 against 771 value
        objects -- so the common case has to be the cheap one.
        """
        if isinstance(data, str):
            return {"@value": data}
        return data

    # A value object carries at most one of @type or @language -- required by
    # JSON-LD, and confirmed in the data: 703 with a datatype, 68 with a
    # language, none with both. That rule is *not* enforced here, and the
    # omission is deliberate.
    #
    # These models parse; schema/dialect.json judges. A model_validator here
    # would make one rule of several behave differently from the rest, so a
    # caller could not predict what load() refuses -- and it would put the rule
    # in two places, since a validator never reaches model_json_schema() and it
    # has to be written into the schema regardless. Call validate() to be told
    # about it.

    @property
    def approximate(self) -> bool:
        """Whether this is an EDTF value, and so may be uncertain."""
        return self.datatype == EDTF

    def __str__(self) -> str:
        return self.value


class Ref(Shape):
    """Something the record points at rather than describes.

    Blue Core keeps a referenced resource's description in its own row, so what
    remains here is usually just a URI -- 5,245 of 8,875 node values in a
    200-record sample. `label` is present when the record happens to carry one.
    """

    # The authority a term belongs to. A subject cites the scheme it came from
    # here, and it is the only thing distinguishing two identically spelled
    # headings from different vocabularies.
    source: list["Ref"] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_a_bare_uri(cls, data: Any) -> Any:
        """`@type: @id` in the context writes a reference as a plain string."""
        if isinstance(data, str):
            return {"@id": data}
        return data


# A value is a literal, a reference, or a nested node. Declared as a union of
# Text and Ref because those cover what templates read; a nested node with its
# own properties still parses as a Ref, with the rest reachable via model_extra.
Value = Annotated[Text | Ref, Field(union_mode="left_to_right")]


class Node(Shape):
    """Anything with a @type and properties: a node you describe rather than
    only point at."""


def _local(types: list[str], name: str) -> bool:
    """Whether any of these types is the named class.

    Compared on the local name, since a type is a compacted term for BIBFRAME's
    own classes and a full URI for anything else -- a record framed under a
    different @vocab keeps `http://example.org/base/Title`.
    """
    return any(t.rsplit("/", 1)[-1] == name for t in types)


def _subtype(types: list[str], base: str) -> str | None:
    """The first type that is not the base class: Isbn, ClassificationLcc, Publication.

    What tells two otherwise identical nodes apart. Compared on the local name,
    since a type is a compacted term for BIBFRAME's own classes and a full URI
    for anything else.
    """
    for candidate in types:
        if candidate.rsplit("/", 1)[-1] != base:
            return candidate
    return None


class Title(Node):
    main: list[Text] = Field(default_factory=list, alias="mainTitle")
    subtitle: list[Text] = Field(default_factory=list)
    part_number: list[Text] = Field(default_factory=list, alias="partNumber")
    part_name: list[Text] = Field(default_factory=list, alias="partName")

    def __str__(self) -> str:
        parts = [str(self.main[0])] if self.main else []
        if self.subtitle:
            parts.append(str(self.subtitle[0]))
        return ": ".join(parts)


class Contribution(Node):
    agent: list[Ref] = Field(default_factory=list)
    role: list[Ref] = Field(default_factory=list)

    @property
    def primary(self) -> bool:
        """Whether this is the primary contribution, by its extra type."""
        return any(t.endswith("PrimaryContribution") for t in self.types)


class Identifier(Node):
    value: list[Text] = Field(default_factory=list, alias="rdf:value")
    qualifier: list[Text] = Field(default_factory=list)
    status: list[Ref] = Field(default_factory=list)

    @property
    def kind(self) -> str | None:
        """Isbn, Lccn, Local -- the first type that is not Identifier itself.

        None rather than "Identifier" when a record says only that much: a
        caller printing the kind wants to omit it, not to print the base class.
        """
        return _subtype(self.types, "Identifier")


class ProvisionActivity(Node):
    place: list[Ref] = Field(default_factory=list)
    date: list[Text] = Field(default_factory=list)
    simple_date: list[Text] = Field(default_factory=list, alias="bflc:simpleDate")
    simple_place: list[Text] = Field(default_factory=list, alias="bflc:simplePlace")
    simple_agent: list[Text] = Field(default_factory=list, alias="bflc:simpleAgent")
    simple_statement: list[Text] = Field(
        default_factory=list, alias="bflc:simpleStatement"
    )

    @property
    def kind(self) -> str | None:
        """Publication, Distribution, Manufacture -- what the activity was."""
        return _subtype(self.types, "ProvisionActivity")


class Classification(Node):
    """A call number, and who assigned it.

    LC prints one as "LCC: ML31 .C595 (Assigner: dlc)": the kind, the number in
    two portions, then whoever assigned it and how far it is trusted.

    Note that bf:Classification itself is usually absent from @type -- a call
    number is typed ClassificationLcc or ClassificationDdc and nothing else --
    which is why `kind` looks for the first type that is not the base rather
    than for a second one.
    """

    portion: list[Text] = Field(default_factory=list, alias="classificationPortion")
    item_portion: list[Text] = Field(default_factory=list, alias="itemPortion")
    assigner: list[Ref] = Field(default_factory=list)
    status: list[Ref] = Field(default_factory=list)

    @property
    def kind(self) -> str | None:
        """ClassificationLcc, ClassificationDdc -- how the number is built."""
        return _subtype(self.types, "Classification")


class AdminMetadata(Node):
    """How the record itself came to be, rather than what it describes.

    Modelled for three things a consumer reads rather than for the block as a
    whole, which is rendered property by property: `status`, which is where a
    stub record declares itself incomplete; `derived_from`, which links back to
    the record this one was converted from; and the two reference-valued
    properties that turn up here rather than on the resource.
    """

    agent: list[Ref] = Field(default_factory=list)
    date: list[Text] = Field(default_factory=list)
    status: list[Ref] = Field(default_factory=list)
    derived_from: list[Ref] = Field(default_factory=list, alias="derivedFrom")
    description_conventions: list[Ref] = Field(
        default_factory=list, alias="descriptionConventions"
    )
    generation_process: list[Ref] = Field(
        default_factory=list, alias="generationProcess"
    )
    description_level: list[Ref] = Field(default_factory=list, alias="descriptionLevel")


class Relation(Node):
    """How one resource points at another, and what the pointing means.

    `relationship` names the kind, and a relation routinely names two at once --
    "part of" and "holding of" -- which is why it is a list and why LC files the
    relation under both headings rather than choosing.

    `associated_resource` is the other end, and it is a Resource rather than a
    Ref because a series relation frequently describes it in place: a bf:Title
    of its own, in two scripts, with no URI anywhere. Typed Resource and not
    Work deliberately -- either end can be any resource type, and a
    self-referential Work would make the generated schema a $ref to itself.
    """

    relationship: list[Ref] = Field(default_factory=list)
    associated_resource: list["Resource"] = Field(
        default_factory=list, alias="associatedResource"
    )
    series_enumeration: list[Text] = Field(
        default_factory=list, alias="seriesEnumeration"
    )


class Resource(Node):
    """What a Work, Instance, Hub and Item have in common.

    Sharing a base is what lets one set of template partials serve all four --
    `{% include "partials/titles.html" %}` regardless of resource type.
    """

    title: list[Title] = Field(default_factory=list)
    note: list[Ref] = Field(default_factory=list)
    subject: list[Ref] = Field(default_factory=list)
    identified_by: list[Identifier] = Field(default_factory=list, alias="identifiedBy")
    admin_metadata: list[AdminMetadata] = Field(
        default_factory=list, alias="adminMetadata"
    )
    contribution: list[Contribution] = Field(default_factory=list)

    # Down from Work, because a Hub is typed bf:Work in the data but is not a
    # Work in these models, and a consumer renders all three for any resource
    # type. Sharing them here is the reason Resource exists: one set of template
    # partials serves all four.
    classification: list[Classification] = Field(default_factory=list)
    language: list[Ref] = Field(default_factory=list)
    genre_form: list[Ref] = Field(default_factory=list, alias="genreForm")

    relation: list[Relation] = Field(default_factory=list)
    series_statement: list[Text] = Field(default_factory=list, alias="seriesStatement")
    electronic_locator: list[Ref] = Field(
        default_factory=list, alias="electronicLocator"
    )
    # The name LC files a record under: "King, Stephen, 1947-. Dark tower". Used
    # to name the record in every link to it, not only as a field of its own.
    aap: list[Text] = Field(default_factory=list, alias="bflc:aap")
    # The Hub-Work link, readable from either end: a consumer reads expressionOf
    # off a Work and hasExpression off a Hub, so this cannot live on Hub alone.
    expression_of: list[Ref] = Field(default_factory=list, alias="expressionOf")

    @property
    def title_proper(self) -> list[Title]:
        """The titles that name the resource, rather than a variant of it.

        A variant is a subtype of bf:Title -- VariantTitle, KeyTitle,
        ParallelTitle -- and an untyped node counts as the proper one, since a
        record that says only "this is a title" means the title. LC prints the
        two under separate headings, and joining them would run a title together
        with its own variants.
        """
        return [t for t in self.title if not t.types or _local(t.types, "Title")]

    @property
    def variant_titles(self) -> list[Title]:
        """The titles that name a variant: the complement of title_proper."""
        return [t for t in self.title if t.types and not _local(t.types, "Title")]

    @property
    def main_title(self) -> Text | None:
        """The display title: the first title proper's mainTitle.

        `work.title[0].main[0]` with a check at each step is what a template
        would otherwise have to write, and every consumer would write it again.
        Prefers a Title over a VariantTitle or KeyTitle.
        """
        for title in self.title_proper:
            if title.main:
                return title.main[0]
        for title in self.title:
            if title.main:
                return title.main[0]
        return None

    @property
    def access_point(self) -> Text | None:
        """The name this record is filed under: "King, Stephen, 1947-. Dark tower".

        What names the record in a heading and in every link to it. bflc:aap
        where the source writes one, rdfs:label where it writes that instead,
        and the title as the fallback -- an authority or an agent carries no
        title at all, so a caller asking for "what is this called" cannot rely
        on main_title alone.
        """
        for held in (self.aap, self.label):
            for value in held:
                if str(value).strip():
                    return value
        return self.main_title

    def titles_in(self, language: str | None) -> list[Text]:
        """Titles in one language, or untagged ones when language is None.

        The operation `scalar()` in bluecore_api currently answers by joining
        every form with a comma, so a record with romanised and Cyrillic titles
        renders as both at once.
        """
        return [
            main
            for title in self.title
            for main in title.main
            if main.language == language
        ]

    @property
    def primary_contributions(self) -> list[Contribution]:
        return [c for c in self.contribution if c.primary]

    def __str__(self) -> str:
        """The access point, since a resource writes its name in a nested Title.

        Shape.__str__ reads the label keys a node carries directly, which is
        right for something you only point at. A resource names itself one level
        down, in title/mainTitle -- and a resource described in place rather than
        referenced, which is how a transcribed series arrives, has no URI to fall
        back on either. Without this it printed as the empty string.
        """
        return str(self.access_point or self.uri or "")


# A reference is a Ref even where a context writes it as a bare URI. This
# library's context coerces six properties with `@type: @id`, but it is not the
# only context that frames this data: bluecore-models coerces hasInstance,
# hasWork and instanceOf and nothing else, so a stored record holds
# {"@id": ...} for itemOf and hasItem where ours holds a string. Ref reads both
# -- accept_a_bare_uri is what makes that true -- and str(ref) is the URI when
# there is no label, so typing these as list[str] bought nothing and refused
# half the corpus.


class Work(Resource):
    has_instance: list[Ref] = Field(default_factory=list, alias="hasInstance")
    # No instance_of here: bf:instanceOf has rdfs:domain bf:Instance, so
    # schema/ontology.json reports it as a domain violation on a Work. A Work
    # points the other way, with hasInstance.


class Instance(Resource):
    instance_of: list[Ref] = Field(default_factory=list, alias="instanceOf")
    provision_activity: list[ProvisionActivity] = Field(
        default_factory=list, alias="provisionActivity"
    )
    extent: list[Ref] = Field(default_factory=list)
    publication_statement: list[Text] = Field(
        default_factory=list, alias="publicationStatement"
    )


class Hub(Resource):
    # The inverse of Resource.expression_of, and Hub-only: only a Hub gathers
    # the Works that express it.
    has_expression: list[Ref] = Field(default_factory=list, alias="hasExpression")


class Item(Resource):
    item_of: list[Ref] = Field(default_factory=list, alias="itemOf")


# Shape.label is declared as list["Text"] and Ref.source as list["Ref"], since
# both name a class defined after the one that holds the field.
Shape.model_rebuild()
Ref.model_rebuild()
Relation.model_rebuild()
