<!--
    This page exists to prove the installation boots. It is not a starting
    point to build on: there is no layout to extend, no stylesheet to import
    and no component to reuse, on purpose.

    Delete this file and the "/" route in routes/web.py when you have
    something of your own to show. Nothing else refers to either.
-->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CraftEngine</title>
    <!-- Inlined so a generated project needs no favicon file. -->
    <link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2064%2064%22%3E%3Cg%20fill%3D%22%23ea580c%22%3E%3Cpath%20d%3D%22M32%209a23%2023%200%200%200-23%2023%2023%2023%200%200%200%2023%2023v-8a15%2015%200%200%201-15-15%2015%2015%200%200%201%2015-15z%22%2F%3E%3Crect%20x%3D%2228.5%22%20y%3D%222%22%20width%3D%227%22%20height%3D%2210%22%20rx%3D%221.5%22%20transform%3D%22rotate%28200%2032%2032%29%22%2F%3E%3Crect%20x%3D%2228.5%22%20y%3D%222%22%20width%3D%227%22%20height%3D%2210%22%20rx%3D%221.5%22%20transform%3D%22rotate%28245%2032%2032%29%22%2F%3E%3Crect%20x%3D%2228.5%22%20y%3D%222%22%20width%3D%227%22%20height%3D%2210%22%20rx%3D%221.5%22%20transform%3D%22rotate%28290%2032%2032%29%22%2F%3E%3Crect%20x%3D%2228.5%22%20y%3D%222%22%20width%3D%227%22%20height%3D%2210%22%20rx%3D%221.5%22%20transform%3D%22rotate%28335%2032%2032%29%22%2F%3E%3C%2Fg%3E%3Cpath%20d%3D%22M38%2012%20L24%2034%20L33%2034%20L31%2054%20L48%2029%20L38%2029%20Z%22%20fill%3D%22%23f97316%22%2F%3E%3C%2Fsvg%3E">
    <style>
        :root {
            --brand: #f97316;
            --brand-dark: #ea580c;
            --surface: #0f172a;
            --surface-raised: #1e293b;
            --muted: #94a3b8;
        }
        * { box-sizing: border-box; }
        html, body {
            margin: 0;
            height: 100%;
        }
        body {
            background: var(--surface);
            color: var(--muted);
            font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        main {
            text-align: center;
            width: 100%;
        }
        /* The mark is set in type rather than drawn in block characters. Block
           art needs the glyph to fill its advance width exactly; browsers
           substitute fonts where it does not, and the letters collapse into a
           smear at any size large enough to read. The console banner, where
           the font is a terminal's and does fill the cell, still uses the
           block mark - see craft.support.branding. */
        .mark {
            width: min(22vw, 132px);
            height: auto;
            display: block;
            margin: 0 auto 28px;
        }
        h1 {
            margin: 0;
            font-weight: 700;
            font-size: min(10vw, 118px);
            line-height: 1;
            letter-spacing: -0.04em;
            color: var(--brand);
        }
        h1 .second {
            color: var(--surface-raised);
            /* Dark-on-dark would vanish, so the second half is drawn as an
               outline: present, clearly part of the mark, visibly secondary. */
            -webkit-text-stroke: 2px var(--brand-dark);
            color: transparent;
        }
        .stamp {
            margin: 32px 0 0;
            font-size: 13px;
            color: var(--muted);
        }
        .stamp span {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 999px;
            background: var(--surface-raised);
        }
        @media (max-width: 480px) {
            h1 { letter-spacing: -0.03em; }
            h1 .second { -webkit-text-stroke-width: 1px; }
        }
        @media (prefers-reduced-motion: no-preference) {
            main { animation: rise 420ms ease-out; }
            @keyframes rise {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: none; }
            }
        }
    </style>
</head>
<body>
    <main>
        <!--
            The mark is inlined rather than linked: a generated project ships no
            static assets, and this page is meant to be deleted whole. The
            source of truth for it is docs/brand/ in the framework repository.
        -->
        <svg class="mark" viewBox="0,0,64,64" role="img" aria-label="CraftEngine">
            <g fill="#ea580c">
                <path d="M32 9a23 23 0 0 0-23 23 23 23 0 0 0 23 23v-8a15 15 0 0 1-15-15 15 15 0 0 1 15-15z"/>
                <rect x="28.5" y="2" width="7" height="10" rx="1.5" transform="rotate(200 32 32)"/>
                <rect x="28.5" y="2" width="7" height="10" rx="1.5" transform="rotate(245 32 32)"/>
                <rect x="28.5" y="2" width="7" height="10" rx="1.5" transform="rotate(290 32 32)"/>
                <rect x="28.5" y="2" width="7" height="10" rx="1.5" transform="rotate(335 32 32)"/>
            </g>
            <path d="M38 12 L24 34 L33 34 L31 54 L48 29 L38 29 Z" fill="#f97316"/>
        </svg>
        <h1>Craft<span class="second">Engine</span></h1>
        <p class="stamp"><span>{{ version }} {{ release }}</span></p>
    </main>
</body>
</html>
