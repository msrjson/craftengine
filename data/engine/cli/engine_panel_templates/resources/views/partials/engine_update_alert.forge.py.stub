{#
    Engine update alert, shown at the top of admin panel pages.

    `engine_update` is the cached `UpdateNotice` that `PanelPage.panel()` puts
    in the context for admins only (None for everyone else). Rendering it never
    calls the network: the notice is refreshed by `dev.py engine check` (run it
    from the scheduler) or by the "check" button on `/admin/engine`.
#}
@if(engine_update and engine_update.available)
    <div role="status" class="bg-orange-50 border border-orange-200 text-orange-900 rounded-2xl px-6 py-4 text-sm flex flex-wrap items-center justify-between gap-3">
        <span>{{ __('engine.update.alert.available', version=engine_update.update or engine_update.newest) }}</span>
        <a href="/admin/engine" class="font-bold underline">{{ __('engine.update.alert.action') }}</a>
    </div>
@endif
