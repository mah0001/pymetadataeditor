from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SchemaBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True, protected_namespaces=(), use_enum_values=True
    )  # if a subclass has a model_config then this will be overridden

    def __setitem__(self, key, value):
        """Allow dict like setting: Model[key] = value"""
        setattr(self, key, value)


class OriginDescription(SchemaBaseModel):
    harvest_date: Optional[str] = Field(None, description="Harvest date using UTC date format")
    altered: Optional[bool] = Field(
        None,
        description="If the metadata was altered before dissemination",
        title="Metadata altered",
    )
    base_url: Optional[str] = Field(None, description="Base URL of the originating repository")
    identifier: Optional[str] = Field(
        None,
        description="Unique idenifiter of the item from the originating repository",
    )
    date_stamp: Optional[str] = Field(
        None,
        description=(
            "Datestamp (UTC date format) of the metadata record disseminated by the" " originating repository"
        ),
    )
    metadata_namespace: Optional[str] = Field(
        None,
        description=(
            "Metadata namespace URI of the metadata format of the record harvested from" " the originating repository"
        ),
    )


class Keyword(SchemaBaseModel):
    name: str = Field(..., title="Keyword")
    vocabulary: Optional[str] = Field(None, title="Vocabulary")
    uri: Optional[str] = Field(None, title="URI")


class BboxItem(SchemaBaseModel):
    west: Optional[str] = Field(None, title="West")
    east: Optional[str] = Field(None, title="East")
    south: Optional[str] = Field(None, title="South")
    north: Optional[str] = Field(None, title="North")


class VersionStatement(SchemaBaseModel):
    """
    Version Statement
    """

    version: Optional[str] = Field(None, title="Version")
    version_date: Optional[str] = Field(None, title="Version Date")
    version_resp: Optional[str] = Field(
        None,
        description=("The organization or person responsible for the version of the work"),
        title="Version Responsibility Statement",
    )
    version_notes: Optional[str] = Field(None, title="Version Notes")


class Producer(SchemaBaseModel):
    name: Optional[str] = Field(None, description="Name (required)", title="Name")
    abbr: Optional[str] = Field(None, title="Abbreviation")
    affiliation: Optional[str] = Field(None, title="Affiliation")
    role: Optional[str] = Field(None, title="Role")


class ProvenanceSchema(SchemaBaseModel):
    """
    Provenance of metadata based on the OAI provenance schema (http://www.openarchives.org/OAI/2.0/provenance.xsd)
    """

    origin_description: Optional[OriginDescription] = Field(None, title="Origin description")


class Tag(SchemaBaseModel):
    tag: Optional[str] = Field(None, title="Tag")
    tag_group: Optional[str] = Field(None, title="Tag group")
