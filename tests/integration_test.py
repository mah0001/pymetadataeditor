import os

import nbformat
import pandas as pd
import pytest
from metadataschemas.utils.quick_start import make_skeleton
from metadataschemas.utils.test_utils import assert_pydantic_models_equal, fill_in_pydantic_outline
from nbconvert.preprocessors import ExecutePreprocessor
from pydantic import ValidationError

from pymetadataeditor import MetadataEditor
from pymetadataeditor.interface import TemplateError


@pytest.fixture
def metadata_editor():
    # instantiate
    your_api_key = os.getenv("API_KEY")
    api_url = os.getenv("API_URL")
    me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)
    return me


def test_projects_integration(tmpdir, metadata_editor):
    """Do not use pytest.mark.parametrize since parallel runs cause the counts of projects to be off."""
    projects = metadata_editor.list_projects(limit="all")
    num_original_projects = len(projects)
    assert min(10, num_original_projects) == len(metadata_editor.list_projects(limit=10))
    assert num_original_projects - 1 == len(metadata_editor.list_projects(limit="all", offset=1))
    assert num_original_projects >= len(metadata_editor.list_projects(limit="all", metadata_type="indicator"))
    assert num_original_projects == len(metadata_editor.list_projects(limit="all", sort_by="updated_asc"))

    # Good: "document", "microdata", "table", "indicator", "indicators_db", "video"
    # fail due to not searchable: "geospatial", "image", "script"

    metadata_types = [
        "document",
        "microdata",
        "table",
        "indicator",
        "indicators_db",
        "video",
        # "geospatial",  # evidently the default template is invalid
        "script",
        "image",
    ]
    creation_data = {
        "document": {
            "document_description": {
                "title_statement": {"idno": "integration_test_document", "title": "integration test document"}
            }
        },
        "geospatial": {
            "description": {
                "idno": "integration_test_geospatial",
                "contact": [{"organisation_name": "test"}],
                "date_stamp": "2023-10-01",
            },
            "metadata_information": {
                "idno": "integration_test_geospatial",
                "title": "integration test geospatial",
            },
        },
        "script": {
            "doc_desc": {
                "idno": "integration_test_script",
                "title": "Integration Test Script",
                "producers": [{"name": "Test Producer"}],
                "prod_date": "2024-01-24",
            }
        },
        "microdata": {
            "study_desc": {
                "title_statement": {
                    "idno": "integration_test_microdata_idno",
                    "title": "integration_test_microdata title",
                    "identifiers": [{"type": "doi", "identifier": "10.1234/5678"}],
                },
                "study_info": {
                    "nation": [{"name": "example_nation"}],
                    "bbox": [{"west": "-10", "south": "-10", "east": "10", "north": "10"}],
                    "bound_poly": [{"lat": "10", "lon": "-10"}],
                },
            },
            # "additional": {"file_description": {"data_file": {"file_id": "nothing", "file_name": "nothing"}}},
        },
        "table": {
            "table_description": {
                "title_statement": {"idno": "integration_test_table", "title": "integration test table"}
            }
        },
        "image": {
            "metadata_information": {
                "idno": "integration_test_image",
                "title": "integration test image",
                "production_date": "2024-01-01",
                "version": "1.0",
            }
        },
        "indicator": {
            "series_description": {"idno": "integration_test_indicator", "name": "integration test indicator"},
        },
        "indicators_db": {
            "database_description": {
                "title_statement": {
                    "idno": "integration_test_indicators_db",
                    "title": "integration_test_indicators_db title",
                }
            }
        },
        "video": {"video_description": {"idno": "integration_test_video", "title": "integration_test_video title"}},
    }
    update_data = {
        "document": {
            "document_description": {
                "title_statement": {"idno": "integration_test_document", "title": "integration test document updated"}
            }
        },
        "geospatial": {
            "metadata_information": {
                "idno": "integration_test_geospatial",
                "title": "integration test geospatial updated",
            }
        },
        "script": {
            "doc_desc": {
                "idno": "integration_test_script",
                "title": "integration test script updated",
                "producers": [{"name": "Test Producer"}],
                "prod_date": "2024-01-24",
            }
        },
        "microdata": {
            "study_desc": {
                "title_statement": {
                    "idno": "integration_test_microdata_idno",
                    "title": "integration_test_microdata title updated",
                    "identifiers": [{"type": "doi", "identifier": "10.1234/5678"}],
                },
                "study_info": {
                    "nation": [{"name": "example_nation"}],
                    "bbox": [{"west": "-10", "south": "-10", "east": "10", "north": "10"}],
                    "bound_poly": [{"lat": "10", "lon": "-10"}],
                },
            },
            # "additional": {"file_description": {"data_file": {"file_id": "nothing", "file_name": "nothing"}}},
        },
        "table": {
            "table_description": {
                "title_statement": {"idno": "integration_test_table", "title": "integration test table updated"}
            }
        },
        "image": {
            "metadata_information": {
                "idno": "integration_test_image",
                "title": "integration test image updated",
                "production_date": "2024-01-01",
                "version": "1.0",
            }
        },
        "indicator": {
            "series_description": {"idno": "integration_test_indicator", "name": "integration test indicator updated"}
        },
        "indicators_db": {
            "database_description": {
                "title_statement": {
                    "idno": "integration_test_indicators_db",
                    "title": "integration_test_indicators_db title updated",
                }
            }
        },
        "video": {
            "video_description": {"idno": "integration_test_video", "title": "integration_test_video title updated"}
        },
    }
    patch_update_data = {
        "document": [
            {
                "op": "add",
                "path": "/document_description/title_statement/title",
                "value": "patched integration test document updated",
            }
        ],
        "geospatial": [
            {
                "op": "replace",
                "path": "metadata_information/title",
                "value": "patched integration test geospatial",
            }
        ],
        "microdata": [
            {
                "op": "replace",
                "path": "study_desc/title_statement/title",
                "value": "integration_test_microdata title updated patched",
            }
        ],
        "table": [
            {
                "op": "replace",
                "path": "/table_description/title_statement/title",
                "value": "patched integration test table updated",
            },
        ],
        "image": [{"op": "replace", "path": "metadata_information/title", "value": "patched integration test image"}],
        "indicator": [
            {"op": "replace", "path": "series_description/name", "value": "patched integration_test_indicator_updated"}
        ],
        "indicators_db": [
            {
                "op": "add",
                "path": "database_description/title_statement/title",
                "value": "integration_test_indicators_db title updated patched",
            }
        ],
        "video": [
            {
                "op": "replace",
                "path": "/video_description",
                "value": {"idno": "integration_test_video", "title": "integration_test_video title updated patched"},
            }
        ],
        "script": [
            {
                "op": "replace",
                "path": "doc_desc/title",
                "value": "patched integration test script updated",
            }
        ],
    }

    for metadata_type in metadata_types:
        print(f"looking at {metadata_type} with creation data {creation_data[metadata_type]}")
        # create project
        project_id = metadata_editor.create_project_log(
            metadata=creation_data[metadata_type], metadata_type_or_template_uid=metadata_type
        )
        metadata_editor.delete_project_by_id(project_id)
        pydantic_model = metadata_editor.get_metadata_class(metadata_type)(**creation_data[metadata_type])
        project_id = metadata_editor.create_project_log(metadata=pydantic_model)
        metadata_editor.delete_project_by_id(project_id)
        filename = os.path.join(tmpdir, f"{metadata_type}.xlsx")
        metadata_editor.save_metadata_to_excel(pydantic_model, filename=filename)
        project_id = metadata_editor.create_project_log(filename, metadata_type_or_template_uid=metadata_type)

        try:
            assert len(metadata_editor.list_projects(limit="all")) == num_original_projects + 1

            # # get project
            # project_metadata = metadata_editor.get_project_by_id(project_id).metadata
            # for k, v in creation_data[metadata_type].items():
            #     assert k in project_metadata, project_metadata
            #     assert project_metadata[k] == v, project_metadata

            project_metadata = metadata_editor.get_project_metadata_by_id(project_id, output_mode="dict")
            for k, v in creation_data[metadata_type].items():
                assert k in project_metadata, project_metadata
                assert project_metadata[k] == v, project_metadata

            # update project
            print(f"updating project {project_id} with {update_data[metadata_type]}")
            metadata_editor.update_project_log_by_id(project_id, new_metadata=update_data[metadata_type])
            project_metadata_updated = metadata_editor.get_project_metadata_by_id(project_id, output_mode="dict")
            for k, v in update_data[metadata_type].items():
                assert project_metadata_updated[k] == v, project_metadata_updated

            # # check project is searchable and updated
            # title_contains_updated = metadata_editor.list_projects(
            #     limit="all", keywords="updated", metadata_type=metadata_type
            # )
            # assert (
            #     project_id in title_contains_updated.index or str(project_id) in title_contains_updated.index
            # ), title_contains_updated
            # title_contains_bogus = metadata_editor.list_projects(
            #     limit="all", keywords="bogus", metadata_type=metadata_type
            # )
            # assert (
            #     project_id not in title_contains_bogus.index and str(project_id) not in title_contains_bogus.index
            # ), title_contains_bogus

            # patch update
            title_contains_updated = metadata_editor.list_projects(
                limit="all", keywords="patched", metadata_type=metadata_type
            )
            assert project_id not in title_contains_updated.index or str(project_id) in title_contains_updated.index, (
                title_contains_updated
            )
            print(f"patching project {project_id} with {patch_update_data[metadata_type]}")
            for p in patch_update_data[metadata_type]:
                print(f"patching with {p}")
                metadata_editor.patch_update_project_log_by_id(project_id, **p)

            # title_contains_updated = metadata_editor.list_projects(
            #     limit="all", keywords="patched", metadata_type=metadata_type
            # )
            # assert (
            #     project_id in title_contains_updated.index or str(project_id) in title_contains_updated.index
            # ), title_contains_updated

            filename = f"{metadata_type}_{project_id}.xlsx"
            filename = os.path.join(tmpdir, filename)
            metadata_editor.get_project_metadata_by_id(project_id, output_mode="excel", filename=filename)
            metadata_editor.update_project_log_by_id(project_id, filename)
        finally:
            metadata_editor.delete_project_by_id(project_id)


