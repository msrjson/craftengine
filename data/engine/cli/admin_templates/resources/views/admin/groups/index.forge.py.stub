{#
    Admin — Groups.

    Rendered by `app/Http/Controllers/Admin/GroupController.py::index`, behind
    `auth` + `role:admin` (see `routes/web.py`). This screen hands out access,
    so reaching it is itself an authorized action.

    A group grants access to a team rather than to one person at a time: it
    carries roles and/or permissions, and every member inherits them. The
    conditions column shows a grant's ABAC conditions verbatim — "publish-post,
    only where user_id matches the acting user" is precisely the detail that
    must not be rounded off on the screen people audit.

    Context provided by the controller:
      groups          list[Group]
      members         {group_id: list[User]}
      roles_of        {group_id: list[Role]}
      permissions_of  {group_id: [{"slug": str, "conditions": str|None}]}
      roles, permissions, users   for the three grant forms below
#}
@extends("layouts.panel")

@section("title", "Groups — Admin")

@section("content")
<div class="space-y-8">
    {# The heading is rendered by the panel layout from the controller's
       `heading`/`subheading`; repeating it here would print it twice. #}

    {# --- The groups themselves, with everything they grant ----------------- #}
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50/75 border-b border-slate-200 text-xs font-bold uppercase text-slate-500 font-mono">
                        <th class="px-6 py-3.5">Name</th>
                        <th class="px-6 py-3.5">Slug</th>
                        <th class="px-6 py-3.5">Members</th>
                        <th class="px-6 py-3.5">Roles</th>
                        <th class="px-6 py-3.5">Direct permissions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
                    @foreach(groups as group)
                        <tr>
                            <td class="px-6 py-4 font-semibold text-slate-900">{{ group.get_attribute('name') }}</td>
                            <td class="px-6 py-4 font-mono text-xs text-slate-500">{{ group.get_attribute('slug') }}</td>
                            <td class="px-6 py-4">
                                @if(members[group.get_attribute('id')]|length > 0)
                                    @foreach(members[group.get_attribute('id')] as member)
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 mr-1 mb-1">
                                            {{ member.get_attribute('email') }}
                                        </span>
                                    @endforeach
                                @else
                                    <span class="text-slate-400 text-xs">No members</span>
                                @endif
                            </td>
                            <td class="px-6 py-4">
                                @if(roles_of[group.get_attribute('id')]|length > 0)
                                    @foreach(roles_of[group.get_attribute('id')] as role)
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-orange-50 text-orange-700 mr-1 mb-1">
                                            {{ role.get_attribute('slug') }}
                                        </span>
                                    @endforeach
                                @else
                                    <span class="text-slate-400 text-xs">No roles</span>
                                @endif
                            </td>
                            <td class="px-6 py-4">
                                @if(permissions_of[group.get_attribute('id')]|length > 0)
                                    @foreach(permissions_of[group.get_attribute('id')] as grant)
                                        <div class="mb-1">
                                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
                                                {{ grant['slug'] }}
                                            </span>
                                            {# A conditional grant is NOT the same permission as an
                                               unconditional one; showing the condition is the point. #}
                                            @if(grant['conditions'])
                                                <code class="ml-1 text-[11px] text-slate-500">{{ grant['conditions'] }}</code>
                                            @else
                                                <span class="ml-1 text-[11px] text-slate-400">unconditional</span>
                                            @endif
                                        </div>
                                    @endforeach
                                @else
                                    <span class="text-slate-400 text-xs">None</span>
                                @endif
                            </td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    </div>

    <div class="grid gap-6 md:grid-cols-2">
        {# --- Create a group -------------------------------------------------- #}
        <div class="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-900 mb-4">Create a group</h2>
            <form action="/admin/groups" method="POST" class="space-y-4">
                @csrf
                <div class="space-y-2">
                    <label for="name" class="block text-sm font-semibold text-slate-700">Name</label>
                    <input type="text" name="name" id="name" required
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                </div>
                <div class="space-y-2">
                    <label for="slug" class="block text-sm font-semibold text-slate-700">Slug</label>
                    {# The slug is what `group:<slug>` route middleware matches. #}
                    <input type="text" name="slug" id="slug" required placeholder="support-team"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-mono text-sm focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                </div>
                <div class="space-y-2">
                    <label for="description" class="block text-sm font-semibold text-slate-700">Description</label>
                    <input type="text" name="description" id="description"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                </div>
                <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                    Create group
                </button>
            </form>
        </div>

        {# --- Add a member ---------------------------------------------------- #}
        <div class="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-900 mb-4">Add a member</h2>
            <form action="/admin/groups/members" method="POST" class="space-y-4">
                @csrf
                <div class="space-y-2">
                    <label for="member_group_id" class="block text-sm font-semibold text-slate-700">Group</label>
                    <select name="group_id" id="member_group_id" required
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                        @foreach(groups as group)
                            <option value="{{ group.get_attribute('id') }}">{{ group.get_attribute('name') }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="space-y-2">
                    <label for="user_id" class="block text-sm font-semibold text-slate-700">User</label>
                    <select name="user_id" id="user_id" required
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                        @foreach(users as user)
                            <option value="{{ user.get_attribute('id') }}">{{ user.get_attribute('email') }}</option>
                        @endforeach
                    </select>
                </div>
                <button type="submit" class="bg-slate-900 hover:bg-slate-800 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                    Add to group
                </button>
            </form>
        </div>

        {# --- Grant a role ---------------------------------------------------- #}
        <div class="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-900 mb-4">Grant a role to a group</h2>
            <form action="/admin/groups/roles" method="POST" class="space-y-4">
                @csrf
                <div class="space-y-2">
                    <label for="role_group_id" class="block text-sm font-semibold text-slate-700">Group</label>
                    <select name="group_id" id="role_group_id" required
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                        @foreach(groups as group)
                            <option value="{{ group.get_attribute('id') }}">{{ group.get_attribute('name') }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="space-y-2">
                    <label for="role_id" class="block text-sm font-semibold text-slate-700">Role</label>
                    <select name="role_id" id="role_id" required
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                        @foreach(roles as role)
                            <option value="{{ role.get_attribute('id') }}">{{ role.get_attribute('slug') }}</option>
                        @endforeach
                    </select>
                </div>
                <button type="submit" class="bg-slate-900 hover:bg-slate-800 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                    Grant role
                </button>
            </form>
        </div>

        {# --- Grant a permission, optionally conditional (ABAC) ---------------- #}
        <div class="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-900 mb-4">Grant a permission to a group</h2>
            <form action="/admin/groups/permissions" method="POST" class="space-y-4">
                @csrf
                <div class="space-y-2">
                    <label for="perm_group_id" class="block text-sm font-semibold text-slate-700">Group</label>
                    <select name="group_id" id="perm_group_id" required
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                        @foreach(groups as group)
                            <option value="{{ group.get_attribute('id') }}">{{ group.get_attribute('name') }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="space-y-2">
                    <label for="permission_id" class="block text-sm font-semibold text-slate-700">Permission</label>
                    <select name="permission_id" id="permission_id" required
                            class="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                        @foreach(permissions as permission)
                            <option value="{{ permission.get_attribute('id') }}">{{ permission.get_attribute('slug') }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="space-y-2">
                    <label for="conditions" class="block text-sm font-semibold text-slate-700">
                        Conditions <span class="font-normal text-slate-400">(optional, JSON)</span>
                    </label>
                    <input type="text" name="conditions" id="conditions" placeholder='{"user_id": "@user.id"}'
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-200 font-mono text-xs focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500">
                    <p class="text-xs text-slate-500">
                        Narrows the grant to matching records. <code>@user.&lt;attr&gt;</code> refers to the
                        acting user, so <code>{"user_id": "@user.id"}</code> means “only their own”.
                        Operators: eq, ne, in, not_in, gt, gte, lt, lte, is_null, contains.
                    </p>
                </div>
                <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                    Grant permission
                </button>
            </form>
        </div>
    </div>
</div>
@endsection
