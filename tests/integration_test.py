import os

import pytest
from requests import HTTPError

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
    # list
    projects = metadata_editor.list_projects()
    num_original_projects = len(projects)

    metadata_types = ["timeseries", "survey"]
    create_functions = {
        "timeseries": metadata_editor.create_and_log_timeseries,
        "survey": metadata_editor.create_and_log_survey_microdata,
    }
    update_functions = {
        "timeseries": metadata_editor.update_timeseries_by_id,
        "survey": metadata_editor.update_survey_microdata_by_id,
    }
    creation_data = {
        "timeseries": {
            "idno": "integration_test_timeseries",
            "series_description": {"idno": "integration_test_timeseries", "name": "integration_test_timeseries"},
        },
        "survey": {
            "repositoryid": "example_survey_repository_id",
            "study_desc": {
                "title_statement": {"idno": "example_survey_idno", "title": "survey_example_title"},
                "study_info": {"nation": [{"name": "example_nation"}]},
            },
        },
    }
    update_data = {
        "timeseries": {
            "series_description": {"idno": "integration_test_timeseries", "name": "integration_test_timeseries_updated"}
        },
        "survey": {
            "study_desc": {
                "title_statement": {"idno": "example_survey_idno", "title": "survey_example_title_updated"},
                "study_info": {"nation": [{"name": "example_nation"}]},
            }
        },
    }

    for metadata_type in metadata_types:
        # create project
        project_id = create_functions[metadata_type](**creation_data[metadata_type])
        assert len(metadata_editor.list_projects()) == num_original_projects + 1

        # get project
        project_metadata = metadata_editor.get_project_by_id(project_id).metadata
        for k, v in creation_data[metadata_type].items():
            assert project_metadata[k] == v

        # update timeseries
        update_functions[metadata_type](project_id, **update_data[metadata_type])
        project_metadata_updated = metadata_editor.get_project_by_id(project_id).metadata
        for k, v in update_data[metadata_type].items():
            assert project_metadata_updated[k] == v

        # delete timeseries
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
    assert len(metadata_editor.list_collections()) == num_original_collections + 1

    collection_description_updated = "integration_test_collection_updated"
    metadata_editor.update_collection(id=collection_id, description=collection_description_updated)
    updated_collection = metadata_editor.get_collection_by_id(collection_id)
    updated_collection.title = collection_title_updated
    updated_collection.description = collection_description_updated
    assert len(metadata_editor.list_collections()) == num_original_collections + 1

    # count projects in collection (should be zero)
    initial_projects_collection = metadata_editor.list_projects_in_collection(collection_id)
    assert len(initial_projects_collection) == 0, f"expected zero projects but got {initial_projects_collection}"

    # create a project and add it to the collection by id
    project_idno = "project_for_collection_integration_test"
    project_name = "project_for_collection_integration_test"
    project_id = metadata_editor.create_and_log_timeseries(
        idno=project_idno, series_description={"idno": project_idno, "name": project_name}
    )
    metadata_editor.add_projects_to_collection(collection_id, "id", project_id)
    oneproject_collection = metadata_editor.list_projects_in_collection(collection_id)
    assert len(oneproject_collection) == 1
    assert oneproject_collection.iloc[0].idno == project_idno

    # set template for collection
    metadata_editor.set_template_for_collection(
        collection_id=collection_id, template_uid="timeseries-system-en", project_type="timeseries"
    )

    # setting a non-existant template raises an error
    with pytest.raises(HTTPError):
        metadata_editor.set_template_for_collection(
            collection_id=collection_id, template_uid="no_such_template", project_type="timeseries"
        )

    # remove that project by idno
    metadata_editor.remove_projects_from_collection(collection_id, "idno", project_idno)
    final_collection = metadata_editor.list_projects_in_collection(collection_id)
    assert len(final_collection) == 0
    metadata_editor.delete_project_by_id(project_id)

    # delete collection
    metadata_editor.delete_collection_by_id(collection_id)
    assert len(metadata_editor.list_collections()) == num_original_collections
