# pymetadataeditor v2 — legacy API migration

Migration reference for **pymetadataeditor v2** (`me = MetadataEditor(...)`).

Sub-clients return **raw API `dict`s** unless noted. There is **no backward compatibility** with the old flat methods on `MetadataEditor`.

---

## Projects

| Old | New |
|-----|-----|
| `me.count_projects()` | `me.projects.count()` |
| `me.list_projects(limit=..., offset=..., keywords=..., ...)` | `me.projects.list(...)` |
| `me.list_projects(limit="all", ...)` | `me.projects.iter_all(...)` (generator) or `me.projects.list_all(...)` |
| `me.get_project_by_id(id)` | `me.projects.get(id)` |
| `me.delete_project_by_id(id)` | `me.projects.delete(id)` — **POST** `/editor/delete/{id}` |
| `me.patch_update_project_log_by_id(id, type, patches)` | `me.projects.patch(project_id, patches, project_type=None)` |
| `me.patch_update_project_log_by_id(...)` (single op) | `me.projects.patch_one(project_id, op, path, value=..., project_type=None)` |
| *(no direct old equivalent)* | `me.projects.create(project_type, metadata)` |
| *(no direct old equivalent)* | `me.projects.update(id, project_type, metadata)` |
| *(no direct old equivalent)* | `me.projects.get_json(...)`, `get_json_field(...)`, `generate_pdf(...)`, `import_file(...)`, version helpers |

---

## Metadata workflows (template-aware create / update / get)

| Old | New |
|-----|-----|
| `me.get_project_metadata_by_id(id, output_mode=..., ...)` | `me.metadata.get(project_id, output_mode=..., ...)` |
| `me.create_project_log(metadata, type)` | `me.metadata.create(metadata, metadata_type_or_template_uid=...)` |
| `me.update_project_log_by_id(id, metadata)` | `me.metadata.update(id, new_metadata)` |

---

## Collections

| Old | New |
|-----|-----|
| `me.list_collections()` → `pd.DataFrame` | `me.collections.list()` → `dict` |
| `me.get_collection_by_id(id)` → `pd.Series` | `me.collections.get(id)` → `dict` (`response["collection"]`) |
| `me.create_collection(title, description)` → id | `me.collections.create(title, description)` → full `dict` (`["collection"]` for id) |
| `me.update_collection(id, title=..., description=...)` | `me.collections.update(id, title=..., description=...)` |
| `me.delete_collection_by_id(id)` | `me.collections.delete(id)` — **POST** `/collections/delete/{id}` |
| `me.copy_collection(source_id, target_id)` | `me.collections.copy(source_id, target_id)` |
| `me.move_collection(source_id, target_id)` | `me.collections.move(source_id, target_id)` |
| `me.count_projects_in_collection(collection)` | `me.collections.count_projects(collection_id)` |
| `me.list_projects_in_collection(collection, limit=..., ...)` → `pd.DataFrame` | `me.collections.list_projects(collection_id, limit=..., ...)` → `dict` |
| `me.list_projects_in_collection(..., limit="all")` | `me.collections.iter_projects(collection_id, ...)` (generator; wrap in `list()` for all) |
| `me.add_projects_to_collection(collection, id_format, projects)` | `me.collections.add_projects(collections, id_format, projects)` |
| `me.remove_projects_from_collection(collection, id_format, projects)` | `me.collections.remove_projects(collections, id_format, projects)` |
| `me.set_template_for_collection(collection_id, template_uid)` *(auto `project_type`)* | `me.collections.set_template(collection_id, template_uid, project_type)` — **`project_type` required** |
| *(no old equivalent)* | `me.collections.permissions()` |

---

## Templates

| Old | New |
|-----|-----|
| `me.list_templates()` → `pd.DataFrame` | `me.templates.list()` → `dict` |
| `me.list_templates()` *(default-template cache for `get_metadata_class`)* | `me._refresh_default_templates_cache()` → `pd.DataFrame` *(internal)* |
| `me.get_template_by_uid(uid)` → `pd.Series` | `me.templates.get(uid)` → template `dict` (`uid`, `name`, `data_type`, `template`, …) |
| `me.get_template_by_uid(uid)` *(pydantic class building)* | `me._ensure_template_cached(uid)` → `pd.Series` *(internal)* |
| `me.delete_template(uid)` | `me.templates.delete(uid)` |
| *(no old equivalent)* | `me.templates.create(...)`, `update(...)`, `duplicate(...)`, `translation_keys(...)` |