@pytest.mark.parametrize(
    "metadata_type",
    ["document", "geospatial", "image", "indicator", "indicators_db", "microdata", "script", "table", "video"],
)
def test_get_class(metadata_editor, metadata_type):
    metadata_editor.get_metadata_class(metadata_type)
    metadata_class_no_rules, metadata_type, _ = metadata_editor._get_metadata_class_and_type_and_UID(
        metadata_type, apply_template_rules=False
    )

    temps = metadata_editor.list_templates()
    temps = temps[temps["data_type"] == metadata_type]
    for i, temp in temps.iterrows():
        klass = metadata_editor.get_metadata_class(temp["uid"])
        assert klass._metadata_type__ == metadata_type or klass._metadata_type__.default == metadata_type
        assert klass._metadata_type_version__ is not None and (
            isinstance(klass._metadata_type_version__, str) or klass._metadata_type_version__.default is not None
        )
        assert klass._template_uid__ == temp["uid"] or klass._template_uid__.default == temp["uid"]
        assert klass._template_name__ is not None and (
            isinstance(klass._template_name__, str) or klass._template_name__.default is not None
        )

        metadata_class_no_rules, metadata_type, _ = metadata_editor._get_metadata_class_and_type_and_UID(
            temp["uid"], apply_template_rules=False
        )


