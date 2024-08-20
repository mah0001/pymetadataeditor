import os

import pandas as pd
import pytest

from pymetadataeditor import MetadataEditor


@pytest.fixture
def metadata_editor():
    # instantiate
    your_api_key = os.getenv("API_KEY")
    api_url = os.getenv("API_URL")
    me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)
    return me


def test_projects_integration(tmpdir, metadata_editor):
    """Do not use pytest.mark.parametrize since parallel runs cause the counts of projects to be off"""

    projects = metadata_editor.list_projects(limit="all")
    num_original_projects = len(projects)
    assert min(10, num_original_projects) == len(metadata_editor.list_projects(limit=10))
    assert num_original_projects - 1 == len(metadata_editor.list_projects(limit="all", offset=1))
    assert num_original_projects >= len(metadata_editor.list_projects(limit="all", metadata_type="timeseries"))
    assert num_original_projects == len(metadata_editor.list_projects(limit="all", sort_by="updated_asc"))

    # Good: "document", "survey", "table", "timeseries", "timeseries_db", "video"
    # fail due to not searchable: "geospatial", "script"
    # fail due to api saying "unknown type": "series"

    metadata_types = [
        "document",
        "survey",
        "table",
        "timeseries",
        "timeseries_db",
        "video",
    ]  # "document", "geospatial", "script", "series", "survey", "table", "timeseries", "timeseries_db", "video"
    creation_data = {
        "document": {
            "document_description": {
                "title_statement": {"idno": "integration_test_document", "title": "integration test document"}
            }
        },
        "geospatial": {
            "description": {"idno": "integration_test_geospatial"},
            "metadata_information": {
                "idno": "integration_test_geospatial",
                "title": "integration test geospatial",
            },
        },
        "script": {"doc_desc": {"idno": "integration_test_script"}},
        "series": {"idno": "integration_test_series", "name": "integration_test_series"},
        "survey": {
            "repositoryid": "integration_test_survey_repository_id",
            "study_desc": {
                "title_statement": {"idno": "integration_test_survey_idno", "title": "integration_test_survey title"},
                "study_info": {"nation": [{"name": "example_nation"}]},
            },
        },
        "table": {
            "table_description": {
                "title_statement": {"idno": "integration_test_table", "title": "integration test table"}
            }
        },
        "timeseries": {
            "idno": "integration_test_timeseries",
            "series_description": {"idno": "integration_test_timeseries", "name": "integration_test_timeseries"},
        },
        "timeseries_db": {
            "database_description": {
                "title_statement": {
                    "idno": "integration_test_timeseries_db",
                    "title": "integration_test_timeseries_db title",
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
        "script": {"doc_desc": {"idno": "integration_test_script", "title": "integration test script updated"}},
        "series": {"idno": "integration_test_series", "name": "integration_test_series_updated"},
        "survey": {
            "study_desc": {
                "title_statement": {
                    "idno": "integration_test_survey_idno",
                    "title": "integration_test_survey title updated",
                },
                "study_info": {"nation": [{"name": "example_nation"}]},
            }
        },
        "table": {
            "table_description": {
                "title_statement": {"idno": "integration_test_table", "title": "integration test table updated"}
            }
        },
        "timeseries": {
            "series_description": {"idno": "integration_test_timeseries", "name": "integration_test_timeseries_updated"}
        },
        "timeseries_db": {
            "database_description": {
                "title_statement": {
                    "idno": "integration_test_timeseries_db",
                    "title": "integration_test_timeseries_db title updated",
                }
            }
        },
        "video": {
            "video_description": {"idno": "integration_test_video", "title": "integration_test_video title updated"}
        },
    }
    patch_update_data = {
        "document": {
            "op": "add",
            "path": "/document_description/title_statement/title",
            "value": "patched integration test document updated",
        },
        "survey": [
            {
                "op": "replace",
                "path": "study_desc/title_statement/title",
                "value": "integration_test_survey title updated patched",
            }
        ],
        "table": [
            {"op": "remove", "path": "/table_description/title_statement/title"},
            {
                "op": "add",
                "path": "/table_description/title_statement/title",
                "value": "patched integration test table updated",
            },
        ],
        "timeseries": [
            {"op": "replace", "path": "series_description/name", "value": "patched integration_test_timeseries_updated"}
        ],
        "timeseries_db": {
            "op": "add",
            "path": "database_description/title_statement/title",
            "value": "integration_test_timeseries_db title updated patched",
        },
        "video": {
            "op": "replace",
            "path": "/video_description",
            "value": {"idno": "integration_test_video", "title": "integration_test_video title updated patched"},
        },
    }

    for metadata_type in metadata_types:
        # create project
        project_id = metadata_editor.create_project_log(
            metadata_type=metadata_type, metadata=creation_data[metadata_type]
        )

        try:
            assert len(metadata_editor.list_projects(limit="all")) == num_original_projects + 1

            # get project
            project_metadata = metadata_editor.get_project_by_id(project_id).metadata
            for k, v in creation_data[metadata_type].items():
                assert project_metadata[k] == v

            # update project
            metadata_editor.update_project_log_by_id(project_id, new_metadata=update_data[metadata_type])
            project_metadata_updated = metadata_editor.get_project_metadata_by_id(project_id, mode="dict")
            for k, v in update_data[metadata_type].items():
                assert project_metadata_updated[k] == v

            # check project is searchable and updated
            title_contains_updated = metadata_editor.list_projects(
                limit="all", keywords="updated", metadata_type=metadata_type
            )
            assert (
                project_id in title_contains_updated.index or str(project_id) in title_contains_updated.index
            ), title_contains_updated
            title_contains_bogus = metadata_editor.list_projects(
                limit="all", keywords="bogus", metadata_type=metadata_type
            )
            assert (
                project_id not in title_contains_bogus.index and str(project_id) not in title_contains_bogus.index
            ), title_contains_bogus

            # patch update
            title_contains_updated = metadata_editor.list_projects(
                limit="all", keywords="patched", metadata_type=metadata_type
            )
            assert (
                project_id not in title_contains_updated.index or str(project_id) in title_contains_updated.index
            ), title_contains_updated
            metadata_editor.patch_update_project_log_by_id(project_id, patches=patch_update_data[metadata_type])
            title_contains_updated = metadata_editor.list_projects(
                limit="all", keywords="patched", metadata_type=metadata_type
            )
            assert (
                project_id in title_contains_updated.index or str(project_id) in title_contains_updated.index
            ), title_contains_updated

            # save project to excel and then upload it
            if metadata_type == "geospatial":
                with pytest.raises(NotImplementedError):
                    filename = f"{metadata_type}_{project_id}.xlsx"
                    metadata_editor.get_project_metadata_by_id(project_id, mode="excel", filename=filename)
                    metadata_editor.update_project_log_by_id(project_id, filename)
            else:
                filename = f"{metadata_type}_{project_id}.xlsx"
                filename = os.path.join(tmpdir, filename)
                metadata_editor.get_project_metadata_by_id(project_id, mode="excel", filename=filename)
                metadata_editor.update_project_log_by_id(project_id, filename)
        finally:
            metadata_editor.delete_project_by_id(project_id)
        # except Exception as e:
        #     metadata_editor.delete_project_by_id(project_id)
        #     raise e

        # # delete project
        # metadata_editor.delete_project_by_id(project_id)
        final_projects = metadata_editor.list_projects(limit="all")
        assert len(final_projects) == num_original_projects


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
            metadata_type="timeseries",
            metadata={"idno": project_idno, "series_description": {"idno": project_idno, "name": project_name}},
        )
        try:
            metadata_editor.add_projects_to_collection(collection_id, "id", project_id)

            # check the project can be found
            oneproject_collection = metadata_editor.list_projects_in_collection(collection_id, limit="all")
            assert len(oneproject_collection) == 1
            assert oneproject_collection.iloc[0].idno == project_idno
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
            assert good_search.iloc[0].idno == project_idno
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
            metadata_editor.remove_projects_from_collection(collection_id, "idno", project_idno)
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
        "timeseries",
        {
            "idno": "resources_integration_test",
            "series_description": {"idno": "resources_integration_test", "name": "integration_test_of_resources"},
        },
    )
    try:
        initial_resources = metadata_editor.list_resources_by_id(project_id)
        assert isinstance(initial_resources, pd.DataFrame)
        assert len(initial_resources) == 0

        filename = "resources_integration.txt"
        temp_file = tmpdir.join(filename)
        temp_file.write("dummy content")
        filename = str(temp_file)

        resource_id = metadata_editor.create_resource(
            project_id, dctype="txt", title="resources_integration", filename=filename
        )
        try:
            resources = metadata_editor.list_resources_by_id(project_id)
            assert isinstance(resources, pd.DataFrame)
            assert len(resources) == 1
            resources.iloc[0].title = "resources_integration"

            metadata_editor.update_resource(
                project_id=project_id, resource_id=resource_id, dctype="txt", title="updated_resources_integration"
            )
            resources = metadata_editor.list_resources_by_id(project_id)
            assert isinstance(resources, pd.DataFrame)
            assert len(resources) == 1
            resources.iloc[0].title = "updated_resources_integration"

        except Exception as e:
            metadata_editor.delete_resource_by_id(project_id=project_id, resource_id=resource_id)
            raise e
        else:
            metadata_editor.delete_resource_by_id(project_id=project_id, resource_id=resource_id)
            final_resources = metadata_editor.list_resources_by_id(project_id)
            assert isinstance(final_resources, pd.DataFrame)
            assert len(final_resources) == 0

    except Exception as e:
        metadata_editor.delete_project_by_id(project_id)
        raise e
    else:
        metadata_editor.delete_project_by_id(project_id)