---

## Resources

| Old | New |
|-----|-----|
| `me.get_resources_by_id(project_id)` → `pd.DataFrame` | `me.resources.list(project_id)` → `dict` |
| `me.log_resource(project_id, dctype, title, ..., filename=path)` | `me.resources.create(project_id, dctype, title, ..., file_path=path)` |
| `me.update_resource(project_id, resource_id, ..., filename=path)` | `me.resources.update(project_id, resource_id, ..., file_path=path)` |
| `me.delete_resource_by_id(project_id, resource_id)` | `me.resources.delete(project_id, resource_id)` |
| *(no old equivalent)* | `me.resources.import_file(project_id, file_path)` |

---

## Generic / escape hatch

| Old | New |
|-----|-----|
| `me.generic_api_request("get"\|"post", endpoint, ...)` | `me.api.request(method, path, ...)` — also **PUT**, **DELETE**, and `id=` |
| *(use specific methods)* | `me.api.get(path, ...)` |
| *(use specific methods)* | `me.api.post(path, json=...)` or `post(path, data=..., files=...)` |
| *(use specific methods)* | `me.api.put(path, ...)` |
| *(use specific methods)* | `me.api.delete(path, ...)` |
| *(use specific methods)* | `me.api.request(method, path, ...)` |

---

## Unchanged on `MetadataEditor`

These remain on `me` directly (not moved to sub-clients):

- `get_metadata_class`
- `make_metadata_outline`
- `change_mode_or_template`
- `read_metadata_from_excel`
- LLM / Excel helpers

---

## 0.5.0 changes

Changes from 0.4.0 that can break existing calls. All other 0.5.0 additions are new methods or optional arguments.

Every project argument is now `project_id` (type `ProjectIdOrIdno`): the numeric project id or the project idno. IDNOs cannot be numeric only, so a numeric value is always the id.

Methods that only queue work start with `queue_` and return the job id; pass `wait=True` to block until the job finishes. `me.jobs.*` is the editor job queue (`uuid`); `me.indicators.*_data_job` are indicator data jobs (`job_id`). `me.publish.*` methods run now (no queue).

