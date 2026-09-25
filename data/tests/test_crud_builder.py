"""CRUD builder — migration, model, controller, request, resource, and route."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

import pytest

from craft.cli import crud_builder


FIELDS = [
    {"name": "name", "type": "string", "nullable": False},
    {"name": "price", "type": "decimal", "nullable": True},
    {"name": "active", "type": "boolean", "nullable": True, "rules": ["nullable", "boolean"]},
]


def _make_routes_file(base_path):
    routes_dir = os.path.join(base_path, "routes")
    os.makedirs(routes_dir, exist_ok=True)
    path = os.path.join(routes_dir, "api.py")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('from craft.facades import Route\n\nRoute.get("/", [None, "index"])\n')
    return path


def _make_web_routes_file(base_path):
    routes_dir = os.path.join(base_path, "routes")
    os.makedirs(routes_dir, exist_ok=True)
    path = os.path.join(routes_dir, "web.py")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('from craft.facades import Route\n\nRoute.get("/", [None, "index"])\n')
    return path


class TestBuildCrudFileShapes:
    def test_generates_every_expected_file(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))

        files = result["files"]
        assert result["entity"] == "Product"
        assert os.path.isfile(files["migration"])
        assert os.path.isfile(files["model"])
        assert os.path.isfile(files["request"])
        assert os.path.isfile(files["resource"])
        assert os.path.isfile(files["controller"])
        assert os.path.isfile(files["admin_view_index"])
        assert os.path.isfile(files["admin_view_create"])
        assert os.path.isfile(files["admin_view_edit"])
        assert os.path.isfile(files["admin_controller"])

    def test_migration_has_the_declared_columns(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["migration"], encoding="utf-8").read()

        assert 'Schema.create_table("products"' in source
        assert 't.string("name")' in source
        assert 't.decimal("price").nullable()' in source
        assert 't.boolean("active").nullable()' in source
        assert "t.id()" in source
        assert "t.uuid_key()" in source
        assert "t.timestamps()" in source


    def test_model_fillable_reflects_fields(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["model"], encoding="utf-8").read()

        assert "class Product(Model)" in source
        assert "fillable = ['name', 'price', 'active']" in source

    def test_controller_is_wired_to_real_orm_calls(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["controller"], encoding="utf-8").read()

        assert "from app.Models.Product import Product" in source
        assert "Product.query().paginate" in source
        assert "Product.find(id)" in source
        assert "Product.create(data)" in source
        assert '{"data": []}' not in source

    def test_resource_exposes_every_field(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["resource"], encoding="utf-8").read()

        for field in FIELDS:
            assert f'"{field["name"]}"' in source


class TestAdminUiGeneration:
    def test_admin_index_view_lists_every_field(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["admin_view_index"], encoding="utf-8").read()

        assert '@extends("layouts.app")' in source
        assert "records" in source
        for field in FIELDS:
            assert field["name"] in source
        assert "New Product" in source
        assert "No Product records yet." in source  # empty-state, dashed border pattern
        assert "/admin/products/create" in source

    def test_admin_create_view_has_one_input_per_field_and_csrf(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["admin_view_create"], encoding="utf-8").read()

        assert "@csrf" in source
        assert 'action="/admin/products"' in source
        assert 'name="name"' in source
        assert 'name="price"' in source
        assert 'type="checkbox" name="active"' in source
        assert "old('name')" in source

    def test_admin_edit_view_prefills_from_record_and_old(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["admin_view_edit"], encoding="utf-8").read()

        assert 'value="PUT"' in source
        assert "old('name') or record.get_attribute('name')" in source

    def test_admin_controller_is_distinct_from_json_api_controller(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["admin_controller"], encoding="utf-8").read()

        assert "class ProductAdminController(Controller):" in source
        assert "class ProductController" not in source
        assert "from app.Models.Product import Product" in source
        assert "def store(self, request):" in source
        assert "def update(self, request, id):" in source
        assert "def destroy(self, request, id):" in source
        # File paths never collide even though both controllers exist.
        assert result["files"]["controller"] != result["files"]["admin_controller"]
        assert "Admin" in result["files"]["admin_controller"]

    def test_admin_route_block_is_appended_and_idempotent(self, tmp_path):
        _make_routes_file(str(tmp_path))
        web_routes_path = _make_web_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(web_routes_path, encoding="utf-8").read()

        assert 'Route.resource("products", ProductAdminController)' in source
        assert 'prefix="/admin"' in source
        assert 'middleware="auth"' in source
        assert source.count(crud_builder.WEB_ROUTES_MARKER) == 1

    def test_running_twice_does_not_duplicate_the_admin_route(self, tmp_path):
        _make_routes_file(str(tmp_path))
        web_routes_path = _make_web_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path), force=True)
        crud_builder.build_crud("Product", FIELDS, str(tmp_path), force=True)
        source = open(web_routes_path, encoding="utf-8").read()

        assert source.count('Route.resource("products", ProductAdminController)') == 1
        assert source.count(
            "from app.Http.Controllers.Admin.ProductAdminController import ProductAdminController"
        ) == 1
        assert source.count(crud_builder.WEB_ROUTES_MARKER) == 1

    def test_build_crud_creates_the_web_routes_file_when_missing(self, tmp_path):
        # Skipping silently left the printed admin URL answering 404.
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))

        web_routes = os.path.join(str(tmp_path), "routes", "web.py")
        assert result["files"]["admin_routes"] == web_routes
        assert 'Route.resource("products", ProductAdminController)' in open(web_routes, encoding="utf-8").read()

    def test_json_api_and_admin_ui_coexist_for_the_same_entity(self, tmp_path):
        """Generating one entity produces both a JSON API controller/route
        and an admin HTML controller/route, with no name or file collision."""
        _make_routes_file(str(tmp_path))
        _make_web_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))

        files = result["files"]
        assert os.path.isfile(files["controller"])
        assert os.path.isfile(files["admin_controller"])
        assert files["controller"] != files["admin_controller"]
        assert os.path.isfile(files["routes"])
        assert os.path.isfile(files["admin_routes"])
        assert files["routes"] != files["admin_routes"]

        api_source = open(files["routes"], encoding="utf-8").read()
        web_source = open(files["admin_routes"], encoding="utf-8").read()
        assert 'Route.api_resource("products"' in api_source
        assert 'Route.resource("products", ProductAdminController)' in web_source


class TestFormRequestRules:
    def test_required_field_gets_required_rule(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["request"], encoding="utf-8").read()

        assert '"name": [\'required\']' in source or '"name": ["required"]' in source.replace("'", '"')

    def test_nullable_field_gets_nullable_rule(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["request"], encoding="utf-8").read()

        assert '"price": [\'nullable\']' in source or '"price": ["nullable"]' in source.replace("'", '"')

    def test_explicit_rules_are_preserved(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["request"], encoding="utf-8").read()

        assert "boolean" in source

    def test_authorize_checks_for_an_authenticated_user(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(result["files"]["request"], encoding="utf-8").read()

        assert "def authorize(self) -> bool:" in source
        assert "return self.user() is not None" in source
        assert "return True" not in source


class TestRouteAppendIsIdempotent:
    def test_route_is_appended_once(self, tmp_path):
        routes_path = _make_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(routes_path, encoding="utf-8").read()
        assert source.count('Route.api_resource("products"') == 1

    def test_write_routes_require_real_authentication(self, tmp_path):
        # Generated writes carry both aliases: `"api"` (a valid bearer token)
        # and `"auth"` (an authenticated session). Runtime enforcement of the
        # `"api"` alias itself is covered by
        # `test_api_token_middleware.py`.
        routes_path = _make_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        source = open(routes_path, encoding="utf-8").read()
        assert 'write_middleware=["api", "auth"]' in source

    def test_running_twice_does_not_duplicate_the_route(self, tmp_path):
        routes_path = _make_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path), force=True)
        crud_builder.build_crud("Product", FIELDS, str(tmp_path), force=True)
        source = open(routes_path, encoding="utf-8").read()

        assert source.count('Route.api_resource("products"') == 1
        assert source.count("from app.Http.Controllers.ProductController import ProductController") == 1

    def test_marker_comment_is_present_once(self, tmp_path):
        routes_path = _make_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path), force=True)
        crud_builder.build_crud("Product", FIELDS, str(tmp_path), force=True)
        source = open(routes_path, encoding="utf-8").read()

        assert source.count(crud_builder.ROUTES_MARKER) == 1


class TestOverwriteProtection:
    def test_refuses_to_overwrite_without_force(self, tmp_path):
        _make_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        with pytest.raises(FileExistsError):
            crud_builder.build_crud("Product", FIELDS, str(tmp_path))

    def test_force_overwrites(self, tmp_path):
        _make_routes_file(str(tmp_path))
        crud_builder.build_crud("Product", FIELDS, str(tmp_path))
        assert crud_builder.build_crud("Product", FIELDS, str(tmp_path), force=True)


class TestParseFields:
    def test_parses_name_type_rules(self):
        fields = crud_builder.parse_fields("name:string:required,price:decimal,active:boolean")
        assert fields[0] == {"name": "name", "type": "string", "rules": ["required"], "nullable": False}
        assert fields[1]["name"] == "price"
        assert fields[1]["nullable"] is True
        assert fields[2]["type"] == "boolean"

    def test_parses_extended_field_types(self):
        fields = crud_builder.parse_fields("metadata:json,count:big_integer,ratio:float")
        assert fields[0]["type"] == "json"
        assert fields[1]["type"] == "big_integer"
        assert fields[2]["type"] == "float"


    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            crud_builder.parse_fields("name:not_a_type")


class TestPretendMode:
    def test_pretend_mode_does_not_write_files(self, tmp_path):
        _make_routes_file(str(tmp_path))
        result = crud_builder.build_crud("Article", FIELDS, str(tmp_path), pretend=True)
        assert result["pretend"] is True
        assert not os.path.exists(result["files"]["model"])
        assert not os.path.exists(result["files"]["controller"])

