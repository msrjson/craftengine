{#
    Admin — Roles.

    Rendered by `app/Http/Controllers/Admin/RoleController.py::index` at
    `GET /admin/roles`, behind `auth` + `role:admin`. The form posts to
    `/admin/roles/grant`. Granting access is itself an authorized action, which
    is why this screen is admin-only.

    Context:
      roles              list[Role]
      role_permissions   {role_id: list[Permission]}
      permissions        list[Permission]   options for the grant form
      show_sidebar       bool
#}
@extends("layouts.panel")

@section("title", "Roles — Admin")

@section("content")
<div class="space-y-8">
    {# Heading comes from the panel layout (`heading`/`subheading`). #}
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-xs font-bold uppercase text-slate-500 font-mono">
                        <th class="px-6 py-3.5">Name</th>
                        <th class="px-6 py-3.5">Slug</th>
                        <th class="px-6 py-3.5">Permissions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
                    @foreach(roles as role)
                        <tr>
                            <td class="px-6 py-4 font-semibold text-slate-900">{{ role.get_attribute('name') }}</td>
                            <td class="px-6 py-4 font-mono text-xs text-slate-500">{{ role.get_attribute('slug') }}</td>
                            <td class="px-6 py-4">
                                @if(role_permissions[role.get_attribute('id')]|length > 0)
                                    @foreach(role_permissions[role.get_attribute('id')] as permission)
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 mr-1 mb-1">
                                            {{ permission.get_attribute('slug') }}
                                        </span>
                                    @endforeach
                                @else
                                    <span class="text-slate-400 text-xs">No permissions granted</span>
                                @endif
                            </td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    </div>

    <div class="max-w-xl bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900 mb-4">Grant a permission to a role</h2>
        <form action="/admin/roles/grant" method="POST" class="space-y-4">
            @csrf

            <div class="space-y-2">
                <label for="role_id" class="block text-sm font-semibold text-slate-700">Role</label>
                <select name="role_id" id="role_id" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500" required>
                    @foreach(roles as role)
                        <option value="{{ role.get_attribute('id') }}">{{ role.get_attribute('name') }}</option>
                    @endforeach
                </select>
            </div>

            <div class="space-y-2">
                <label for="permission_id" class="block text-sm font-semibold text-slate-700">Permission</label>
                <select name="permission_id" id="permission_id" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500" required>
                    @foreach(permissions as permission)
                        <option value="{{ permission.get_attribute('id') }}">{{ permission.get_attribute('slug') }}</option>
                    @endforeach
                </select>
            </div>

            <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                Grant Permission
            </button>
        </form>
    </div>
</div>
@endsection