def test_project_download_and_read(metadata_editor, tmpdir):
    projects = metadata_editor.list_projects(limit="all")
    i = 0
    template_errors = set()
    default_validation_errors = {}
    dict_validation_errors = {}
    pydantic_validation_errors = {}
    excel_validation_errors = {}
    for project_id, project_info in projects.iterrows():
        if i >= 50:
            break
        i += 1
        # if project_info.type == "geospatial":
        #     continue
        # print(f"test_project_download_and_read: project_id = {project_id}")
        # print(project_info)
        metadata_editor.get_project_metadata_by_id(project_id, output_mode="dict", template_uid="none")
        if project_info.template_uid is not None:
            try:
                metadata_editor.get_metadata_class(project_info.template_uid)
            except TemplateError as e:
                template_errors.add(e)
                continue
        else:
            metadata_editor.get_metadata_class(project_info.type)

        try:
            metadata_editor.get_project_metadata_by_id(project_id, output_mode="dict", template_uid="default")
        except (ValidationError, TemplateError) as e:
            default_validation_errors[project_id] = e

        try:
            metadata_editor.get_project_metadata_by_id(project_id, output_mode="dict")
        except (ValidationError, TemplateError) as e:
            dict_validation_errors[project_id] = e
            continue
        try:
            pydantic_obj = metadata_editor.get_project_metadata_by_id(project_id, output_mode="pydantic")
        except (ValidationError, TemplateError) as e:
            pydantic_validation_errors[project_id] = e
            continue

        filename = os.path.join(tmpdir, f"test_project_download_and_read_{project_id}.xlsx")
        # filename = f"test_project_download_and_read_{project_id}.xlsx"
        try:
            filename = metadata_editor.get_project_metadata_by_id(
                project_id, output_mode="excel", filename=filename, debug=False
            )
        except (ValidationError, TemplateError) as e:
            excel_validation_errors[project_id] = e
            continue

        excel_obj = metadata_editor.read_metadata_from_excel(filename)
        assert_pydantic_models_equal(pydantic_obj, excel_obj)

    output = ""

    def format_errors(template_errors, name: str):
        output = ""
        template_errors_count = {}
        if isinstance(template_errors, dict):
            template_errors = [f"Project Id {k}: {v}" for k, v in template_errors.items()]
        for e in template_errors:
            if str(e) not in template_errors_count:
                template_errors_count[str(e)] = 0
            template_errors_count[str(e)] += 1
        template_errors = "\n\n\t".join(
            [f"{v} occurrence{'s' if v > 1 else ''} of {k}" for k, v in template_errors_count.items()]
        )
        output += f"\n\n\n\n{name}:\n\t{template_errors}\n"
        return output

    if len(template_errors) > 0:
        # count unique occurences of each template error
        output += format_errors(template_errors, "template errors")
    if len(dict_validation_errors) > 0:
        # formatted_errors = "\n\n\t".join([f"{k}: {v}" for k, v in dict_validation_errors.items()])
        # output += f"\n\n\n\ndict validation errors:\n\t{formatted_errors}\n"
        output += format_errors(dict_validation_errors, "dict validation errors")
    if len(pydantic_validation_errors) > 0:
        # formatted_errors = "\n\n\t".join([f"{k}: {v}" for k, v in pydantic_validation_errors.items()])
        # output += f"\n\n\n\npydantic validation errors:\n\t{formatted_errors}\n"
        output += format_errors(pydantic_validation_errors, "pydantic validation errors")
    if len(excel_validation_errors) > 0:
        # formatted_errors = "\n\n\t".join([f"{k}: {v}" for k, v in excel_validation_errors.items()])
        # output += f"\n\n\n\nexcel validation errors:\n\t{formatted_errors}\n"
        output += format_errors(excel_validation_errors, "excel validation errors")
    if len(default_validation_errors) > 0:
        # formatted_errors = "\n\n\t".join([f"{k}: {v}" for k, v in default_validation_errors.items()])
        # output += f"\n\n\n\ndefault validation errors:\n\t{formatted_errors}\n"
        output += format_errors(default_validation_errors, "default validation errors")
    if len(output) > 0:
        print(output)
    assert output == "", output