| 0.4.0 | 0.5.0 |
|-----|-----|
| `me.codelists.list(limit=50, offset=0, ...)` | `me.codelists.list(page=1, per_page=50, flat=False, ...)` — returns `{codelists, total, page, per_page, collapsed}`; versions are collapsed into one row unless `flat=True`. Use `me.codelists.iter_all(...)` for everything |
| `me.projects.delete_version_by_id(id, version)` | `me.projects.delete_version_by_id(version_project_id)` — the id of the version project itself |
| `me.projects.list(exclude_collections="...")` | `me.projects.list(collection=..., exclude_collections=True)` — bool; raises `ValueError` without `collection` |
| `me.jobs.list(limit=...)` *(any limit)* | Raises `ValueError` when `limit > 100` (server maximum); use `me.jobs.iter_all(...)` |
| `me.projects.get(id=...)`, `basic_info`, `update`, `patch`, `patch_one`, `delete`, `get_json`, `get_json_field`, `generate_pdf`, `list_versions`, `create_version`, `delete_version` | Argument renamed `id` → `project_id` (only affects keyword calls) |
| `me.metadata.get_for_project(id=...)`, `me.metadata.update(id=...)` | `me.metadata.get(project_id=...)`, `me.metadata.update(project_id=...)` |
| `me.indicators.*(project=...)`, `me.indicators.notes.*(project=...)` | `project_id=...` |
| `me.indicators.project_id(project)` | `me.projects.resolve_id(project_id)` → numeric id; `me.projects.resolve_idno(project_id)` → idno |
| `me.indicators.load_many(...)` rows: `project` | `project_id` |
| `me.jobs.create(job_type, payload)` | `me.jobs.queue(job_type, payload)` |
| `me.jobs.publish_to_nada(...)` | `me.jobs.queue_publish_to_nada(...)` |
| `me.jobs.publish_to_nada_and_wait(...)` | `me.jobs.queue_publish_to_nada(..., wait=True)` |
| `me.jobs.import_indicator_data(...)` | `me.jobs.queue_indicator_data_import(...)` |
| `me.jobs.import_indicator_data_and_wait(...)` | `me.jobs.queue_indicator_data_import(..., wait=True)` |
| `me.indicators.recompute(project_id)` | `me.indicators.queue_recompute(project_id, wait=False)` |
| `me.indicators.job(project_id, job_id)` | `me.indicators.get_data_job(project_id, job_id)`; new `wait_data_job` |
| `me.indicators.publish(project_id, conn, metadata_options=...)` | `me.publish.project(project_id, conn, publish_dsd=True, dsd_overwrite=True, publish_indicator_data=True, options={"overwrite": "yes", ...})` — returns `{results, errors}`; also publishes the thumbnail and resources unless turned off |
| `me.publish.indicator(...)` | `me.publish.indicator_data(...)` |
| `me.publish.generate_json(project_id)` | `me.projects.generate_json(project_id)` |
| `me.generic_api_request(method, endpoint, ...)` | `me.api.request(method, endpoint, ...)` |
| `me.indicators.reset(project_id)` | `me.indicators.delete_data(project_id)` — also deletes the CSV archive, and fails when the data service is unavailable |
| `me.indicators.notes.add(...)` | `me.indicators.notes.upsert(...)` (adds or updates by note ID) |
| `me.data_structures.export(...)` | `me.data_structures.export_json(...)` (pairs with `import_json`) |
| `me.projects.import_project(project_type, file_path)` | `me.projects.import_file(project_type, file_path)` |
| `me.projects.patch(id, project_type, patches, validate=False)` | `me.projects.patch(project_id, patches, project_type=None, validate=True)` — `project_type` is looked up when omitted; patches are checked before sending; the patched metadata is schema-validated by default |
| `me.projects.patch_one(id, project_type, op, path, value=None)` | `me.projects.patch_one(project_id, op, path, value=..., from_path=None, project_type=None, validate=True)` — `value=None` now sends JSON `null`; `from_path` enables `move` / `copy` |
| `me.publish.*(project_id="<idno>")` | The idno is resolved to the numeric id first (the publish endpoints need it) |
| `me.jobs.list(project_id="<idno>")` | The idno is resolved to the numeric id (one extra `basic_info` call) |
| `me.indicators.data_rows(..., limit=...)` *(any limit)* | Raises `ValueError` when `limit > 200` (server maximum); use `me.indicators.iter_data_rows(...)` |
| `me.collections.list_projects(collection_id)` → `POST /collections/projects` | `me.collections.list_projects(collection_id, limit=..., offset=..., keywords=..., ...)` — one page from `GET /editor?collection=` |
| `me.collections.list_projects_via_editor(...)` | `me.collections.list_projects(...)` |
| `me.collections.list_projects_all(collection_id, ...)` | `list(me.collections.iter_projects(collection_id, ...))` |
| `me.codelists.versions`, `codes`, `translations` | `me.codelists.list_versions`, `list_codes`, `list_translations` |
| `me.data_structures.versions`, `components`, `projects` | `me.data_structures.list_versions`, `list_components`, `list_projects` |
| `me.templates.get(uid)["result"]` | `me.templates.get(uid)` — the template `dict` itself, no `result` wrapper |
| `me.projects.count()` | `me.projects.count(**filters)` — same result without filters |

New in 0.5.0: `publish.project`, `publish.thumbnail`, `publish.resources`, `publish.resource`, `publish.delete_nada_resources`, `publish.list_files`, `publish.create_catalog_connection`, `indicators.wait_data_job`, `projects.resolve_id`, `projects.resolve_idno`, `projects.iter_all`, `projects.facets`, `projects.basic_info`, `templates.defaults`, `collections.iter_projects`, `jobs.iter_all`, `codelists.iter_all`, `codelists.iter_codes`, `data_structures.iter_all`, `data_structures.iter_projects`, `indicators.iter_data_rows`, `indicators.get_dsd(detailed=..., resolve_codelists=...)`, `metadata.get_for_project(..., include_variables=...)`.

---

## Notes

1. **Return types:** Many list/get helpers went from **pandas** (`DataFrame` / `Series`) to **`dict`** (API JSON).
2. **Deletes in restricted networks:** Prefer typed **POST** delete routes (`projects.delete`, `collections.delete`). Raw **DELETE** on `/collections/{id}` may be blocked by proxies; the editor UI uses POST aliases.
3. **`me.api.post` payloads:**
   - `json={...}` — JSON body (`Content-Type: application/json`)
   - `data={...}` — form fields (`application/x-www-form-urlencoded`)
   - `data={...}` + `files={...}` — multipart uploads (e.g. resources)
   - Do not mix `json` and `data`/`files` on the same call unless you know the server expects it.
4. **Unwrapped endpoints:** Use `me.api.post("/any/path", ...)` when no typed client method exists yet.
