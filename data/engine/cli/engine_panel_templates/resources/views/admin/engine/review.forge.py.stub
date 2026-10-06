{#
    Admin - Engine update review and result.

    Rendered by `EngineUpdateController.review` (a dry run: nothing changed)
    and by `EngineUpdateController.apply` (the move happened), behind `auth` +
    `role:admin`. The apply form posts only the target; the verification
    command is the one recorded in `craft-engine.lock`.

    Context:
      report   MoveReport   current, target, plan (carried, retired), notes, applied
      target   str          `update` or a release tag
#}
@extends("layouts.app")

@section("title", __('engine.update.title'))

@section("content")
<div class="space-y-8">
    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-4">
        @if(report.applied)
            <h1 class="text-lg font-bold text-emerald-800">{{ __('engine.update.review.heading_applied', current=report.current.ref, target=report.target.ref) }}</h1>
            <p class="text-sm text-slate-700">{{ __('engine.update.review.next_steps') }}</p>
        @else
            <h1 class="text-lg font-bold text-slate-900">{{ __('engine.update.review.heading_dry_run', current=report.current.ref, target=report.target.ref) }}</h1>
        @endif

        @if(report.plan.carried)
            <div>
                <h2 class="text-sm font-bold text-slate-700">{{ __('engine.update.review.carried') }}</h2>
                <ul class="font-mono text-xs text-slate-700">
                    @foreach(report.plan.carried as patch)
                        <li>{{ patch.id }}</li>
                    @endforeach
                </ul>
            </div>
        @endif
        @if(report.plan.retired)
            <div>
                <h2 class="text-sm font-bold text-slate-700">{{ __('engine.update.review.retired') }}</h2>
                <ul class="font-mono text-xs text-slate-700">
                    @foreach(report.plan.retired as patch_id)
                        <li>{{ patch_id }}</li>
                    @endforeach
                </ul>
            </div>
        @endif
    </div>

    <div class="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6">
        <h2 class="text-base font-bold text-slate-900 mb-3">{{ __('engine.update.review.notes') }}</h2>
        @foreach(report.notes as section)
            <h3 class="font-mono text-sm font-semibold text-slate-800 mt-4">{{ section.heading }}</h3>
            <ul class="text-sm text-slate-700 list-disc ml-5">
                @foreach(section.attention as entry)
                    <li>{{ entry }}</li>
                @endforeach
            </ul>
        @endforeach
        @if(not report.notes)
            <p class="text-sm text-slate-500">{{ __('engine.update.review.no_notes') }}</p>
        @endif
    </div>

    <div class="flex flex-wrap gap-3">
        @if(not report.applied)
            <form action="/admin/engine/apply" method="POST">
                @csrf
                <input type="hidden" name="target" value="{{ target }}">
                <button type="submit" class="bg-orange-600 hover:bg-orange-700 text-white font-bold px-6 py-2.5 rounded-xl shadow-md text-sm">
                    {{ __('engine.update.action.apply', version=report.target.ref) }}
                </button>
            </form>
        @endif
        <a href="/admin/engine" class="border border-slate-300 hover:bg-slate-50 text-slate-800 font-semibold px-5 py-2.5 rounded-xl text-sm">
            {{ __('engine.update.action.back') }}
        </a>
    </div>
</div>
@endsection
