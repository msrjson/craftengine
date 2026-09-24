{#
    Admin — CRUD builder form.

    Rendered by `app/Http/Controllers/Admin/CrudBuilderController.py::index` and
    re-rendered by `store()` when validation fails, at `/admin/crud-builder`,
    behind `auth` + `role:admin`. That guard is not decoration: the builder
    writes real `.py` files into `app/` and `database/migrations/` and rewrites
    `routes/`, so behind `auth` alone it would be remote code execution for any
    registered user.

    Context:
      errors        dict   validation messages, keyed by field
      old           dict   submitted values, so a failed submit is not retyped
      field_rows    list   the entity's field definitions, preserved on failure
      show_sidebar  bool
#}
@extends("layouts.app")

@section("title", "CRUD Builder — Admin")

@section("content")
<div class="max-w-4xl bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm">
    <div class="flex items-center justify-between mb-4">
        <div>
            <h1 class="text-2xl font-bold text-slate-900 mb-1">CRUD Builder</h1>
            <p class="text-slate-500 text-sm">Describe an entity and its fields; a migration with UUID support, Model, Controller,
                FormRequest, Resource, API route and Admin UI will be generated automatically.</p>
        </div>
        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-orange-50 text-orange-700 border border-orange-200">
            Active Record + Admin UI
        </span>
    </div>

    @if(errors|length > 0)
    <div class="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-sm space-y-1">
        @foreach(errors as message)
            <p>{{ message }}</p>
        @endforeach
    </div>
    @endif

    <form action="/admin/crud-builder" method="POST" class="space-y-6" id="crud-builder-form">
        @csrf

        <div class="space-y-2">
            <label for="entity" class="block text-sm font-semibold text-slate-700">Entity name</label>
            <input type="text" name="entity" id="entity" value="{{ entity }}" placeholder="Product"
                   class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500"
                   required>
            <p class="text-xs text-slate-400">Singular, PascalCase or snake_case — e.g. "Product" or "order_item".</p>
        </div>

        <!-- Field Presets Quick-Add Toolbar -->
        <div class="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div class="flex items-center justify-between">
                <span class="text-xs font-bold uppercase tracking-wider text-slate-500">Quick Field Presets</span>
                <span class="text-xs text-slate-400">Click to append common fields</span>
            </div>
            <div class="flex flex-wrap gap-2 pt-1">
                <button type="button" class="preset-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:border-orange-400 hover:text-orange-600 transition" data-name="name" data-type="string" data-req="1">+ Name (string, req)</button>
                <button type="button" class="preset-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:border-orange-400 hover:text-orange-600 transition" data-name="title" data-type="string" data-req="1">+ Title (string, req)</button>
                <button type="button" class="preset-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:border-orange-400 hover:text-orange-600 transition" data-name="description" data-type="text" data-req="0">+ Description (text)</button>
                <button type="button" class="preset-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:border-orange-400 hover:text-orange-600 transition" data-name="price" data-type="decimal" data-req="1">+ Price (decimal, req)</button>
                <button type="button" class="preset-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:border-orange-400 hover:text-orange-600 transition" data-name="active" data-type="boolean" data-req="0">+ Active (boolean)</button>
                <button type="button" class="preset-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:border-orange-400 hover:text-orange-600 transition" data-name="metadata" data-type="json" data-req="0">+ Metadata (json)</button>
                <button type="button" class="preset-btn px-2.5 py-1 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:border-orange-400 hover:text-orange-600 transition" data-name="due_date" data-type="date" data-req="0">+ Due Date (date)</button>
            </div>
        </div>

        <div class="space-y-3">
            <div class="flex items-center justify-between">
                <label class="block text-sm font-semibold text-slate-700">Entity Fields</label>
                <button type="button" id="add-field-row"
                        class="text-xs font-bold text-orange-600 hover:text-orange-700 bg-orange-50 hover:bg-orange-100 px-3 py-1.5 rounded-lg transition">
                    + Add Field Row
                </button>
            </div>

            <div id="field-rows" class="space-y-3"></div>
        </div>

        <div id="client-error-box" class="hidden p-4 rounded-xl bg-rose-50 border border-rose-100 text-rose-700 text-sm"></div>

        <div class="flex items-center space-x-4 pt-2">
            <button type="submit" id="submit-btn"
                    class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                Generate CRUD Slice
            </button>
        </div>
    </form>
</div>

<!-- Restored Fields from previous submit -->
<div id="field-rows-data" data-fields="{{ fields_json }}" class="hidden"></div>

<template id="field-row-template">
    <div class="flex items-center space-x-3 field-row bg-slate-50/50 p-2.5 rounded-xl border border-slate-200">
        <!-- Reorder buttons -->
        <div class="flex flex-col space-y-0.5">
            <button type="button" class="move-up-btn text-[10px] text-slate-400 hover:text-slate-700 p-0.5" title="Move Up">▲</button>
            <button type="button" class="move-down-btn text-[10px] text-slate-400 hover:text-slate-700 p-0.5" title="Move Down">▼</button>
        </div>
        <div class="flex-1">
            <label class="sr-only field-name-label">Field name</label>
            <input type="text" placeholder="field_name" class="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm field-name-input bg-white focus:outline-none focus:border-orange-500">
        </div>
        <div>
            <label class="sr-only field-type-label">Field type</label>
            <select class="px-3 py-2 rounded-lg border border-slate-200 text-sm field-type-input bg-white focus:outline-none focus:border-orange-500">
                @foreach(field_types as type)
                    <option value="{{ type }}">{{ type }}</option>
                @endforeach
            </select>
        </div>
        <label class="flex items-center text-xs text-slate-600 space-x-1 select-none pr-2">
            <input type="checkbox" class="field-required-input rounded border-slate-300 text-orange-600 focus:ring-orange-500">
            <span>required</span>
        </label>
        <button type="button" class="text-xs text-rose-500 hover:text-rose-700 font-medium remove-field-row px-2 py-1 rounded hover:bg-rose-50 transition">Remove</button>
    </div>
</template>

<script>
(function () {
    var rowsContainer = document.getElementById("field-rows");
    var template = document.getElementById("field-row-template");
    var form = document.getElementById("crud-builder-form");
    var errorBox = document.getElementById("client-error-box");
    var counter = 0;

    function addRow(data) {
        data = data || {};
        var index = counter++;
        var fragment = template.content.cloneNode(true);
        var row = fragment.querySelector(".field-row");

        var nameInput = row.querySelector(".field-name-input");
        nameInput.name = "field_name_" + index;
        nameInput.id = "field_name_" + index;
        if (data.name) {
            nameInput.value = data.name;
        }
        var nameLabel = row.querySelector(".field-name-label");
        if (nameLabel) {
            nameLabel.setAttribute("for", nameInput.id);
        }

        var typeInput = row.querySelector(".field-type-input");
        typeInput.name = "field_type_" + index;
        typeInput.id = "field_type_" + index;
        if (data.type) {
            typeInput.value = data.type;
        }
        var typeLabel = row.querySelector(".field-type-label");
        if (typeLabel) {
            typeLabel.setAttribute("for", typeInput.id);
        }

        var requiredInput = row.querySelector(".field-required-input");
        requiredInput.name = "field_required_" + index;
        requiredInput.id = "field_required_" + index;
        if (data.required) {
            requiredInput.checked = true;
        }

        row.querySelector(".remove-field-row").addEventListener("click", function () {
            if (rowsContainer.querySelectorAll(".field-row").length > 1) {
                row.remove();
            } else {
                nameInput.value = "";
            }
        });

        row.querySelector(".move-up-btn").addEventListener("click", function () {
            var prev = row.previousElementSibling;
            if (prev) {
                rowsContainer.insertBefore(row, prev);
            }
        });

        row.querySelector(".move-down-btn").addEventListener("click", function () {
            var next = row.nextElementSibling;
            if (next) {
                rowsContainer.insertBefore(next, row);
            }
        });

        rowsContainer.appendChild(row);
    }

    document.getElementById("add-field-row").addEventListener("click", function () {
        addRow();
    });

    document.querySelectorAll(".preset-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            addRow({
                name: btn.getAttribute("data-name"),
                type: btn.getAttribute("data-type"),
                required: btn.getAttribute("data-req") === "1"
            });
        });
    });

    form.addEventListener("submit", function (e) {
        var names = [];
        var duplicates = [];
        var inputs = rowsContainer.querySelectorAll(".field-name-input");
        var hasValidField = false;

        inputs.forEach(function (input) {
            var val = input.value.trim().toLowerCase();
            if (val) {
                hasValidField = true;
                if (names.indexOf(val) !== -1) {
                    duplicates.push(val);
                }
                names.push(val);
            }
        });

        if (!hasValidField) {
            e.preventDefault();
            errorBox.textContent = "Please define at least one valid field name.";
            errorBox.classList.remove("hidden");
            return false;
        }

        if (duplicates.length > 0) {
            e.preventDefault();
            errorBox.textContent = "Duplicate field names detected: " + duplicates.join(", ");
            errorBox.classList.remove("hidden");
            return false;
        }

        errorBox.classList.add("hidden");
    });

    var restoredFields = [];
    try {
        restoredFields = JSON.parse(document.getElementById("field-rows-data").getAttribute("data-fields") || "[]");
    } catch (e) {
        restoredFields = [];
    }

    if (restoredFields.length > 0) {
        restoredFields.forEach(function (field) {
            addRow(field);
        });
    } else {
        addRow({ name: "name", type: "string", required: true });
    }
})();
</script>
@endsection

