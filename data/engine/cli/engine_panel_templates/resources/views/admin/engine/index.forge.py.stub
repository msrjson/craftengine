{#
    Admin - Engine updates.

    Rendered by `app/Http/Controllers/Admin/EngineUpdateController.py` at
    `GET /admin/engine`, behind `auth` + `role:admin`. Reads only the cached
    notice; the "check" form asks the canonical repository on demand.

    Context:
      overview   dict    pin, mode, running, verify_command, patches, drift, error
      notice     UpdateNotice | None   the last check, from the cache
      refusal    str     refusal code of the last action, or ""
#}
@extends("layouts.app")

@section("title", __('engine.update.title'))

@section("content")
<div class="space-y-8">
    @include("partials.engine_update_alert")

    @if(refusal)
        <div role="alert" class="bg-red-50 border border-red-200 text-red-800 rounded-2xl px-6 py-4 text-sm">
            {{ __('engine.update.refused', code=refusal) }}
        </div>
    @endif

    @if(overview.error)
        <div role="alert" class="bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl px-6 py-4 text-sm">
            {{ __('engine.update.lock_missing', code=overview.error) }}
        </div>
    @else
        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
            <h1 class="text-lg font-bold text-slate-900 mb-4">{{ __('engine.update.title') }}</h1>
            <dl class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                <div><dt class="text-slate-500">{{ __('engine.update.field.pinned') }}</dt><dd class="font-mono text-slate-900">{{ overview.pinned }}</dd></div>
                <div><dt class="text-slate-500">{{ __('engine.update.field.running') }}</dt><dd class="font-mono text-slate-900">{{ overview.running }}</dd></div>
                <div><dt class="text-slate-500">{{ __('engine.update.field.mode') }}</dt><dd class="font-mono text-slate-900">{{ overview.mode }}</dd></div>
                <div>
                    <dt class="text-slate-500">{{ __('engine.update.field.verify_command') }}</dt>
                    <dd class="font-mono text-slate-900">
                        @if(overview.verify_command)
                            {{ overview.verify_command }}
                        @else
                            <span class="text-amber-700">{{ __('engine.update.empty.verify_command') }}</span>
                        @endif
                    </dd>
                </div>
            </dl>
        </div>

        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-4">
            @if(notice is none)
                <p class="text-sm text-slate-600">{{ __('engine.update.status.never_checked') }}</p>
            @elseif(notice.error)
                <p class="text-sm text-red-700">{{ __('engine.update.status.check_failed', code=notice.error) }}</p>
            @elseif(not notice.available)
                <p class="text-sm text-emerald-700">{{ __('engine.update.status.current') }}</p>
            @endif
            @if(notice is not none)
                <p class="text-xs text-slate-500">{{ __('engine.update.field.checked_at') }}: <span class="font-mono">{{ notice.checked_at }}</span></p>
            @endif

            <div class="flex flex-wrap gap-3">
                <form action="/admin/engine/check" method="POST">
                    @csrf
                    <button type="submit" class="border border-slate-300 hover:bg-slate-50 text-slate-800 font-semibold px-5 py-2.5 rounded-xl text-sm">
                        {{ __('engine.update.action.check') }}
                    </button>
                </form>
                @if(notice is not none and notice.update and not overview.drift)
                    <a href="/admin/engine/review?target=update" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-5 py-2.5 rounded-xl text-sm">
                        {{ __('engine.update.action.review_update', version=notice.update) }}
                    </a>
                @endif
                @if(notice is not none and notice.newest and notice.newest != notice.update and not overview.drift)
                    <a href="/admin/engine/review?target={{ notice.newest }}" class="bg-slate-900 hover:bg-slate-800 text-white font-bold px-5 py-2.5 rounded-xl text-sm">
                        {{ __('engine.update.action.review_upgrade', version=notice.newest) }}
                    </a>
                @endif
            </div>
        </div>

        @if(overview.drift)
            <div class="bg-white rounded-2xl border border-red-200 shadow-sm p-6">
                <h2 class="text-base font-bold text-red-800 mb-2">{{ __('engine.update.drift.heading') }}</h2>
                <p class="text-sm text-slate-600 mb-3">{{ __('engine.update.drift.blocking') }}</p>
                <ul class="font-mono text-xs text-slate-700 space-y-1">
                    @foreach(overview.drift as path)
                        <li>{{ path }}</li>
                    @endforeach
                </ul>
            </div>
        @endif

        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
            <h2 class="text-base font-bold text-slate-900 mb-3">{{ __('engine.update.patches.heading') }}</h2>
            @if(overview.patches)
                <ul class="text-sm text-slate-700 space-y-2">
                    @foreach(overview.patches as patch)
                        <li><span class="font-mono font-semibold">{{ patch.id }}</span> <span class="text-xs uppercase text-slate-500">{{ patch.patch_class }}</span> {{ patch.reason }}</li>
                    @endforeach
                </ul>
            @else
                <p class="text-sm text-slate-500">{{ __('engine.update.patches.empty') }}</p>
            @endif
        </div>
    @endif
</div>
@endsection