def test_collections_integration(metadata_editor):
    # list collections
    original_collections = metadata_editor.list_collections()
    num_original_collections = len(original_collections)

    # create collection
    collection_title = "integration_test_collection"
    collection_description = "integration_test_collection"
    collection_id = metadata_editor.create_collection(title=collection_title, description=collection_description)
    assert len(metadata_editor.list_collections()) == num_original_collections + 1

    try:
        # get collection
        new_collection = metadata_editor.get_collection_by_id(collection_id)
        new_collection.title = collection_title
        new_collection.description = collection_description

        # update_collection
        collection_title_updated = "integration_test_collection_updated"
        metadata_editor.update_collection(id=collection_id, title=collection_title_updated)
        updated_collection = metadata_editor.get_collection_by_id(collection_id)
        updated_collection.title = collection_title_updated
        updated_collection.description = collection_description

        collection_description_updated = "integration_test_collection_updated"
        metadata_editor.update_collection(id=collection_id, description=collection_description_updated)
        updated_collection = metadata_editor.get_collection_by_id(collection_id)
        updated_collection.title = collection_title_updated
        updated_collection.description = collection_description_updated

        # count projects in collection (should be zero)
        initial_projects_collection = metadata_editor.list_projects_in_collection(collection_id, limit="all")
        assert len(initial_projects_collection) == 0, f"expected zero projects but got {initial_projects_collection}"

        # create a project and add it to the collection by id
        project_idno = "project for collection integration test"
        project_name = "project for collection integration test"
        project_id = metadata_editor.create_project_log(
            metadata_type_or_template_uid="indicator",
            metadata={"series_description": {"idno": project_idno, "name": project_name}},
        )
        try:
            metadata_editor.add_projects_to_collection(collection_id, "id", project_id)

            # check the project can be found
            oneproject_collection = metadata_editor.list_projects_in_collection(collection_id, limit="all")
            assert len(oneproject_collection) == 1
            assert oneproject_collection.iloc[0].study_idno == project_idno, oneproject_collection.iloc[0].keys()
            good_search = metadata_editor.list_projects_in_collection(
                collection_id, keywords="integration", limit="all"
            )
            assert len(good_search) == 1
            good_search = metadata_editor.list_projects_in_collection(
                collection_id, keywords=["project", "integration"], limit="all"
            )
            assert len(good_search) == 1
            good_search = metadata_editor.list_projects_in_collection(
                collection_id, keywords="project integration", limit="all"
            )
            assert len(good_search) == 1
            assert good_search.iloc[0].study_idno == project_idno
            bad_search = metadata_editor.list_projects_in_collection(collection_id, keywords="bogus", limit="all")
            assert len(bad_search) == 0
            good_search = metadata_editor.list_projects_in_collection(collection_id, limit="all")
            assert len(good_search) == 1
            good_search = metadata_editor.list_projects_in_collection(collection_id, limit=10)
            assert len(good_search) == 1
            good_search = metadata_editor.list_projects_in_collection(collection_id, offset=1, limit="all")
            assert len(good_search) == 0
            good_search = metadata_editor.list_projects_in_collection(collection_id, sort_by="updated_asc", limit="all")
            assert len(good_search) == 1

            # remove that project by idno
            metadata_editor.remove_projects_from_collection(collection_id, "id", project_id)
            final_collection = metadata_editor.list_projects_in_collection(collection_id, limit="all")
            assert len(final_collection) == 0
        except Exception as e:
            metadata_editor.delete_project_by_id(project_id)
            raise e
        metadata_editor.delete_project_by_id(project_id)
    except Exception as e:
        metadata_editor.delete_collection_by_id(collection_id)
        raise e

    # delete collection
    metadata_editor.delete_collection_by_id(collection_id)
    assert len(metadata_editor.list_collections()) == num_original_collections


