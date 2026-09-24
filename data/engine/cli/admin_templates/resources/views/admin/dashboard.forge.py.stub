{#
    Admin dashboard — the installation's user directory.

    Rendered by `app/Http/Controllers/Admin/HomeController.py::admin` at
    `GET /admin`, behind `auth` + `role:admin`, and the controller repeats the
    check with `Gate.authorize("access-admin-dashboard")`. Two independent
    controls on purpose: this page lists every account in the system, and it
    once shipped behind `auth` alone, which let any user who could log in read
    the whole directory.

    Context:
      administrators  list[User]  accounts with `is_admin`
      users           list[User]  every account, newest first
      tenants         list        active tenants, or [] where tenancy is not
                                  provisioned (a legitimate empty, not a
                                  swallowed failure)
      show_sidebar    bool
#}
@extends("layouts.app")

@section("title", "Admin Cockpit — Craft Cloud SaaS Management")

@section("content")
    <!-- Dashboard Header -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between pb-6 mb-8 border-b border-slate-200">
        <div>
            <h1 class="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">System Admin Dashboard</h1>
            <p class="text-slate-500 text-sm mt-1">Central administration panel for Tenants, Users, and Administrators.</p>
        </div>
        <div class="mt-4 md:mt-0 flex space-x-3">
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-600 border border-emerald-100 font-mono">
                <span class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping mr-2"></span>
                Active Database: pgsql (PostgreSQL)
            </span>
        </div>
    </div>

    <!-- Stats & Live Monitors -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.01)] flex items-center space-x-4">
            <div class="p-3 bg-orange-50 text-orange-600 rounded-xl">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
            </div>
            <div>
                <span class="text-xs text-slate-400 font-bold uppercase tracking-wider block">Total Tenants</span>
                <span class="text-xl font-extrabold text-slate-800">{{ tenants|length }} Active</span>
            </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.01)] flex items-center space-x-4">
            <div class="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
            </div>
            <div>
                <span class="text-xs text-slate-400 font-bold uppercase tracking-wider block">Registered Users</span>
                <span class="text-xl font-extrabold text-slate-800">{{ users|length }} Profiles</span>
            </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.01)] flex items-center space-x-4">
            <div class="p-3 bg-blue-50 text-blue-600 rounded-xl">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
            </div>
            <div>
                <span class="text-xs text-slate-400 font-bold uppercase tracking-wider block">PQC Keys</span>
                <span class="text-xl font-extrabold text-slate-800">ML-KEM Active</span>
            </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.01)] flex items-center space-x-4">
            <div class="p-3 bg-purple-50 text-purple-600 rounded-xl">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18.2M7 9a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
            </div>
            <div>
                <span class="text-xs text-slate-400 font-bold uppercase tracking-wider block">Queue Jobs</span>
                <span class="text-xl font-extrabold text-slate-800">Async Idle</span>
            </div>
        </div>
    </div>

    <!-- Main Content Area: Tenants, Users, Administrators -->
    <div class="space-y-10">

        <!-- 1. SaaS Tenants Management -->
        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.01)] overflow-hidden">
            <div class="p-6 border-b border-slate-200 flex items-center justify-between">
                <div>
                    <h3 class="text-lg font-bold text-slate-900">Cloud Tenants (Workspace Isolation)</h3>
                    <p class="text-xs text-slate-500">List of tenant accounts mapped in the routing subdomains.</p>
                </div>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-50/75 border-b border-slate-200 text-xs font-bold uppercase text-slate-500 font-mono">
                            <th class="px-6 py-3.5">ID</th>
                            <th class="px-6 py-3.5">Tenant Name</th>
                            <th class="px-6 py-3.5">Routing Host / Subdomain</th>
                            <th class="px-6 py-3.5">Database Dialect</th>
                            <th class="px-6 py-3.5">Status</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
                        @foreach(tenants as tenant)
                            <tr>
                                <td class="px-6 py-4 font-mono font-bold">{{ tenant.id }}</td>
                                <td class="px-6 py-4 font-semibold text-slate-900">{{ tenant.name }}</td>
                                <td class="px-6 py-4 font-mono text-slate-500 text-xs">{{ tenant.domain }}</td>
                                <td class="px-6 py-4">
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
                                        {{ tenant.db_engine }}
                                    </span>
                                </td>
                                <td class="px-6 py-4">
                                    @if(tenant.status == "Active")
                                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
                                            Active
                                        </span>
                                    @else
                                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-100">
                                            Suspended
                                        </span>
                                    @endif
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 2. System Administrators Grid -->
        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.01)] overflow-hidden">
            <div class="p-6 border-b border-slate-200">
                <h3 class="text-lg font-bold text-slate-900">System Administrators</h3>
                <p class="text-xs text-slate-500">Accounts authorized to execute dev.py tasks and configurations.</p>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-50/75 border-b border-slate-200 text-xs font-bold uppercase text-slate-500 font-mono">
                            <th class="px-6 py-3.5">ID</th>
                            <th class="px-6 py-3.5">Admin Name</th>
                            <th class="px-6 py-3.5">Email</th>
                            <th class="px-6 py-3.5">Active Roles</th>
                            <th class="px-6 py-3.5">Privilege Level</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
                        @if(administrators|length > 0)
                            @foreach(administrators as admin)
                                <tr>
                                    <td class="px-6 py-4 font-mono">{{ admin.get_attribute('id') }}</td>
                                    <td class="px-6 py-4 font-semibold text-slate-900">{{ admin.get_attribute('name') }}</td>
                                    <td class="px-6 py-4 font-mono text-xs text-slate-500">{{ admin.get_attribute('email') }}</td>
                                    <td class="px-6 py-4">
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-orange-50 text-orange-600 border border-orange-100">
                                            Admin
                                        </span>
                                    </td>
                                    <td class="px-6 py-4">
                                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-900 text-slate-200">
                                            Root Access
                                        </span>
                                    </td>
                                </tr>
                            @endforeach
                        @else
                            <tr>
                                <td colspan="5" class="px-6 py-8 text-center text-slate-400">No system administrators registered in database.</td>
                            </tr>
                        @endif
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 3. All Users List -->
        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.01)] overflow-hidden">
            <div class="p-6 border-b border-slate-200">
                <h3 class="text-lg font-bold text-slate-900">User Directory</h3>
                <p class="text-xs text-slate-500">General profiles registered in the active PostgreSQL database.</p>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-50/75 border-b border-slate-200 text-xs font-bold uppercase text-slate-500 font-mono">
                            <th class="px-6 py-3.5">ID</th>
                            <th class="px-6 py-3.5">Full Name</th>
                            <th class="px-6 py-3.5">Email Address</th>
                            <th class="px-6 py-3.5">Created At</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 text-sm text-slate-700">
                        @foreach(users as u)
                            <tr>
                                <td class="px-6 py-4 font-mono text-xs">{{ u.get_attribute('id') }}</td>
                                <td class="px-6 py-4 font-semibold text-slate-900">{{ u.get_attribute('name') }}</td>
                                <td class="px-6 py-4 font-mono text-xs text-slate-500">{{ u.get_attribute('email') }}</td>
                                <td class="px-6 py-4 text-xs text-slate-400 font-mono">{{ u.get_attribute('created_at') }}</td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </div>

    </div>
@endsection
