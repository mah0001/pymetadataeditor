import os

import pytest

from pymetadataeditor import MetadataEditor


@pytest.fixture
def metadata_editor():
    # instantiate
    your_api_key = os.getenv("API_KEY")
    api_url = os.getenv("API_URL")
    me = MetadataEditor(api_url=api_url, api_key=your_api_key, verify_ssl=False)
    return me


def test_projects_integration(metadata_editor):
    """Do not use pytest.mark.parametrize since parallel runs cause the counts of projects to be off"""

    projects = metadata_editor.list_projects()
    num_original_projects = len(projects)
    # fail due to api saying "unknown type": "series", "timeseries_db",
    metadata_types = ["document", "geospatial", "script", "survey", "table", "timeseries", "video"]
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
        "script": {"doc_desc": {"idno": "integration_test_script", "title": "integration_test_script_updated"}},
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

    for metadata_type in metadata_types:
        # create project
        create_function = getattr(metadata_editor, "create_log_of_{}".format(metadata_type))
        update_function = getattr(metadata_editor, "update_{}_by_id".format(metadata_type))
        project_id = create_function(**creation_data[metadata_type])

        try:
            assert len(metadata_editor.list_projects()) == num_original_projects + 1

            # get project
            project_metadata = metadata_editor.get_project_by_id(project_id).metadata
            for k, v in creation_data[metadata_type].items():
                assert project_metadata[k] == v

            # update project
            update_function(project_id, **update_data[metadata_type])
            project_metadata_updated = metadata_editor.get_project_metadata_by_id(project_id)
            for k, v in update_data[metadata_type].items():
                assert project_metadata_updated[k] == v

            # # check project is searchable and updated
            # title_contains_updated = metadata_editor.list_projects(keywords="updated")
            # assert (
            #     project_id in title_contains_updated.index or str(project_id) in title_contains_updated.index
            # ), title_contains_updated
            # title_contains_bogus = metadata_editor.list_projects(keywords="bogus")
            # assert (
            #     project_id not in title_contains_bogus.index and str(project_id) not in title_contains_bogus.index
            # ), title_contains_bogus

            # save project to excel and then upload it
            if metadata_type == "geospatial":
                with pytest.raises(NotImplementedError):
                    filename = f"{metadata_type}_{project_id}.xlsx"
                    metadata_editor.save_project_metadata_to_excel(project_id, filename)
                    metadata_editor.update_by_id_from_excel(project_id, metadata_type, filename)
            else:
                filename = f"{metadata_type}_{project_id}.xlsx"
                metadata_editor.save_project_metadata_to_excel(project_id, filename)
                metadata_editor.update_by_id_from_excel(project_id, metadata_type, filename)
        except Exception as e:
            metadata_editor.delete_project_by_id(project_id)
            raise e

        # delete project
        metadata_editor.delete_project_by_id(project_id)
        final_projects = metadata_editor.list_projects()
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
    initial_projects_collection = metadata_editor.list_projects_in_collection(collection_id)
    assert len(initial_projects_collection) == 0, f"expected zero projects but got {initial_projects_collection}"

    # create a project and add it to the collection by id
    project_idno = "project for collection integration test"
    project_name = "project for collection integration test"
    project_id = metadata_editor.create_and_log_timeseries(
        idno=project_idno, series_description={"idno": project_idno, "name": project_name}
    )
    metadata_editor.add_projects_to_collection(collection_id, "id", project_id)

    # check the project can be found
    oneproject_collection = metadata_editor.list_projects_in_collection(collection_id)
    assert len(oneproject_collection) == 1
    assert oneproject_collection.iloc[0].idno == project_idno
    good_search = metadata_editor.list_projects_in_collection(collection_id, keywords="integration")
    assert len(good_search) == 1
    assert good_search.iloc[0].idno == project_idno
    bad_search = metadata_editor.list_projects_in_collection(collection_id, keywords="bogus")
    assert len(bad_search) == 0

    # remove that project by idno
    metadata_editor.remove_projects_from_collection(collection_id, "idno", project_idno)
    final_collection = metadata_editor.list_projects_in_collection(collection_id)
    assert len(final_collection) == 0
    metadata_editor.delete_project_by_id(project_id)

    # delete collection
    metadata_editor.delete_collection_by_id(collection_id)
    assert len(metadata_editor.list_collections()) == num_original_collections
