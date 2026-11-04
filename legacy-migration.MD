# pymetadataeditor v2 — legacy API migration

Migration reference for **pymetadataeditor v2** (`me = MetadataEditor(...)`).

Sub-clients return **raw API `dict`s** unless noted. There is **no backward compatibility** with the old flat methods on `MetadataEditor`.

---

## Projects

| Old | New |
|-----|-----|
| `me.count_projects()` | `me.projects.count()` |
| `me.list_projects(limit=..., offset=..., keywords=..., ...)` | `me.projects.list(...)` |
| `me.list_projects(limit="all", ...)` | `me.projects.list_all(...)` |
| `me.get_project_by_id(id)` | `me.projects.get(id)` |
| `me.delete_project_by_id(id)` | `me.projects.delete(id)` — **POST** `/editor/delete/{id}` |
| `me.patch_update_project_log_by_id(id, type, patches)` | `me.projects.patch(id, project_type, patches)` |
| `me.patch_update_project_log_by_id(...)` (single op) | `me.projects.patch_one(id, project_type, op, path, value=...)` |
| *(no direct old equivalent)* | `me.projects.create(project_type, metadata)` |
| *(no direct old equivalent)* | `me.projects.update(id, project_type, metadata)` |
| *(no direct old equivalent)* | `me.projects.get_json(...)`, `get_json_field(...)`, `generate_pdf(...)`, `import_project(...)`, version helpers |

---

## Metadata workflows (template-aware create / update / get)

| Old | New |
|-----|-----|
| `me.get_project_metadata_by_id(id, output_mode=..., ...)` | `me.metadata.get_for_project(id, output_mode=..., ...)` |
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
| `me.list_projects_in_collection(collection, limit=..., ...)` → `pd.DataFrame` | `me.collections.list_projects_via_editor(...)` or `me.collections.list_projects_all(...)` → `dict` |
| `me.list_projects_in_collection(..., limit="all")` | `me.collections.list_projects_all(collection_id, ...)` |
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
| `me.get_template_by_uid(uid)` → `pd.Series` | `me.templates.get(uid)` → `dict` (`response["result"]`) |
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
| `me.generic_api_request("get"\|"post", endpoint, ...)` | `me.generic_api_request(method, endpoint, ...)` — also **PUT**, **DELETE**, and `id=` |
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

## Notes

1. **Return types:** Many list/get helpers went from **pandas** (`DataFrame` / `Series`) to **`dict`** (API JSON).
2. **Deletes in restricted networks:** Prefer typed **POST** delete routes (`projects.delete`, `collections.delete`). Raw **DELETE** on `/collections/{id}` may be blocked by proxies; the editor UI uses POST aliases.
3. **`me.api.post` payloads:**
   - `json={...}` — JSON body (`Content-Type: application/json`)
   - `data={...}` — form fields (`application/x-www-form-urlencoded`)
   - `data={...}` + `files={...}` — multipart uploads (e.g. resources)
   - Do not mix `json` and `data`/`files` on the same call unless you know the server expects it.
4. **Unwrapped endpoints:** Use `me.api.post("/any/path", ...)` when no typed client method exists yet.
