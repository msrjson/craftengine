{#
    Admin — CRUD builder result.

    Rendered by `app/Http/Controllers/Admin/CrudBuilderController.py::store`
    after a successful generation, behind `auth` + `role:admin`. Lists the files
    that were written and the routes that were registered, because a generator
    that reports only "done" leaves you guessing what changed.

    Context:
      entity        str    the generated entity name
      created       list   paths written
      show_sidebar  bool
#}
@extends("layouts.app")

@section("title", "CRUD Builder — Generated")

@section("content")
<div class="max-w-4xl bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm space-y-6">
    <div class="flex items-center justify-between">
        <div>
            <div class="inline-flex items-center space-x-2 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full mb-2">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>Generation Successful</span>
            </div>
            <h1 class="text-2xl font-bold text-slate-900">CRUD generated for {{ entity }}</h1>
            <p class="text-slate-500 text-sm mt-0.5">The complete vertical slice has been generated and wired into the application.</p>
        </div>
    </div>

    <!-- Next Step Box -->
    <div class="p-5 rounded-2xl bg-amber-50/80 border border-amber-200 text-amber-900 space-y-2">
        <h3 class="font-bold text-sm flex items-center space-x-2">
            <span>⚡ Next Step: Apply Database Migration</span>
        </h3>
        <p class="text-xs text-amber-700">Run the pending migration in your terminal to create the database table with UUID identity:</p>
        <div class="bg-slate-900 text-amber-300 font-mono text-xs px-4 py-2.5 rounded-xl shadow-inner flex items-center justify-between">
            <code>python dev.py migrate</code>
        </div>
    </div>

    <!-- Generated Files List -->
    <div class="space-y-2">
        <h2 class="text-sm font-bold text-slate-700">Generated Files & Routes</h2>
        <div class="divide-y divide-slate-100 border border-slate-200/80 rounded-2xl overflow-hidden bg-slate-50/30">
            @foreach(files.items() as kind, path)
                <div class="flex items-center justify-between px-5 py-3 text-sm hover:bg-slate-50/60 transition">
                    <span class="font-semibold text-slate-700 text-xs uppercase tracking-wider">{{ kind.replace('_', ' ') }}</span>
                    <code class="text-xs text-slate-600 font-mono bg-white px-2 py-0.5 rounded border border-slate-200">{{ path }}</code>
                </div>
            @endforeach
        </div>
    </div>

    <!-- Quick Navigation Links -->
    <div class="flex items-center justify-between pt-4 border-t border-slate-100">
        <div class="flex items-center space-x-3">
            <a href="/admin/crud-builder"
               class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-5 py-2.5 rounded-xl shadow-md transition duration-150 text-sm">
                + Build Another Entity
            </a>
            <a href="/admin" class="text-sm font-semibold text-slate-600 hover:text-slate-900 px-4 py-2.5 rounded-xl hover:bg-slate-100 transition">
                Back to Dashboard
            </a>
        </div>
    </div>
</div>
@endsection