def test_resources_integration(metadata_editor, tmpdir):
    project_id = metadata_editor.create_project_log(
        {
            "idno": "resources_integration_test",
            "series_description": {"idno": "resources_integration_test", "name": "integration_test_of_resources"},
        },
        "indicator",
    )
    try:
        initial_resources = metadata_editor.get_resources_by_id(project_id)
        assert isinstance(initial_resources, pd.DataFrame)
        assert len(initial_resources) == 0

        filename = "resources_integration.txt"
        temp_file = tmpdir.join(filename)
        temp_file.write("dummy content")
        filename = str(temp_file)

        resource_id = metadata_editor.log_resource(
            project_id, dctype="txt", title="resources_integration", filename=filename
        )
        try:
            resources = metadata_editor.get_resources_by_id(project_id)
            assert isinstance(resources, pd.DataFrame)
            assert len(resources) == 1
            resources.iloc[0].title = "resources_integration"

            metadata_editor.update_resource(
                project_id=project_id, resource_id=resource_id, dctype="txt", title="updated_resources_integration"
            )
            resources = metadata_editor.get_resources_by_id(project_id)
            assert isinstance(resources, pd.DataFrame)
            assert len(resources) == 1
            resources.iloc[0].title = "updated_resources_integration"

        except Exception as e:
            metadata_editor.delete_resource_by_id(project_id=project_id, resource_id=resource_id)
            raise e
        else:
            metadata_editor.delete_resource_by_id(project_id=project_id, resource_id=resource_id)
            final_resources = metadata_editor.get_resources_by_id(project_id)
            assert isinstance(final_resources, pd.DataFrame)
            assert len(final_resources) == 0

    except Exception as e:
        metadata_editor.delete_project_by_id(project_id)
        raise e
    else:
        metadata_editor.delete_project_by_id(project_id)


