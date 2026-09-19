{#
    Panel — Dashboard.

    Rendered by `app/Http/Controllers/Panel/PanelController.py::index` at
    `GET /panel`, behind `auth`. Every signed-in account reaches this page; what
    it contains differs by account.

    Context:
      stats        list[{label, value, hint}]  always shown
      admin_stats  list[{label, value, hint}]  administrators only, may be []
#}
@extends("layouts.panel")

@section("title", "Dashboard")

@section("content")

<section>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        @foreach(stats as stat)
            <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <p class="text-xs font-bold uppercase tracking-wider text-slate-400">{{ stat['label'] }}</p>
                <p class="mt-2 text-3xl font-extrabold text-slate-900 tabular-nums">{{ stat['value'] }}</p>
                <p class="mt-1 text-xs text-slate-500 truncate">{{ stat['hint'] }}</p>
            </div>
        @endforeach
    </div>
</section>

@if(admin_stats|length > 0)
    {# Only administrators get this row #}
    <section>
        <h3 class="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">This installation</h3>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            @foreach(admin_stats as stat)
                <div class="bg-slate-900 text-white rounded-2xl p-5 shadow-sm">
                    <p class="text-xs font-bold uppercase tracking-wider text-slate-400">{{ stat['label'] }}</p>
                    <p class="mt-2 text-3xl font-extrabold tabular-nums">{{ stat['value'] }}</p>
                    <p class="mt-1 text-xs text-slate-500 truncate">{{ stat['hint'] }}</p>
                </div>
            @endforeach
        </div>
    </section>
@endif

<section>
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h3 class="text-base font-bold text-slate-900 mb-2">Welcome to your Craft Engine Workspace</h3>
        <p class="text-sm text-slate-600 mb-4">
            Your workspace is running clean and ready for development. Use the CLI commands or create new modules and models to build your application features from scratch.
        </p>

        <div class="flex flex-wrap gap-3">
            <a href="/panel/profile" class="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl text-slate-700 bg-slate-100 hover:bg-slate-200 transition">
                Manage Profile &rarr;
            </a>
            @can("access-admin-dashboard")
                <a href="/admin/crud-builder" class="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl text-white bg-orange-600 hover:bg-orange-700 transition">
                    Visual CRUD Builder &rarr;
                </a>
                <a href="/panel/system" class="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl text-slate-700 bg-slate-100 hover:bg-slate-200 transition">
                    System Overview &rarr;
                </a>
            @endcan
        </div>
    </div>
</section>

@endsection