def test_templates(metadata_editor, tmpdir):
    templates = metadata_editor.list_templates().drop_duplicates(["uid"])
    default_templates = templates[templates["default"]]
    for i, uid in enumerate(default_templates[["uid"]].values):
        temp = metadata_editor.get_template_by_uid(uid[0])
        metadata_type = metadata_editor._mm.standardize_metadata_name(temp.data_type)
        if metadata_type == "resource" or metadata_type == "geospatial":
            continue
        print(i, uid[0], metadata_type)

        metadata_type = metadata_type.replace("-", "_")

        class_def = metadata_editor.get_metadata_class(uid[0])
        assert (
            class_def._metadata_type__ == metadata_type
            if isinstance(class_def._metadata_type__, str)
            else class_def._metadata_type__.default == metadata_type
        )
        assert class_def._metadata_type_version__ is not None
        assert (
            class_def._template_uid__ == uid[0]
            if isinstance(class_def._template_uid__, str)
            else class_def._template_uid__.default == uid[0]
        )
        assert class_def._template_name__ is not None

        print(f"\n\n\n\n\n\n\ntemplate {uid[0]} of {metadata_type}")
        print("making skeleton")
        skeleton = make_skeleton(class_def)
        print(f"{skeleton}")
        print("skeleton made\n\n")
        assert (
            skeleton._metadata_type__ == metadata_type
            if isinstance(skeleton._metadata_type__, str)
            else skeleton._metadata_type__.default == metadata_type
        )
        assert skeleton._metadata_type_version__ is not None
        assert (
            skeleton._template_uid__ == uid[0]
            if isinstance(skeleton._template_uid__, str)
            else skeleton._template_uid__.default == uid[0]
        )
        assert skeleton._template_name__ is not None
        # log skeleton
        log_id = metadata_editor.create_project_log(metadata_type_or_template_uid=uid[0], metadata=skeleton)
        try:
            expected = metadata_editor.get_project_metadata_by_id(log_id, output_mode="pydantic")
            assert_pydantic_models_equal(skeleton, expected)

            filename1 = tmpdir.join(f"test_skeleton_from_log_{uid[0].replace(' ', '_').replace('.', '_')}.xlsx")
            # filename1 = f"test_skeleton_from_log_{uid[0].replace(' ', '_').replace('.', '_')}.xlsx"
            print(f"logging skeleton to {filename1}")
            metadata_editor.get_project_metadata_by_id(log_id, output_mode="excel", filename=filename1)
            # actual = metadata_editor._mm.read_metadata_from_excel(filename1, class_def)
            actual = metadata_editor.read_metadata_from_excel(filename1)
            assert (
                actual._metadata_type__ == metadata_type
                if isinstance(actual._metadata_type__, str)
                else actual._metadata_type__.default == metadata_type
            )
            assert actual._metadata_type_version__ is not None
            assert (
                actual._template_uid__ == uid[0]
                if isinstance(actual._template_uid__, str)
                else actual._template_uid__.default == uid[0]
            )
            assert actual._template_name__ is not None
            assert_pydantic_models_equal(skeleton, actual)
        finally:
            metadata_editor.delete_project_by_id(log_id)

        # fill in metadata then save and read back
        for i in range(3):
            modl = metadata_editor.make_metadata_outline(uid[0], output_mode="pydantic")
            fill_in_pydantic_outline(modl)

            # Write filled in metadata
            filename2 = tmpdir.join(f"test_{uid[0].replace(' ', '_').replace('.', '_')}_{i}.xlsx")
            # filename2 = f"test_{uid[0].replace(' ', '_').replace('.', '_')}_{i}.xlsx"
            # print(f"writing filled in metadata to {filename2}")
            # metadata_editor._mm.save_metadata_to_excel(modl, filename2, title=f"{metadata_type}_{uid}")
            metadata_editor.save_metadata_to_excel(modl, filename=filename2, title=f"{metadata_type}_{uid}")

            # Read the metadata back
            # actual = metadata_editor._mm.read_metadata_from_excel(filename2, class_def)
            actual = metadata_editor.read_metadata_from_excel(filename2)
            assert (
                actual._metadata_type__ == metadata_type
                if isinstance(actual._metadata_type__, str)
                else actual._metadata_type__.default == metadata_type
            )
            assert actual._metadata_type_version__ is not None
            assert (
                actual._template_uid__ == uid[0]
                if isinstance(actual._template_uid__, str)
                else actual._template_uid__.default == uid[0]
            )
            assert actual._template_name__ is not None
            assert_pydantic_models_equal(modl, actual)

        # log filled in metadata
        print("logging filled in metadata")
        print(f"{modl}\n\n")
        log_id = metadata_editor.create_project_log(metadata_type_or_template_uid=uid[0], metadata=modl)
        try:
            actual = metadata_editor.get_project_metadata_by_id(log_id, output_mode="pydantic", debug=True)
            print("actual from log direct")
            print(f"{actual}\n\n")
            assert (
                actual._metadata_type__ == metadata_type
                if isinstance(actual._metadata_type__, str)
                else actual._metadata_type__.default == metadata_type
            )
            assert actual._metadata_type_version__ is not None
            assert (
                actual._template_uid__ == uid[0]
                if isinstance(actual._template_uid__, str)
                else actual._template_uid__.default == uid[0]
            )
            assert actual._template_name__ is not None
            assert_pydantic_models_equal(modl, actual)

            filename3 = tmpdir.join(f"test_filledin_from_log_{uid[0].replace(' ', '_').replace('.', '_')}.xlsx")
            # filename3 = f"test_filledin_from_log_{uid[0].replace(' ', '_').replace('.', '_')}.xlsx"
            print(f"logging filled in metadata to {filename3}")
            metadata_editor.get_project_metadata_by_id(log_id, output_mode="excel", filename=filename3)
            # actual = metadata_editor._mm.read_metadata_from_excel(filename3, class_def)
            actual = metadata_editor.read_metadata_from_excel(filename3)
            print("actual from log via excel")
            print(f"{actual}\n\n")
            assert (
                actual._metadata_type__ == metadata_type
                if isinstance(actual._metadata_type__, str)
                else actual._metadata_type__.default == metadata_type
            )
            assert actual._metadata_type_version__ is not None
            assert (
                actual._template_uid__ == uid[0]
                if isinstance(actual._template_uid__, str)
                else actual._template_uid__.default == uid[0]
            )
            assert actual._template_name__ is not None
            assert_pydantic_models_equal(modl, actual)
        finally:
            metadata_editor.delete_project_by_id(log_id)


def test_change_mode_or_template(metadata_editor, tmpdir):
    # Define the template UID
    template_uid = "timeseries-system-en"

    # Create a metadata outline and fill it in
    modl = metadata_editor.make_metadata_outline(template_uid, output_mode="pydantic")
    fill_in_pydantic_outline(modl)

    # Convert the pydantic model to a dictionary
    dict_modl = metadata_editor.change_mode_or_template(modl, "dict")
    assert isinstance(dict_modl, dict)

    # Convert the dictionary back to a pydantic model and verify equality
    back_to_pydantic = metadata_editor.change_mode_or_template(dict_modl, "pydantic", input_template_uid=template_uid)
    assert_pydantic_models_equal(modl, back_to_pydantic)

    # Convert the dictionary to an Excel file
    filename_from_dict = metadata_editor.change_mode_or_template(
        dict_modl,
        "excel",
        input_template_uid=template_uid,
        filename=tmpdir.join(f"test_change_mode_or_template_{template_uid}.xlsx"),
    )

    # Convert the Excel file back to a pydantic model and verify equality
    from_excel_via_dict = metadata_editor.change_mode_or_template(
        filename_from_dict, "pydantic", input_template_uid=template_uid
    )
    assert_pydantic_models_equal(modl, from_excel_via_dict)

    # Convert the Excel file to a dictionary and then back to a pydantic model, verifying equality
    from_dict_via_excel = metadata_editor.change_mode_or_template(
        filename_from_dict, "dict", input_template_uid=template_uid
    )
    pydantic_from_dict_via_excel = metadata_editor.change_mode_or_template(
        from_dict_via_excel, "pydantic", input_template_uid=template_uid
    )
    assert_pydantic_models_equal(modl, pydantic_from_dict_via_excel)

    # Convert the pydantic model to an Excel file
    filename_from_pydantic = metadata_editor.change_mode_or_template(
        modl, "excel", filename=tmpdir.join(f"test_change_mode_or_template_{template_uid}2.xlsx")
    )

    # Convert the Excel file back to a pydantic model and verify equality
    from_excel_via_pydantic = metadata_editor.change_mode_or_template(
        filename_from_pydantic, "pydantic", input_template_uid=template_uid
    )
    assert_pydantic_models_equal(modl, from_excel_via_pydantic)

    # Convert the Excel file to a dictionary and then back to a pydantic model, verifying equality
    dict_from_excel_via_pydantic = metadata_editor.change_mode_or_template(
        filename_from_pydantic, "dict", input_template_uid=template_uid
    )
    pydantic_from_dict_via_pydantic = metadata_editor.change_mode_or_template(
        dict_from_excel_via_pydantic, "pydantic", input_template_uid=template_uid
    )
    assert_pydantic_models_equal(modl, pydantic_from_dict_via_pydantic)

    # Change the template UID and verify the conversion
    alternative_template_uid = "8603d94e27bccc2bdad1e00dbbf0fe32en"
    modl_alt = metadata_editor.change_mode_or_template(modl, "pydantic", output_template_uid=alternative_template_uid)
    modl_alt_from_dict = metadata_editor.change_mode_or_template(
        dict_modl, "pydantic", input_template_uid=template_uid, output_template_uid=alternative_template_uid
    )
    assert_pydantic_models_equal(modl_alt, modl_alt_from_dict)

    # Convert the Excel file to a pydantic model with the alternative template UID and verify equality
    modl_alt_from_excel = metadata_editor.change_mode_or_template(
        filename_from_dict, "pydantic", input_template_uid=template_uid, output_template_uid=alternative_template_uid
    )
    assert_pydantic_models_equal(modl_alt, modl_alt_from_excel)


def test_generic_api_request(metadata_editor):
    # Define the API URL and parameters

    list_projects_get_path = "/editor"
    params = {"offset": 0, "limit": 2}

    # Make a GET request to the API
    response = metadata_editor.generic_api_request("get", endpoint=list_projects_get_path, params=params)
    assert isinstance(response, dict)

    # Check if the response contains the expected keys
    assert "projects" in response, response
    assert len(response["projects"]) <= 10, response["projects"]


def test_execute_demo_notebook():
    notebook_path = os.path.join(os.path.dirname(__file__), "..", "demo", "demo.ipynb")
    executed_notebook_path = os.path.join(os.path.dirname(__file__), "..", "demo", "demo.ipynb")

    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": os.path.join(os.path.dirname(__file__), "..")}})

    with open(executed_notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
